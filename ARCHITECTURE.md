# Архитектура

---

## 1. Развёртывание

Пять контейнеров в одном `docker-compose`. Приложение не держит состояния в
памяти процесса, поэтому реплик `app` может быть сколько угодно.

```mermaid
flowchart LR
    browser["Браузер<br/>SPA + WebSocket"]

    subgraph compose["docker-compose на VPS"]
        direction LR
        nginx["nginx :80<br/>reverse proxy"]
        app["app × N<br/>gunicorn + uvicorn"]
        worker["worker<br/>ARQ · cron 06:00"]
        pg[("PostgreSQL<br/>том pgdata")]
        redis[("Redis<br/>кеш + pub/sub")]
    end

    browser -->|"HTTP · WebSocket"| nginx
    nginx -->|":8000"| app
    app -->|"asyncpg"| pg
    app -->|"кеш агрегатов"| redis
    worker -->|"чтение задач"| pg
    worker -->|"очередь"| redis
    redis -.->|"события проекта · pub/sub"| app
```

**Почему события идут через Redis, а не через список сокетов в памяти.** При
двух и более репликах `app` клиенты одного проекта распределены по разным
процессам. Локальный список сокетов доставил бы событие только части из них,
поэтому каждый процесс подписан на общий канал и раздаёт события своим
подключениям.

---

## 2. Слои приложения

Зависимости направлены строго вниз: роутер не знает про SQL, сервис не знает
про HTTP, репозиторий не знает про бизнес-правила.

```mermaid
flowchart TB
    subgraph http["HTTP / WebSocket"]
        routers["api/routers<br/><i>маршрутизация и валидация запроса</i>"]
    end

    services["services<br/><i>бизнес-логика, права, транзакции</i>"]
    repos["repositories<br/><i>инкапсуляция ORM-запросов</i>"]
    models["models · SQLAlchemy 2.0<br/><i>таблицы, индексы, ограничения</i>"]
    pg[("PostgreSQL")]

    core["Чистое ядро<br/>scheduling.py · status.py<br/><i>DAG · CPM · каскад · состояния</i>"]
    errors["core/exceptions → api/errors<br/><i>единый формат ошибки</i>"]

    routers --> services
    services --> repos
    repos --> models
    models --> pg
    services <-->|"датаклассы"| core
    services -.->|"бросает доменные исключения"| errors
    errors -.->|"превращает в HTTP"| routers

    classDef pure fill:#e7eafa,stroke:#2b45c7,stroke-width:2px;
    class core pure;
```

**Ядро вынесено намеренно.** `scheduling.py` не импортирует ни ORM, ни БД, ни
HTTP, ни системное время — на входе и выходе простые датаклассы. Поэтому его
можно тестировать без базы и перенести в отдельный воркер, когда графы задач
вырастут. Все 27 автотестов бьют именно в эти два модуля.

---

## 3. Схема базы данных

Полная версия с ограничениями и индексами — в [`schema.dbml`](schema.dbml)
(открывается в dbdiagram.io). Здесь — связи между таблицами.

```mermaid
erDiagram
    users ||--o{ projects : "владеет · RESTRICT"
    users ||--o{ project_members : "участвует"
    projects ||--o{ project_members : "состав команды"
    projects ||--o{ tasks : "содержит"
    users |o--o{ tasks : "ответственный · SET NULL"
    tasks ||--o{ task_dependencies : "predecessor_id"
    tasks ||--o{ task_dependencies : "successor_id"
    tasks ||--o{ comments : "обсуждение"
    users ||--o{ comments : "автор"
    users ||--o{ notifications : "адресат"
    tasks |o--o{ notifications : "повод"

    users {
        int id PK
        string email UK
        string hashed_password
        string full_name
        bool is_active
    }
    projects {
        int id PK
        string name
        date start_date
        date end_date
        int owner_id FK
        enum status
    }
    project_members {
        int id PK
        int project_id FK
        int user_id FK
        enum role "owner, responsible, viewer"
    }
    tasks {
        int id PK
        int project_id FK
        string title
        date start_date
        date end_date
        enum status
        int assignee_id FK
        int progress_percent
    }
    task_dependencies {
        int id PK
        int project_id FK
        int predecessor_id FK
        int successor_id FK
        enum type "finish_to_start"
        int lag_days
    }
    comments {
        int id PK
        int task_id FK
        int user_id FK
        text text
    }
    notifications {
        int id PK
        int user_id FK
        int project_id FK
        int task_id FK
        enum type
        bool is_read
    }
```

