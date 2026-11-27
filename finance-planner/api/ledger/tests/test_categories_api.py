from collections.abc import Callable
from http import HTTPStatus

from django.http import HttpResponse
import pytest

from ledger.models import Account, Category
from ledger.tests.factories import make_operation, read_errors, read_messages
from users.models import User

pytestmark = pytest.mark.django_db

JsonSender = Callable[..., HttpResponse]

CATEGORIES_URL = "/api/categories"
COMMON_CATEGORY_COUNT = 14
NAME_TAKEN_MESSAGE = "Категория с таким названием уже есть"


def build_category_url(category: Category) -> str:
    return f"{CATEGORIES_URL}/{category.id}"


@pytest.fixture
def hobby(user: User) -> Category:
    return Category.objects.create(user=user, name="Хобби", kind="expense")


@pytest.fixture
def foreign_category(other_user: User) -> Category:
    return Category.objects.create(user=other_user, name="Рыбалка", kind="expense")


@pytest.mark.usefixtures("signed_in_user", "foreign_category")
def test_list_categories_returns_common_and_own(send_json: JsonSender, hobby: Category) -> None:
    response = send_json("GET", CATEGORIES_URL)
    items = response.json()["items"]
    sort_keys = [(item["kind"], item["name"]) for item in items]
    own_items = [item for item in items if not item["is_common"]]

    assert response.status_code == HTTPStatus.OK
    assert len(items) == COMMON_CATEGORY_COUNT + 1
    assert sort_keys == sorted(sort_keys)
    assert own_items == [{"id": hobby.id, "name": "Хобби", "kind": "expense", "is_common": False}]


@pytest.mark.usefixtures("signed_in_user", "hobby")
def test_list_categories_filters_by_kind(send_json: JsonSender) -> None:
    response = send_json("GET", f"{CATEGORIES_URL}?kind=income")
    names = [item["name"] for item in response.json()["items"]]

    assert response.status_code == HTTPStatus.OK
    assert sorted(names) == sorted(["Зарплата", "Подарки", "Прочие доходы"])


@pytest.mark.usefixtures("signed_in_user")
def test_list_categories_rejects_unknown_kind(send_json: JsonSender) -> None:
    response = send_json("GET", f"{CATEGORIES_URL}?kind=refund")

    assert response.status_code == HTTPStatus.UNPROCESSABLE_CONTENT
    assert read_errors(response) == [("kind", "literal_error")]


@pytest.mark.usefixtures("signed_in_user")
def test_create_category(send_json: JsonSender) -> None:
    response = send_json("POST", CATEGORIES_URL, {"name": " Книги ", "kind": "expense"})
    created_category = Category.objects.get(name="Книги")

    assert response.status_code == HTTPStatus.CREATED
    assert response.json() == {"id": created_category.id, "name": "Книги", "kind": "expense", "is_common": False}
    assert created_category.user.username == "anna"


@pytest.mark.usefixtures("signed_in_user", "hobby")
@pytest.mark.parametrize(
    ("name", "kind"),
    [("Хобби", "expense"), ("Кафе", "expense"), ("Зарплата", "income")],
    ids=["own", "common-expense", "common-income"],
)
def test_create_category_rejects_taken_name(send_json: JsonSender, name: str, kind: str) -> None:
    response = send_json("POST", CATEGORIES_URL, {"name": name, "kind": kind})

    assert response.status_code == HTTPStatus.UNPROCESSABLE_CONTENT
    assert read_errors(response) == [("name", "planner_rule")]
    assert read_messages(response) == {"name": NAME_TAKEN_MESSAGE}


@pytest.mark.usefixtures("signed_in_user", "foreign_category")
@pytest.mark.parametrize(("name", "kind"), [("Кафе", "income"), ("Рыбалка", "expense")], ids=["common-of-other-kind", "other-users"])
def test_create_category_allows_name_used_elsewhere(send_json: JsonSender, name: str, kind: str) -> None:
    response = send_json("POST", CATEGORIES_URL, {"name": name, "kind": kind})

    assert response.status_code == HTTPStatus.CREATED


