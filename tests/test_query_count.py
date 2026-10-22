from sqlalchemy import event

from app.models import Tag, Task


def test_list_tasks_query_count_does_not_grow_with_tasks(client, db_session):
    # 할 일이 여러 개여도 GET /tasks 는 할 일 1번, 태그 1번만 조회해야 합니다(N+1 회귀 방지).
    tags = [Tag(name=name) for name in ["업무", "개인", "긴급"]]
    db_session.add_all(
        [Task(title=f"할 일 {i}", tags=tags[: i % 3 + 1]) for i in range(10)]
    )
    db_session.commit()
    # 세션에 남은 태그를 비워, 응답을 만들 때 실제로 다시 조회하게 합니다.
    db_session.expunge_all()

    statements: list[str] = []

    def count(conn, cursor, statement, parameters, context, executemany):
        statements.append(statement)

    engine = db_session.get_bind()
    event.listen(engine, "before_cursor_execute", count)
    try:
        res = client.get("/tasks")
    finally:
        event.remove(engine, "before_cursor_execute", count)

    assert res.status_code == 200
    assert len(res.json()) == 10
    assert all(task["tags"] for task in res.json())
    assert len(statements) == 2
