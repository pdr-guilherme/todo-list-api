from datetime import datetime, timedelta

import pytest
from fastapi import status
from sqlalchemy import func, select

from app.models.tasks import Task
from app.schema.tasks import TaskStatus
from tests import factories

VALID_UPDATE_PAYLOAD = {
    "title": "new title",
    "description": None,
    "status": TaskStatus.DONE,
}


@pytest.fixture
def other_user_task():
    other_user = factories.UserFactory()
    return factories.TaskFactory(user=other_user)


@pytest.fixture
def tasks_with_all_statuses(authenticated_user):
    for task_status in TaskStatus:
        factories.TaskFactory.create_batch(
            3, user=authenticated_user, status=task_status
        )


def test_create_task(authenticated_client):
    data = {
        "title": "Buy groceries",
        "description": "Buy milk, eggs, and bread",
        "status": "pending",
    }

    response = authenticated_client.post("/tasks/", json=data)
    assert response.status_code == status.HTTP_201_CREATED

    response_json = response.json()
    assert "id" in response_json
    assert response_json["title"] == data["title"]
    assert response_json["description"] == data["description"]


def test_create_task_optional_fields(authenticated_client):
    response = authenticated_client.post("/tasks/", json={"title": "Buy groceries"})
    assert response.status_code == status.HTTP_201_CREATED


def test_create_task_not_authenticated(client):
    data = {
        "title": "Buy groceries",
        "description": "Buy milk, eggs, and bread",
        "status": "pending",
    }

    response = client.post("/tasks/", json=data)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.parametrize(
    "data",
    [
        {},
        {"title": ""},
        {"description": "Buy milk, eggs, and bread", "status": "pending"},
    ],
    ids=["no_title", "empty_title", "other_fields"],
)
def test_create_task_bad_payloads(authenticated_client, data):
    response = authenticated_client.post("/tasks/", json=data)
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


def test_list_tasks(authenticated_client, authenticated_user):
    tasks = factories.TaskFactory.create_batch(5, user=authenticated_user)
    response = authenticated_client.get("/tasks/")
    assert response.status_code == status.HTTP_200_OK

    response_data = response.json()
    assert "data" in response_data
    assert "page" in response_data
    assert "limit" in response_data
    assert "total" in response_data
    assert response_data["total"] == len(tasks)
    assert len(response_data["data"]) == len(tasks)
    assert response_data["page"] == 1
    assert response_data["limit"] == 10

    returned_ids = [task["id"] for task in response_data["data"]]
    assert returned_ids == [1, 2, 3, 4, 5]


@pytest.mark.parametrize(
    "query_params",
    [
        {"page": 0},
        {"limit": 0},
        {"limit": 101},
        {"page": "abc"},
        {"limit": "xyz"},
    ],
    ids=[
        "page_less_than_1",
        "limit_less_than_1",
        "limit_higher_than_100",
        "page_not_int",
        "limit_not_int",
    ],
)
def test_list_tasks_query_params(authenticated_client, query_params):
    response = authenticated_client.get("/tasks", params=query_params)
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


def test_list_tasks_custom_limit(authenticated_client, authenticated_user):
    factories.TaskFactory.create_batch(3, user=authenticated_user)
    response = authenticated_client.get("/tasks/", params={"limit": 2})
    assert response.status_code == status.HTTP_200_OK

    response_data = response.json()
    assert response_data["limit"] == 2
    assert response_data["total"] == 3
    assert len(response_data["data"]) == 2


def test_list_tasks_custom_page(authenticated_client, authenticated_user):
    factories.TaskFactory.create_batch(3, user=authenticated_user)
    response = authenticated_client.get("/tasks/", params={"page": 99})
    assert response.status_code == status.HTTP_200_OK

    response_data = response.json()
    assert response_data["page"] == 99
    assert response_data["total"] == 3
    assert len(response_data["data"]) == 0
    assert not response_data["data"]