**Граф зависимостей живёт в таблице рёбер.** `predecessor_id` и `successor_id`
оба ссылаются на `tasks.id` — два внешних ключа на одну таблицу дают
направленный граф. `CHECK (predecessor_id <> successor_id)` запрещает петлю на
уровне БД, уникальный индекс — дубликат пары. Ацикличность целиком в СУБД
проверить нельзя, поэтому её держит приложение — перед каждой вставкой.

**Чего в схеме намеренно нет:** колонок `is_overdue` и `duration_days`. Обе
производны от дат и текущего дня, их пришлось бы пересчитывать по расписанию.
Считаются при чтении.

---

## 4. Основной процесс

```mermaid
flowchart TD
    start(["Нужен контроль<br/>над проектом"]) --> p1["Создать проект<br/>и пригласить команду"]
    p1 --> p2["Добавить задачи:<br/>сроки и ответственные"]
    p2 --> p3["Связать задачи"]
    p3 --> g1{"Связь образует<br/>цикл?"}
    g1 -->|"да · 409 task_cycle"| p4["Отклонить связь"]
    p4 --> p3
    g1 -->|"нет"| p5["Сохранить связь,<br/>пересчитать критический путь"]
    p5 --> p6["Открыть диаграмму Ганта"]
    p6 --> p7["Запросить прогноз сдвига<br/>GET /tasks/id/impact"]
    p7 --> g2{"Дедлайн проекта<br/>срывается?"}
    g2 -->|"да"| p8["Показать риск<br/>и затронутые задачи"]
    p8 --> p7
    g2 -->|"нет"| p9["Применить сдвиг с каскадом<br/>POST /tasks/id/shift"]
    p9 --> p10["Разослать событие участникам"]
    p10 --> done(["Сроки под контролем"])
```

Отдельная ветка процесса — фоновый воркер: ежедневно в 06:00 находит
просроченные задачи и создаёт уведомления ответственным.

---

## 5. Сдвиг задачи с каскадом

Главный сценарий продукта: пользователь двигает задачу, система показывает, что
поедет следом и не сорвётся ли дедлайн.

```mermaid
sequenceDiagram
    autonumber
    actor U as Руководитель
    participant API as api/routers/tasks
    participant TS as TaskService
    participant SCH as scheduling.py<br/>(чистые функции)
    participant DB as PostgreSQL
    participant R as Redis
    participant C as Другие клиенты

    U->>API: POST /tasks/{id}/shift<br/>{shift_days: 10, cascade: true}
    API->>TS: shift_task(...)
    TS->>DB: задачи и связи проекта
    DB-->>TS: nodes, edges

    rect rgb(231, 234, 250)
        Note over TS,SCH: расчёт без побочных эффектов
        TS->>SCH: cascade_shift(nodes, edges, changed)
        SCH-->>TS: список сдвинутых задач
        TS->>SCH: compute_schedule(обновлённый граф)
        SCH-->>TS: ES/EF/LS/LF, резервы, критический путь
    end

    TS->>DB: UPDATE дат задачи и её последователей
    TS->>R: invalidate_project(id)
    TS->>R: publish tasks.rescheduled
    R-->>C: событие через pub/sub
    TS-->>API: ImpactAnalysis
    API-->>U: 200 · затронутые задачи,<br/>прогноз окончания, breaks_deadline
```

Критичность считается на графе **после** сдвига: сдвиг может переложить
критический путь на другую ветку, и пользователю важно видеть новое состояние.

`GET /tasks/{id}/impact` выполняет ровно те же шаги 3–9, но пропускает запись в
базу — отсюда «сухой прогон» для превью при перетаскивании полосы.

---

## 6. Граф задач и критический путь

Пример из тестов: `1 → {2, 3} → 4`, где верхняя ветка длиннее нижней.

