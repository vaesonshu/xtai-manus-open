"""领域层聚合根测试。"""

from domain.agent.entity import AgentRun, RunStatus
from domain.exceptions import ConflictError


def test_create_run_publishes_started_event() -> None:
    run = AgentRun.create(goal="写一个冒泡排序")
    assert run.status is RunStatus.CREATED
    events = run.pull_events()
    assert len(events) == 1
    assert events[0].name == "AgentRunStarted"


def test_full_lifecycle() -> None:
    run = AgentRun.create(goal="计算 1+1")
    run.pull_events()  # 清空 create 时产生的 AgentRunStarted
    run.start()
    run.record_progress(step=1, message="开始计算")
    run.complete(result={"answer": 2})

    assert run.status is RunStatus.COMPLETED
    assert run.result == {"answer": 2}
    assert [e.name for e in run.pull_events()] == [
        "AgentRunProgressed",
        "AgentRunCompleted",
    ]


def test_cannot_complete_before_start() -> None:
    run = AgentRun.create(goal="x")
    try:
        run.complete(result={})
    except ConflictError:
        pass
    else:
        raise AssertionError("expected ConflictError")