def test_list_tasks_search_task_title(authenticated_client, authenticated_user):
    for title in ["SEARCH 1", "search 2", "has search in title"]:
        factories.TaskFactory.create(user=authenticated_user, title=title)
    factories.TaskFactory.create_batch(3, user=authenticated_user, title="Other")

    response = authenticated_client.get("/tasks/", params={"search": "search"})
    assert response.status_code == status.HTTP_200_OK

    response_data = response.json()
    assert response_data["total"] == 3
    assert len(response_data["data"]) == 3
    for task in response_data["data"]:
        assert "search" in task["title"].lower()


def test_list_tasks_filter_by_status(authenticated_client, tasks_with_all_statuses):
    response = authenticated_client.get(
        "/tasks/", params={"status": TaskStatus.PENDING}
    )
    assert response.status_code == status.HTTP_200_OK

    response_data = response.json()
    assert response_data["total"] == 3
    assert len(response_data["data"]) == 3
    for task in response_data["data"]:
        assert task["status"] == TaskStatus.PENDING


def test_list_tasks_filter_by_multiple_status(
    authenticated_client, tasks_with_all_statuses
):
    query_params = {"status": [TaskStatus.DONE, TaskStatus.CANCELLED]}
    response = authenticated_client.get("/tasks/", params=query_params)
    assert response.status_code == status.HTTP_200_OK

    response_data = response.json()
    assert response_data["total"] == 6
    assert len(response_data["data"]) == 6
    for task in response_data["data"]:
        assert task["status"] in [TaskStatus.DONE, TaskStatus.CANCELLED]


def test_list_tasks_sort_by_title_asc(authenticated_client, authenticated_user):
    titles = ["Whale", "Crab", "Shark"]
    for title in titles:
        factories.TaskFactory(user=authenticated_user, title=title)

    response = authenticated_client.get("/tasks/", params={"sort": "title"})
    assert response.status_code == status.HTTP_200_OK

    returned_titles = [task["title"] for task in response.json()["data"]]
    assert returned_titles == sorted(titles)


def test_list_tasks_sort_by_title_desc(authenticated_client, authenticated_user):
    titles = ["Whale", "Crab", "Shark"]
    for title in titles:
        factories.TaskFactory(user=authenticated_user, title=title)

    response = authenticated_client.get(
        "/tasks/", params={"sort": "title", "order": "desc"}
    )
    assert response.status_code == status.HTTP_200_OK

    returned_titles = [task["title"] for task in response.json()["data"]]
    assert returned_titles == sorted(titles, reverse=True)


@pytest.mark.parametrize(
    "sort_field,expected_order",
    [
        ("created_at", ["Newest", "Middle", "Oldest"]),
        ("updated_at", ["Newest", "Middle", "Oldest"]),
    ],
    ids=["created_at", "updated_at"],
)
def test_list_tasks_sort_by_timestamp_desc(
    authenticated_client, authenticated_user, sort_field, expected_order
):
    now = datetime.now()
    tasks_data = [
        ("Oldest", now - timedelta(days=3)),
        ("Middle", now - timedelta(days=1)),
        ("Newest", now - timedelta(hours=1)),
    ]
    for title, timestamp in tasks_data:
        factories.TaskFactory(
            user=authenticated_user, title=title, **{sort_field: timestamp}
        )

    response = authenticated_client.get(
        "/tasks/", params={"sort": sort_field, "order": "desc"}
    )
    assert response.status_code == status.HTTP_200_OK
    returned_titles = [task["title"] for task in response.json()["data"]]
    assert returned_titles == expected_order


def test_list_tasks_invalid_sort_field(authenticated_client):
    response = authenticated_client.get("/tasks/", params={"sort": "not_a_real_field"})
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


def test_list_tasks_invalid_order_value(authenticated_client):
    response = authenticated_client.get(
        "/tasks/", params={"sort": "title", "order": "sideways"}
    )
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


