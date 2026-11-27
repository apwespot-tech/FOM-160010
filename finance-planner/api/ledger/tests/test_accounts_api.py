from collections.abc import Callable
from http import HTTPStatus

from django.http import HttpResponse
import pytest

from ledger.models import Account, Category
from ledger.tests.factories import make_account, make_operation, make_transfer, read_errors, read_messages
from users.models import User

pytestmark = pytest.mark.django_db

JsonSender = Callable[..., HttpResponse]

ACCOUNTS_URL = "/api/accounts"


def build_account_url(account: Account) -> str:
    return f"{ACCOUNTS_URL}/{account.id}"


@pytest.mark.usefixtures("signed_in_user")
def test_create_account_returns_balance(send_json: JsonSender) -> None:
    response = send_json("POST", ACCOUNTS_URL, {"name": "Карта", "kind": "card", "initial_balance": "15000"})
    body = response.json()
    created_account = Account.objects.get(id=body["id"])

    assert response.status_code == HTTPStatus.CREATED
    assert body["name"] == "Карта"
    assert body["kind"] == "card"
    assert body["currency"] == "RUB"
    assert body["initial_balance"] == "15000.00"
    assert body["balance"] == "15000.00"
    assert body["is_archived"] is False
    assert body["created_at"].endswith("Z")
    assert created_account.user.username == "anna"


@pytest.mark.usefixtures("signed_in_user")
def test_create_account_uses_defaults_and_trims_name(send_json: JsonSender) -> None:
    response = send_json("POST", ACCOUNTS_URL, {"name": "  Наличные  ", "kind": "cash"})
    body = response.json()

    assert response.status_code == HTTPStatus.CREATED
    assert body["name"] == "Наличные"
    assert body["currency"] == "RUB"
    assert body["initial_balance"] == "0.00"


@pytest.mark.usefixtures("signed_in_user")
def test_create_account_accepts_negative_initial_balance(send_json: JsonSender) -> None:
    response = send_json("POST", ACCOUNTS_URL, {"name": "Кредитка", "kind": "card", "initial_balance": "-250.5"})

    assert response.status_code == HTTPStatus.CREATED
    assert response.json()["balance"] == "-250.50"


@pytest.mark.usefixtures("signed_in_user")
@pytest.mark.parametrize(
    ("changes", "expected_error"),
    [
        ({"initial_balance": 100}, ("initial_balance", "planner_format")),
        ({"initial_balance": "1 000"}, ("initial_balance", "planner_format")),
        ({"initial_balance": "+5"}, ("initial_balance", "planner_format")),
        ({"initial_balance": "1e3"}, ("initial_balance", "planner_format")),
        ({"initial_balance": "12,50"}, ("initial_balance", "planner_format")),
        ({"initial_balance": "12.345"}, ("initial_balance", "planner_format")),
        ({"initial_balance": "1234567890123"}, ("initial_balance", "planner_format")),
        ({"kind": "deposit"}, ("kind", "literal_error")),
        ({"name": "   "}, ("name", "string_too_short")),
        ({"name": "к" * 101}, ("name", "string_too_long")),
        ({"name": "Ка\x00рта"}, ("name", "planner_format")),
        ({"currency": "usd"}, ("currency", "planner_format")),
        ({"user_id": 2}, ("user_id", "extra_forbidden")),
    ],
    ids=[
        "amount-number",
        "amount-space",
        "amount-plus",
        "amount-exponent",
        "amount-comma",
        "amount-three-decimals",
        "amount-too-long",
        "kind",
        "blank-name",
        "long-name",
        "null-character",
        "currency-format",
        "extra-field",
    ],
)
def test_create_account_rejects_invalid_input(send_json: JsonSender, changes: dict[str, object], expected_error: tuple[str, str]) -> None:
    body = {"name": "Карта", "kind": "card"} | changes
    response = send_json("POST", ACCOUNTS_URL, body)

    assert response.status_code == HTTPStatus.UNPROCESSABLE_CONTENT
    assert response.json()["code"] == "validation_error"
    assert read_errors(response) == [expected_error]
    assert not Account.objects.exists()


@pytest.mark.usefixtures("signed_in_user")
def test_create_account_requires_kind(send_json: JsonSender) -> None:
    response = send_json("POST", ACCOUNTS_URL, {"name": "Карта"})

    assert response.status_code == HTTPStatus.UNPROCESSABLE_CONTENT
    assert read_errors(response) == [("kind", "missing")]


@pytest.mark.usefixtures("signed_in_user")
def test_create_account_in_foreign_currency_is_rejected(send_json: JsonSender) -> None:
    response = send_json("POST", ACCOUNTS_URL, {"name": "Доллары", "kind": "cash", "currency": "USD"})

    assert response.status_code == HTTPStatus.UNPROCESSABLE_CONTENT
    assert read_errors(response) == [("currency", "planner_rule")]
    assert read_messages(response) == {"currency": "Пока счёт можно открыть только в рублях"}