```mermaid
flowchart LR
    t1["1 · Анализ<br/>1–5 янв · 5 дн<br/>резерв 0"]
    t2["2 · Дизайн<br/>6–10 янв · 5 дн<br/>резерв 0"]
    t3["3 · Параллельная<br/>6–8 янв · 3 дн<br/>резерв 2"]
    t4["4 · Тестирование<br/>11–15 янв · 5 дн<br/>резерв 0"]

    t1 ==> t2
    t1 --> t3
    t2 ==> t4
    t3 --> t4

    classDef crit fill:#e7eafa,stroke:#2b45c7,stroke-width:3px;
    classDef slack fill:#f7f9fc,stroke:#858da3,stroke-width:1px;
    class t1,t2,t4 crit;
    class t3 slack;
```

Жирные рёбра — критический путь `1 → 2 → 4`, суммарно 15 дней.

Расчёт в два прохода по топологическому порядку:

| Задача | Длит. | ES | EF | LS | LF | Резерв |
|---|---:|---:|---:|---:|---:|---:|
| 1 Анализ | 5 | 0 | 4 | 0 | 4 | **0** |
| 2 Дизайн | 5 | 5 | 9 | 5 | 9 | **0** |
| 3 Параллельная | 3 | 5 | 7 | 7 | 9 | 2 |
| 4 Тестирование | 5 | 10 | 14 | 10 | 14 | **0** |

Даты переводятся в индексы дней от общего начала — арифметика на целых числах
проще, а лаги и резервы естественно выражаются в днях.

- **Прямой проход**: `ES = max(плановый старт, EF предшественника + 1 + лаг)`,
  `EF = ES + длительность − 1`. Плановая дата старта — нижняя граница: задача не
  может начаться раньше, чем её поставил человек, даже если предшественники
  закончились досрочно.
- **Обратный проход**: `LF = min(LS последователя − 1 − лаг)`, для задач без
  последователей `LF` равен окончанию проекта; `LS = LF − длительность + 1`.
- **Резерв** `= LS − ES`. Критическая задача — с нулевым или отрицательным
  резервом; отрицательный означает, что плановые даты уже противоречат связям.

Сам путь восстанавливается отдельно — идём от задачи с максимальным `EF` назад
по «натянутым» рёбрам, где `EF предшественника + 1 + лаг` в точности равен `ES`
текущей задачи. Множество задач с нулевым резервом само по себе ещё не путь:
в ромбе обе ветви могут оказаться нулевыми при равной длине.

---

## 7. Статус задачи и состояние

Два разных понятия, которые легко перепутать.

```mermaid
stateDiagram-v2
    direction LR

    state "Хранится в БД · ставит пользователь" as stored {
        [*] --> planned
        planned --> in_progress
        in_progress --> done
        planned --> blocked
        in_progress --> blocked
        blocked --> in_progress
        planned --> cancelled
        in_progress --> cancelled
        done --> [*]
        cancelled --> [*]
    }
```

`status` пользователь меняет через `PATCH /tasks/{id}`. А наружу вместе с ним
отдаётся `state` — производная величина, которую сервер вычисляет на каждый
запрос:

```mermaid
flowchart TD
    q0{"status"} -->|"done"| s1["state = done"]
    q0 -->|"cancelled"| s2["state = cancelled"]
    q0 -->|"blocked"| s3["state = blocked"]
    q0 -->|"planned / in_progress"| q1{"end_date<br/>раньше сегодня?"}
    q1 -->|"да"| s4["state = overdue"]
    q1 -->|"нет"| q2{"start_date<br/>позже сегодня?"}
    q2 -->|"да"| s5["state = upcoming"]
    q2 -->|"нет"| s6["state = in_progress"]

    classDef hot fill:#fae7e4,stroke:#c23a2e,stroke-width:2px;
    class s4 hot;
```

**Просрочка нигде не хранится.** Задача становится `overdue` без единого запроса
на изменение — просто потому, что наступило завтра. Правило живёт в одном месте
(`services/status.py`), поэтому API, статистика и уведомления не могут разойтись
в трактовке.

Для раскраски интерфейса используйте `state`, для редактирования — `status`.