def test_get_task(authenticated_client, authenticated_user):
    task = factories.TaskFactory(user=authenticated_user)
    response = authenticated_client.get(f"/tasks/{task.id}")
    assert response.status_code == status.HTTP_200_OK

    response_data = response.json()
    assert response_data["id"] == task.id
    assert response_data["title"] == task.title
    assert response_data["description"] == task.description
    assert response_data["status"] == task.status
    assert response_data["created_at"] == task.created_at.isoformat()
    assert response_data["updated_at"] == task.updated_at.isoformat()


def test_update_task(authenticated_client, authenticated_user):
    task = factories.TaskFactory(user=authenticated_user)
    response = authenticated_client.put(f"/tasks/{task.id}", json=VALID_UPDATE_PAYLOAD)
    assert response.status_code == status.HTTP_200_OK

    response_data = response.json()
    assert response_data["title"] == VALID_UPDATE_PAYLOAD["title"]
    assert response_data["description"] == VALID_UPDATE_PAYLOAD["description"]
    assert response_data["status"] == VALID_UPDATE_PAYLOAD["status"]


@pytest.mark.parametrize(
    "update_data",
    [
        {"description": "new description", "status": "done"},
        {"title": "new title", "status": "done"},
        {"title": "new title", "description": "new description"},
        {"title": "", "description": "new description", "status": "done"},
    ],
    ids=["no_title", "no_description", "no_status", "empty_title"],
)
def test_update_task_missing_fields(
    authenticated_client, authenticated_user, update_data
):
    task = factories.TaskFactory(user=authenticated_user)
    response = authenticated_client.put(f"/tasks/{task.id}", json=update_data)
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


@pytest.mark.parametrize(
    "update_data",
    [
        {"title": "new title", "description": "new description", "status": "done"},
        {"title": "new title"},
        {"description": "new description"},
        {"status": "done"},
    ],
    ids=["full_payload", "title_only", "description_only", "status_only"],
)
def test_partial_update_task(authenticated_client, authenticated_user, update_data):
    fields = ["title", "description", "status"]
    task = factories.TaskFactory(user=authenticated_user)
    response = authenticated_client.patch(f"/tasks/{task.id}", json=update_data)
    assert response.status_code == status.HTTP_200_OK

    response_data = response.json()
    non_updated_fields = [field for field in fields if field not in update_data.keys()]
    for field in fields:
        if field in non_updated_fields:
            assert response_data[field] == getattr(task, field)
        else:
            assert response_data[field] == update_data[field]


def test_delete_task(authenticated_client, authenticated_user, test_db_session):
    task = factories.TaskFactory(user=authenticated_user)
    response = authenticated_client.delete(f"/tasks/{task.id}")
    assert response.status_code == status.HTTP_204_NO_CONTENT

    task_count = test_db_session.scalar(select(func.count(Task.id)))
    assert task_count == 0


@pytest.mark.parametrize(
    "method,payload",
    [
        ("get", None),
        ("put", VALID_UPDATE_PAYLOAD),
        ("patch", {"title": "x"}),
        ("delete", None),
    ],
    ids=["get", "put", "patch", "delete"],
)
def test_task_other_user_returns_404(
    authenticated_client, other_user_task, method, payload
):
    kwargs = {"json": payload} if payload is not None else {}
    response = getattr(authenticated_client, method)(
        f"/tasks/{other_user_task.id}", **kwargs
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.parametrize(
    "method,payload",
    [
        ("get", None),
        ("put", VALID_UPDATE_PAYLOAD),
        ("patch", {"title": "x"}),
        ("delete", None),
    ],
    ids=["get", "put", "patch", "delete"],
)
def test_task_not_found_returns_404(authenticated_client, method, payload):
    kwargs = {"json": payload} if payload is not None else {}
    response = getattr(authenticated_client, method)("/tasks/999", **kwargs)
    assert response.status_code == status.HTTP_404_NOT_FOUND
