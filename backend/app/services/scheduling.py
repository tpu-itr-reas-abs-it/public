from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Dict, Iterable, List, Optional, Sequence, Set, Tuple

from app.core.exceptions import TaskCycleError


@dataclass(frozen=True)
class TaskNode:
    id: int
    start_date: date
    end_date: date

    @property
    def duration_days(self) -> int:
        return (self.end_date - self.start_date).days + 1


@dataclass(frozen=True)
class DepEdge:
    predecessor_id: int
    successor_id: int
    lag_days: int = 0
    id: Optional[int] = None


@dataclass
class TaskSchedule:
    task_id: int
    earliest_start: date
    earliest_finish: date
    latest_start: date
    latest_finish: date
    slack_days: int
    is_critical: bool
    depth: int


@dataclass
class ScheduleResult:
    tasks: Dict[int, TaskSchedule] = field(default_factory=dict)
    critical_path: List[int] = field(default_factory=list)
    critical_path_days: int = 0
    project_start: Optional[date] = None
    project_finish: Optional[date] = None

    @property
    def total_days(self) -> int:
        if self.project_start is None or self.project_finish is None:
            return 0
        return (self.project_finish - self.project_start).days + 1


@dataclass
class ShiftedTask:
    task_id: int
    old_start: date
    old_end: date
    new_start: date
    new_end: date

    @property
    def shift_days(self) -> int:
        return (self.new_start - self.old_start).days


@dataclass
class Violation:
    edge: DepEdge
    required_start: date
    actual_start: date

    @property
    def days(self) -> int:
        return (self.required_start - self.actual_start).days


def build_adjacency(
    edges: Iterable[DepEdge],
) -> Tuple[Dict[int, List[DepEdge]], Dict[int, List[DepEdge]]]:
    outgoing: Dict[int, List[DepEdge]] = defaultdict(list)
    incoming: Dict[int, List[DepEdge]] = defaultdict(list)
    for edge in edges:
        outgoing[edge.predecessor_id].append(edge)
        incoming[edge.successor_id].append(edge)
    return outgoing, incoming


def topological_order(node_ids: Iterable[int], edges: Iterable[DepEdge]) -> List[int]:
    nodes = list(dict.fromkeys(node_ids))
    edge_list = list(edges)
    known: Set[int] = set(nodes)

    indegree: Dict[int, int] = {node_id: 0 for node_id in nodes}
    outgoing: Dict[int, List[int]] = defaultdict(list)
    for edge in edge_list:
        if edge.predecessor_id not in known or edge.successor_id not in known:
            continue
        outgoing[edge.predecessor_id].append(edge.successor_id)
        indegree[edge.successor_id] += 1

    queue = deque(sorted(node_id for node_id in nodes if indegree[node_id] == 0))
    order: List[int] = []
    while queue:
        current = queue.popleft()
        order.append(current)
        for successor in outgoing[current]:
            indegree[successor] -= 1
            if indegree[successor] == 0:
                queue.append(successor)

    if len(order) != len(nodes):
        cycle = sorted(node_id for node_id in nodes if indegree[node_id] > 0)
        raise TaskCycleError(details={"tasks_in_cycle": cycle})
    return order


def has_cycle(node_ids: Iterable[int], edges: Iterable[DepEdge]) -> bool:
    try:
        topological_order(node_ids, edges)
    except TaskCycleError:
        return True
    return False


def would_create_cycle(
    node_ids: Iterable[int],
    edges: Iterable[DepEdge],
    new_edge: DepEdge,
) -> bool:
    if new_edge.predecessor_id == new_edge.successor_id:
        return True
    return has_cycle(node_ids, list(edges) + [new_edge])


def descendants(root_id: int, edges: Iterable[DepEdge]) -> List[int]:
    outgoing, _ = build_adjacency(edges)
    seen: Set[int] = set()
    queue = deque([root_id])
    while queue:
        current = queue.popleft()
        for edge in outgoing.get(current, ()):
            if edge.successor_id not in seen:
                seen.add(edge.successor_id)
                queue.append(edge.successor_id)
    seen.discard(root_id)
    return sorted(seen)


def compute_depths(node_ids: Iterable[int], edges: Iterable[DepEdge]) -> Dict[int, int]:
    order = topological_order(node_ids, edges)
    _, incoming = build_adjacency(edges)
    depth: Dict[int, int] = {node_id: 0 for node_id in order}
    for node_id in order:
        for edge in incoming.get(node_id, ()):
            if edge.predecessor_id in depth:
                depth[node_id] = max(depth[node_id], depth[edge.predecessor_id] + 1)
    return depth