@pytest.mark.usefixtures("signed_in_user")
@pytest.mark.parametrize(
    ("body", "expected_error"),
    [
        ({"name": "Книги"}, ("kind", "missing")),
        ({"name": "", "kind": "expense"}, ("name", "string_too_short")),
        ({"name": "к" * 61, "kind": "expense"}, ("name", "string_too_long")),
        ({"name": "Книги", "kind": "transfer_in"}, ("kind", "literal_error")),
        ({"name": "Книги", "kind": "expense", "is_common": True}, ("is_common", "extra_forbidden")),
    ],
    ids=["missing-kind", "empty-name", "long-name", "transfer-kind", "extra-field"],
)
def test_create_category_rejects_invalid_input(send_json: JsonSender, body: dict[str, object], expected_error: tuple[str, str]) -> None:
    response = send_json("POST", CATEGORIES_URL, body)

    assert response.status_code == HTTPStatus.UNPROCESSABLE_CONTENT
    assert read_errors(response) == [expected_error]


@pytest.mark.usefixtures("signed_in_user")
def test_rename_own_category(send_json: JsonSender, hobby: Category) -> None:
    response = send_json("PATCH", build_category_url(hobby), {"name": "Книги и хобби"})
    hobby.refresh_from_db()

    assert response.status_code == HTTPStatus.OK
    assert response.json()["name"] == "Книги и хобби"
    assert hobby.name == "Книги и хобби"


@pytest.mark.usefixtures("signed_in_user")
def test_rename_category_to_common_name_is_rejected(send_json: JsonSender, hobby: Category) -> None:
    response = send_json("PATCH", build_category_url(hobby), {"name": "Кафе"})

    assert response.status_code == HTTPStatus.UNPROCESSABLE_CONTENT
    assert read_messages(response) == {"name": NAME_TAKEN_MESSAGE}


@pytest.mark.usefixtures("signed_in_user")
def test_rename_category_rejects_kind_change(send_json: JsonSender, hobby: Category) -> None:
    response = send_json("PATCH", build_category_url(hobby), {"kind": "income"})

    assert response.status_code == HTTPStatus.UNPROCESSABLE_CONTENT
    assert read_errors(response) == [("kind", "extra_forbidden")]


@pytest.mark.usefixtures("signed_in_user")
@pytest.mark.parametrize("method", ["PATCH", "DELETE"])
def test_common_category_cannot_be_changed(send_json: JsonSender, groceries: Category, method: str) -> None:
    body = {"name": "Еда"} if method == "PATCH" else None
    response = send_json(method, build_category_url(groceries), body)
    groceries.refresh_from_db()

    assert response.status_code == HTTPStatus.FORBIDDEN
    assert response.json() == {"code": "common_category", "detail": "Общую категорию нельзя изменить или удалить"}
    assert groceries.name == "Продукты"


@pytest.mark.usefixtures("signed_in_user")
def test_delete_unused_category(send_json: JsonSender, hobby: Category) -> None:
    response = send_json("DELETE", build_category_url(hobby))

    assert response.status_code == HTTPStatus.NO_CONTENT
    assert not Category.objects.filter(id=hobby.id).exists()


@pytest.mark.usefixtures("signed_in_user")
def test_delete_category_with_operations_is_refused(send_json: JsonSender, hobby: Category, card_account: Account) -> None:
    make_operation(card_account, hobby)
    response = send_json("DELETE", build_category_url(hobby))

    assert response.status_code == HTTPStatus.CONFLICT
    assert response.json()["code"] == "category_in_use"
    assert Category.objects.filter(id=hobby.id).exists()


@pytest.mark.usefixtures("signed_in_user")
@pytest.mark.parametrize("method", ["PATCH", "DELETE"])
def test_foreign_category_is_not_found(send_json: JsonSender, foreign_category: Category, method: str) -> None:
    body = {"name": "Охота"} if method == "PATCH" else None
    response = send_json(method, build_category_url(foreign_category), body)
    foreign_category.refresh_from_db()

    assert response.status_code == HTTPStatus.NOT_FOUND
    assert response.json()["code"] == "not_found"
    assert foreign_category.name == "Рыбалка"