def test_list_accounts_returns_balances_and_total(
    send_json: JsonSender,
    signed_in_user: User,
    card_account: Account,
    foreign_account: Account,
    groceries: Category,
    salary: Category,
) -> None:
    savings_account = make_account(signed_in_user, name="Копилка", kind="savings", initial_balance="50.00", is_archived=True)
    make_operation(card_account, salary, "500.00")
    make_operation(card_account, groceries, "120.50")
    make_operation(card_account, groceries, "79.50")
    make_transfer(card_account, savings_account, "300.00")
    make_operation(foreign_account, groceries, "999.00")
    response = send_json("GET", ACCOUNTS_URL)
    balances = {item["name"]: item["balance"] for item in response.json()["items"]}

    assert response.status_code == HTTPStatus.OK
    assert balances == {"Карта": "1000.00", "Копилка": "350.00"}
    assert response.json()["total_balance"] == "1350.00"


@pytest.mark.usefixtures("signed_in_user")
def test_list_accounts_without_accounts_is_empty(send_json: JsonSender) -> None:
    response = send_json("GET", ACCOUNTS_URL)

    assert response.status_code == HTTPStatus.OK
    assert response.json() == {"items": [], "total_balance": "0.00"}


@pytest.mark.usefixtures("signed_in_user")
def test_read_account_returns_balance(send_json: JsonSender, card_account: Account, groceries: Category) -> None:
    make_operation(card_account, groceries, "0.01")
    response = send_json("GET", build_account_url(card_account))

    assert response.status_code == HTTPStatus.OK
    assert response.json()["balance"] == "999.99"


@pytest.mark.usefixtures("signed_in_user")
def test_update_account_changes_allowed_fields(send_json: JsonSender, card_account: Account, groceries: Category) -> None:
    make_operation(card_account, groceries, "100.00")
    body = {"name": "Старая карта", "initial_balance": "500", "is_archived": True}
    response = send_json("PATCH", build_account_url(card_account), body)
    card_account.refresh_from_db()

    assert response.status_code == HTTPStatus.OK
    assert response.json()["balance"] == "400.00"
    assert response.json()["is_archived"] is True
    assert card_account.name == "Старая карта"


@pytest.mark.usefixtures("signed_in_user")
def test_update_account_with_empty_body_changes_nothing(send_json: JsonSender, card_account: Account) -> None:
    response = send_json("PATCH", build_account_url(card_account), {})

    assert response.status_code == HTTPStatus.OK
    assert response.json()["name"] == "Карта"


@pytest.mark.usefixtures("signed_in_user")
@pytest.mark.parametrize(
    ("body", "expected_error"),
    [
        ({"kind": "cash"}, ("kind", "extra_forbidden")),
        ({"currency": "RUB"}, ("currency", "extra_forbidden")),
        ({"is_archived": "true"}, ("is_archived", "bool_type")),
        ({"name": None}, ("name", "string_type")),
    ],
    ids=["kind", "currency", "flag-string", "null-name"],
)
def test_update_account_rejects_invalid_input(
    send_json: JsonSender,
    card_account: Account,
    body: dict[str, object],
    expected_error: tuple[str, str],
) -> None:
    response = send_json("PATCH", build_account_url(card_account), body)

    assert response.status_code == HTTPStatus.UNPROCESSABLE_CONTENT
    assert read_errors(response) == [expected_error]


@pytest.mark.usefixtures("signed_in_user")
def test_delete_unused_account(send_json: JsonSender, card_account: Account) -> None:
    response = send_json("DELETE", build_account_url(card_account))

    assert response.status_code == HTTPStatus.NO_CONTENT
    assert response.content == b""
    assert not Account.objects.filter(id=card_account.id).exists()


@pytest.mark.usefixtures("signed_in_user")
def test_delete_account_with_operations_is_refused(send_json: JsonSender, card_account: Account, groceries: Category) -> None:
    make_operation(card_account, groceries)
    response = send_json("DELETE", build_account_url(card_account))

    assert response.status_code == HTTPStatus.CONFLICT
    assert response.json() == {"code": "account_in_use", "detail": "Счёт нельзя удалить: на него ссылаются операции. Его можно перенести в архив"}
    assert Account.objects.filter(id=card_account.id).exists()


@pytest.mark.usefixtures("signed_in_user")
@pytest.mark.parametrize("method", ["GET", "PATCH", "DELETE"])
def test_foreign_account_is_not_found(send_json: JsonSender, foreign_account: Account, method: str) -> None:
    body = {} if method == "PATCH" else None
    response = send_json(method, build_account_url(foreign_account), body)

    assert response.status_code == HTTPStatus.NOT_FOUND
    assert response.json() == {"code": "not_found", "detail": "Объект не найден"}
    assert Account.objects.filter(id=foreign_account.id).exists()


@pytest.mark.usefixtures("signed_in_user")
def test_account_id_must_be_integer(send_json: JsonSender) -> None:
    response = send_json("GET", f"{ACCOUNTS_URL}/abc")

    assert response.status_code == HTTPStatus.UNPROCESSABLE_CONTENT
    assert read_errors(response) == [("account_id", "int_parsing")]
