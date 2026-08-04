import pytest
from fastapi import status
from sqlalchemy import func, select

from app.models.tasks import Task
from app.schema.tasks import TaskStatus
from tests import factories


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


def test_list_tasks_other_user(authenticated_client, client):
    other_user = factories.UserFactory()
    other_token = factories.TokenFactory(user=other_user)
    factories.TaskFactory.create_batch(3, user=other_user)

    response1 = authenticated_client.get("/tasks/")
    assert response1.status_code == status.HTTP_200_OK
    response_data1 = response1.json()
    assert response_data1["total"] == 0
    assert not response_data1["data"]

    response2 = client.get(
        "/tasks/",
        headers={"Authorization": f"Bearer {other_token.key}"},
    )
    assert response2.status_code == status.HTTP_200_OK
    response_data2 = response2.json()
    assert response_data2["total"] == 3
    assert response_data2["data"]


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
    factories.TaskFactory.create(user=authenticated_user, title="SEARCH 1")
    factories.TaskFactory.create(user=authenticated_user, title="search 2")
    factories.TaskFactory.create(user=authenticated_user, title="has search in title")
    factories.TaskFactory.create_batch(3, user=authenticated_user, title="Other")

    response = authenticated_client.get("/tasks/", params={"search": "search"})
    assert response.status_code == status.HTTP_200_OK

    response_data = response.json()
    assert response_data["total"] == 3
    assert len(response_data["data"]) == 3
    for task in response_data["data"]:
        assert "search" in task["title"].lower()


def test_list_tasks_filter_by_status(authenticated_client, authenticated_user):
    for task_status in [TaskStatus.DONE, TaskStatus.PENDING, TaskStatus.CANCELLED]:
        factories.TaskFactory.create_batch(
            3, user=authenticated_user, status=task_status
        )

    response = authenticated_client.get(
        "/tasks/", params={"status": TaskStatus.PENDING}
    )
    assert response.status_code == status.HTTP_200_OK

    response_data = response.json()
    assert response_data["total"] == 3
    assert len(response_data["data"]) == 3
    for task in response_data["data"]:
        assert task["status"] == TaskStatus.PENDING


def test_list_tasks_filter_by_multiple_status(authenticated_client, authenticated_user):
    for task_status in [TaskStatus.DONE, TaskStatus.PENDING, TaskStatus.CANCELLED]:
        factories.TaskFactory.create_batch(
            3, user=authenticated_user, status=task_status
        )

    query_params = {"status": [TaskStatus.DONE, TaskStatus.CANCELLED]}
    response = authenticated_client.get("/tasks/", params=query_params)
    assert response.status_code == status.HTTP_200_OK

    response_data = response.json()
    assert response_data["total"] == 6
    assert len(response_data["data"]) == 6
    for task in response_data["data"]:
        assert task["status"] in [TaskStatus.DONE, TaskStatus.CANCELLED]


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


def test_get_task_not_found(authenticated_client):
    response = authenticated_client.get("/tasks/999")
    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_get_task_other_user(authenticated_client):
    other_user = factories.UserFactory()
    other_task = factories.TaskFactory(user=other_user)

    response = authenticated_client.get(f"/tasks/{other_task.id}")
    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_update_task(authenticated_client, authenticated_user):
    task = factories.TaskFactory(user=authenticated_user)
    update_data = {
        "title": "new title",
        "description": None,
        "status": "done",
    }
    response = authenticated_client.put(f"/tasks/{task.id}", json=update_data)
    assert response.status_code == status.HTTP_200_OK

    response_data = response.json()
    assert response_data["title"] == update_data["title"]
    assert response_data["description"] == update_data["description"]
    assert response_data["status"] == update_data["status"]


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


def test_update_task_not_found(authenticated_client):
    update_data = {
        "title": "new title",
        "description": None,
        "status": "done",
    }
    response = authenticated_client.put("/tasks/999", json=update_data)
    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_update_task_other_user(authenticated_client):
    other_user = factories.UserFactory()
    other_task = factories.TaskFactory(user=other_user)
    update_data = {
        "title": "new title",
        "description": None,
        "status": "done",
    }

    response = authenticated_client.put(f"/tasks/{other_task.id}", json=update_data)
    assert response.status_code == status.HTTP_404_NOT_FOUND


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


def test_partial_update_task_not_found(authenticated_client):
    response = authenticated_client.patch("/tasks/999", json={"title": "new title"})
    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_partial_update_task_other_user(authenticated_client):
    other_user = factories.UserFactory()
    other_task = factories.TaskFactory(user=other_user)

    response = authenticated_client.patch(
        f"/tasks/{other_task.id}", json={"title": "new title"}
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_delete_task(authenticated_client, authenticated_user, test_db_session):
    task = factories.TaskFactory(user=authenticated_user)
    response = authenticated_client.delete(f"/tasks/{task.id}")
    assert response.status_code == status.HTTP_204_NO_CONTENT

    task_count = test_db_session.scalar(select(func.count(Task.id)))
    assert task_count == 0


def test_delete_task_not_found(authenticated_client):
    response = authenticated_client.delete("/tasks/999")
    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_delete_task_other_user(authenticated_client):
    other_user = factories.UserFactory()
    other_task = factories.TaskFactory(user=other_user)

    response = authenticated_client.delete(f"/tasks/{other_task.id}")
    assert response.status_code == status.HTTP_404_NOT_FOUND