def compute_schedule(
    nodes: Sequence[TaskNode],
    edges: Sequence[DepEdge],
    project_start: Optional[date] = None,
) -> ScheduleResult:
    if not nodes:
        return ScheduleResult(project_start=project_start, project_finish=project_start)

    by_id = {node.id: node for node in nodes}
    node_ids = list(by_id)
    valid_edges = [
        edge
        for edge in edges
        if edge.predecessor_id in by_id and edge.successor_id in by_id
    ]
    order = topological_order(node_ids, valid_edges)
    outgoing, incoming = build_adjacency(valid_edges)

    origin = min(node.start_date for node in nodes)
    if project_start is not None:
        origin = min(origin, project_start)

    def to_idx(value: date) -> int:
        return (value - origin).days

    def to_date(value: int) -> date:
        return origin + timedelta(days=value)

    duration = {node_id: by_id[node_id].duration_days for node_id in node_ids}

    es: Dict[int, int] = {}
    ef: Dict[int, int] = {}
    for node_id in order:
        earliest = to_idx(by_id[node_id].start_date)
        for edge in incoming.get(node_id, ()):
            earliest = max(earliest, ef[edge.predecessor_id] + 1 + edge.lag_days)
        es[node_id] = earliest
        ef[node_id] = earliest + duration[node_id] - 1

    project_finish_idx = max(ef.values())

    ls: Dict[int, int] = {}
    lf: Dict[int, int] = {}
    for node_id in reversed(order):
        successors = outgoing.get(node_id, ())
        if successors:
            latest = min(
                ls[edge.successor_id] - 1 - edge.lag_days for edge in successors
            )
        else:
            latest = project_finish_idx
        lf[node_id] = latest
        ls[node_id] = latest - duration[node_id] + 1

    depths = compute_depths(node_ids, valid_edges)

    tasks: Dict[int, TaskSchedule] = {}
    for node_id in order:
        slack = ls[node_id] - es[node_id]
        tasks[node_id] = TaskSchedule(
            task_id=node_id,
            earliest_start=to_date(es[node_id]),
            earliest_finish=to_date(ef[node_id]),
            latest_start=to_date(ls[node_id]),
            latest_finish=to_date(lf[node_id]),
            slack_days=slack,
            is_critical=slack <= 0,
            depth=depths.get(node_id, 0),
        )

    critical_path = _longest_chain(order, incoming, ef, es, duration)

    return ScheduleResult(
        tasks=tasks,
        critical_path=critical_path,
        critical_path_days=sum(duration[node_id] for node_id in critical_path),
        project_start=to_date(min(es.values())),
        project_finish=to_date(project_finish_idx),
    )


def _longest_chain(
    order: List[int],
    incoming: Dict[int, List[DepEdge]],
    ef: Dict[int, int],
    es: Dict[int, int],
    duration: Dict[int, int],
) -> List[int]:
    if not order:
        return []
    end_node = max(order, key=lambda node_id: (ef[node_id], duration[node_id]))
    chain = [end_node]
    current = end_node
    while True:
        tight = [
            edge
            for edge in incoming.get(current, ())
            if ef[edge.predecessor_id] + 1 + edge.lag_days == es[current]
        ]
        if not tight:
            break
        best = max(tight, key=lambda edge: ef[edge.predecessor_id])
        current = best.predecessor_id
        if current in chain:
            break
        chain.append(current)
    chain.reverse()
    return chain


def critical_edges(
    schedule: ScheduleResult, edges: Sequence[DepEdge]
) -> Set[Tuple[int, int]]:
    path = schedule.critical_path
    pairs = {(path[i], path[i + 1]) for i in range(len(path) - 1)}
    return {
        (edge.predecessor_id, edge.successor_id)
        for edge in edges
        if (edge.predecessor_id, edge.successor_id) in pairs
    }


def find_violations(
    nodes: Sequence[TaskNode], edges: Sequence[DepEdge]
) -> List[Violation]:
    by_id = {node.id: node for node in nodes}
    result: List[Violation] = []
    for edge in edges:
        predecessor = by_id.get(edge.predecessor_id)
        successor = by_id.get(edge.successor_id)
        if predecessor is None or successor is None:
            continue
        required = predecessor.end_date + timedelta(days=1 + edge.lag_days)
        if successor.start_date < required:
            result.append(
                Violation(
                    edge=edge,
                    required_start=required,
                    actual_start=successor.start_date,
                )
            )
    return result


def cascade_shift(
    nodes: Sequence[TaskNode],
    edges: Sequence[DepEdge],
    changed: Dict[int, Tuple[date, date]],
) -> List[ShiftedTask]:
    by_id = {node.id: node for node in nodes}
    valid_edges = [
        edge
        for edge in edges
        if edge.predecessor_id in by_id and edge.successor_id in by_id
    ]
    order = topological_order(list(by_id), valid_edges)
    _, incoming = build_adjacency(valid_edges)

    current: Dict[int, Tuple[date, date]] = {
        node.id: (node.start_date, node.end_date) for node in nodes
    }
    for task_id, dates in changed.items():
        if task_id in current:
            current[task_id] = dates

    shifted: List[ShiftedTask] = []
    for node_id in order:
        if node_id in changed:
            continue
        start, end = current[node_id]
        required_start = start
        for edge in incoming.get(node_id, ()):
            predecessor_end = current[edge.predecessor_id][1]
            required_start = max(
                required_start, predecessor_end + timedelta(days=1 + edge.lag_days)
            )
        if required_start > start:
            length = (end - start).days
            new_start = required_start
            new_end = required_start + timedelta(days=length)
            current[node_id] = (new_start, new_end)
            shifted.append(
                ShiftedTask(
                    task_id=node_id,
                    old_start=start,
                    old_end=end,
                    new_start=new_start,
                    new_end=new_end,
                )
            )
    return shifted


def projected_finish(
    nodes: Sequence[TaskNode],
    changed: Optional[Dict[int, Tuple[date, date]]] = None,
    shifted: Optional[Sequence[ShiftedTask]] = None,
) -> Optional[date]:
    if not nodes:
        return None
    dates = {node.id: node.end_date for node in nodes}
    for task_id, (_, end) in (changed or {}).items():
        dates[task_id] = end
    for item in shifted or ():
        dates[item.task_id] = item.new_end
    return max(dates.values())
