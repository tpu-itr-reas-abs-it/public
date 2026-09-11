from datetime import date

import pytest

from app.core.exceptions import TaskCycleError
from app.services.scheduling import (
    DepEdge,
    TaskNode,
    cascade_shift,
    compute_schedule,
    descendants,
    find_violations,
    has_cycle,
    projected_finish,
    topological_order,
    would_create_cycle,
)


def d(day: int) -> date:
    return date(2026, 1, day)


@pytest.fixture
def chain():
    nodes = [
        TaskNode(1, d(1), d(5)),
        TaskNode(2, d(6), d(10)),
        TaskNode(3, d(11), d(20)),
        TaskNode(4, d(21), d(25)),
    ]
    edges = [DepEdge(1, 2), DepEdge(2, 3), DepEdge(3, 4)]
    return nodes, edges


def test_topological_order_respects_dependencies(chain):
    _, edges = chain
    order = topological_order([1, 2, 3, 4], edges)
    assert order.index(1) < order.index(2) < order.index(3) < order.index(4)


def test_cycle_is_detected():
    edges = [DepEdge(1, 2), DepEdge(2, 3), DepEdge(3, 1)]
    assert has_cycle([1, 2, 3], edges) is True
    with pytest.raises(TaskCycleError):
        topological_order([1, 2, 3], edges)


def test_cycle_error_reports_involved_tasks():
    edges = [DepEdge(1, 2), DepEdge(2, 1)]
    with pytest.raises(TaskCycleError) as exc:
        topological_order([1, 2], edges)
    assert exc.value.details["tasks_in_cycle"] == [1, 2]


def test_would_create_cycle_rejects_closing_edge(chain):
    _, edges = chain
    assert would_create_cycle([1, 2, 3, 4], edges, DepEdge(4, 1)) is True
    assert would_create_cycle([1, 2, 3, 4], edges, DepEdge(1, 4)) is False


def test_self_dependency_is_a_cycle():
    assert would_create_cycle([1], [], DepEdge(1, 1)) is True


def test_diamond_graph_is_acyclic():
    edges = [DepEdge(1, 2), DepEdge(1, 3), DepEdge(2, 4), DepEdge(3, 4)]
    assert has_cycle([1, 2, 3, 4], edges) is False


def test_descendants_returns_transitive_successors(chain):
    _, edges = chain
    assert descendants(1, edges) == [2, 3, 4]
    assert descendants(3, edges) == [4]
    assert descendants(4, edges) == []


def test_full_chain_is_critical(chain):
    nodes, edges = chain
    schedule = compute_schedule(nodes, edges)
    assert schedule.critical_path == [1, 2, 3, 4]
    assert all(item.is_critical for item in schedule.tasks.values())
    assert schedule.project_finish == d(25)


def test_parallel_branch_gets_slack():
    nodes = [
        TaskNode(1, d(1), d(5)),
        TaskNode(2, d(6), d(10)),
        TaskNode(3, d(6), d(8)),
        TaskNode(4, d(11), d(15)),
    ]
    edges = [DepEdge(1, 2), DepEdge(1, 3), DepEdge(2, 4), DepEdge(3, 4)]
    schedule = compute_schedule(nodes, edges)

    assert schedule.tasks[2].slack_days == 0
    assert schedule.tasks[3].slack_days == 2
    assert schedule.critical_path == [1, 2, 4]
    assert 3 not in schedule.critical_path


def test_lag_days_shift_earliest_start():
    nodes = [TaskNode(1, d(1), d(5)), TaskNode(2, d(6), d(10))]
    edges = [DepEdge(1, 2, lag_days=3)]
    schedule = compute_schedule(nodes, edges)
    assert schedule.tasks[2].earliest_start == d(9)


def test_empty_project_returns_empty_schedule():
    schedule = compute_schedule([], [])
    assert schedule.tasks == {}
    assert schedule.critical_path == []


def test_single_task_is_its_own_critical_path():
    schedule = compute_schedule([TaskNode(7, d(1), d(3))], [])
    assert schedule.critical_path == [7]
    assert schedule.critical_path_days == 3


def test_cascade_shift_propagates_along_chain(chain):
    nodes, edges = chain
    shifted = cascade_shift(nodes, edges, {1: (d(1), d(8))})
    by_id = {item.task_id: item for item in shifted}

    assert set(by_id) == {2, 3, 4}
    assert all(item.shift_days == 3 for item in by_id.values())
    assert by_id[2].new_start == d(9)
    assert by_id[4].new_end == d(28)


def test_cascade_shift_preserves_duration(chain):
    nodes, edges = chain
    shifted = cascade_shift(nodes, edges, {1: (d(1), d(12))})
    for item in shifted:
        assert (item.new_end - item.new_start).days == (
            item.old_end - item.old_start
        ).days


def test_cascade_shift_does_not_pull_tasks_earlier(chain):
    nodes, edges = chain
    assert cascade_shift(nodes, edges, {1: (d(1), d(2))}) == []


def test_projected_finish_accounts_for_cascade(chain):
    nodes, edges = chain
    changed = {1: (d(1), d(8))}
    shifted = cascade_shift(nodes, edges, changed)
    assert projected_finish(nodes, changed, shifted) == d(28)


def test_violations_detect_broken_links():
    nodes = [TaskNode(1, d(1), d(10)), TaskNode(2, d(5), d(8))]
    violations = find_violations(nodes, [DepEdge(1, 2)])
    assert len(violations) == 1
    assert violations[0].required_start == d(11)
    assert violations[0].days == 6
