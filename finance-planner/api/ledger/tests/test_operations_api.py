from collections.abc import Callable
from datetime import date, timedelta
from decimal import Decimal
from http import HTTPStatus

from django.http import HttpResponse
from django.test import Client
import pytest

from ledger.models import Account, Category, Operation
from ledger.tests.factories import make_account, make_operation, make_transfer, read_errors, read_messages
from users.models import User

pytestmark = pytest.mark.django_db

JsonSender = Callable[..., HttpResponse]

OPERATIONS_URL = "/api/operations"
USER_TODAY = date(2026, 11, 21)
UTC_TODAY = date(2026, 11, 20)
PAGE_SIZE = 50
MAX_PAGE_SIZE = 100
PAGED_OPERATION_COUNT = 55


def build_operation_url(operation: Operation) -> str:
    return f"{OPERATIONS_URL}/{operation.id}"


def build_operation_body(account: Account, category: Category, **changes: object) -> dict[str, object]:
    body = {"kind": "expense", "account_id": account.id, "category_id": category.id, "amount": "1250.5", "date": "2026-11-18"}

    return body | changes


def read_item_ids(response: HttpResponse) -> list[int]:
    return [item["id"] for item in response.json()["items"]]


def build_unsaved_expense(account: Account, category: Category) -> Operation:
    return Operation(user=account.user, account=account, category=category, kind="expense", amount=Decimal("1.00"), date=date(2026, 11, 1))


@pytest.fixture
def paged_operations(card_account: Account, groceries: Category) -> list[Operation]:
    first_date = date(2026, 9, 1)
    operations = []

    for day_number in range(PAGED_OPERATION_COUNT):
        operation_date = first_date + timedelta(days=day_number)
        operations.append(make_operation(card_account, groceries, operation_date=operation_date))

    return operations


@pytest.mark.usefixtures("signed_in_user")
def test_create_operation(send_json: JsonSender, card_account: Account, groceries: Category) -> None:
    body = build_operation_body(card_account, groceries, note=" Продукты на неделю ")
    response = send_json("POST", OPERATIONS_URL, body)
    created_operation = Operation.objects.get()
    response_body = response.json()
    created_at = response_body.pop("created_at")

    expected_body = {
        "id": created_operation.id,
        "kind": "expense",
        "account_id": card_account.id,
        "category_id": groceries.id,
        "amount": "1250.50",
        "date": "2026-11-18",
        "note": "Продукты на неделю",
        "transfer_id": None,
    }

    assert response.status_code == HTTPStatus.CREATED
    assert response_body == expected_body
    assert created_at.endswith("Z")
    assert created_operation.user_id == card_account.user_id


@pytest.mark.usefixtures("signed_in_user", "frozen_now")
def test_create_operation_accepts_users_today(send_json: JsonSender, card_account: Account, groceries: Category) -> None:
    body = build_operation_body(card_account, groceries, date=USER_TODAY.isoformat())
    response = send_json("POST", OPERATIONS_URL, body)

    assert response.status_code == HTTPStatus.CREATED


@pytest.mark.usefixtures("signed_in_user", "frozen_now")
def test_create_operation_rejects_future_date(send_json: JsonSender, card_account: Account, groceries: Category) -> None:
    tomorrow = USER_TODAY + timedelta(days=1)
    body = build_operation_body(card_account, groceries, date=tomorrow.isoformat())
    response = send_json("POST", OPERATIONS_URL, body)

    assert response.status_code == HTTPStatus.UNPROCESSABLE_CONTENT
    assert read_errors(response) == [("date", "planner_rule")]
    assert read_messages(response) == {"date": "Дата не может быть позже сегодняшнего дня"}


@pytest.mark.usefixtures("frozen_now")
def test_today_depends_on_users_time_zone(csrf_client: Client, send_json: JsonSender, other_user: User, groceries: Category) -> None:
    utc_account = make_account(other_user)
    csrf_client.force_login(other_user)
    today_body = build_operation_body(utc_account, groceries, date=UTC_TODAY.isoformat())
    tomorrow_body = build_operation_body(utc_account, groceries, date=USER_TODAY.isoformat())

    assert send_json("POST", OPERATIONS_URL, today_body).status_code == HTTPStatus.CREATED
    assert send_json("POST", OPERATIONS_URL, tomorrow_body).status_code == HTTPStatus.UNPROCESSABLE_CONTENT


@pytest.mark.usefixtures("signed_in_user")
@pytest.mark.parametrize(
    ("changes", "expected_error"),
    [
        ({"amount": 1250.5}, ("amount", "planner_format")),
        ({"amount": "-5.00"}, ("amount", "planner_format")),
        ({"amount": "0"}, ("amount", "greater_than")),
        ({"amount": "0.00"}, ("amount", "greater_than")),
        ({"amount": "1250.5\n"}, ("amount", "planner_format")),
        ({"date": "18.11.2026"}, ("date", "planner_format")),
        ({"date": "2026-11-18T10:00:00"}, ("date", "planner_format")),
        ({"date": 1763424000}, ("date", "planner_format")),
        ({"date": "2026-02-30"}, ("date", "date_from_datetime_parsing")),
        ({"account_id": "3"}, ("account_id", "int_type")),
        ({"category_id": True}, ("category_id", "int_type")),
        ({"kind": "transfer_out"}, ("kind", "literal_error")),
        ({"note": "з" * 256}, ("note", "string_too_long")),
        ({"note": "\x00"}, ("note", "planner_format")),
        ({"user_id": 1}, ("user_id", "extra_forbidden")),
    ],
    ids=[
        "amount-number",
        "amount-negative",
        "amount-zero",
        "amount-zero-cents",
        "amount-newline",
        "date-format",
        "date-time",
        "date-number",
        "date-missing-day",
        "account-string",
        "category-bool",
        "transfer-kind",
        "long-note",
        "null-character",
        "extra-field",
    ],
)
def test_create_operation_rejects_invalid_input(
    send_json: JsonSender,
    card_account: Account,
    groceries: Category,
    changes: dict[str, object],
    expected_error: tuple[str, str],
) -> None:
    body = build_operation_body(card_account, groceries) | changes
    response = send_json("POST", OPERATIONS_URL, body)

    assert response.status_code == HTTPStatus.UNPROCESSABLE_CONTENT
    assert response.json()["code"] == "validation_error"
    assert read_errors(response) == [expected_error]
    assert not Operation.objects.exists()


@pytest.mark.usefixtures("signed_in_user")
def test_create_operation_requires_amount(send_json: JsonSender, card_account: Account, groceries: Category) -> None:
    body = build_operation_body(card_account, groceries)
    del body["amount"]
    response = send_json("POST", OPERATIONS_URL, body)

    assert response.status_code == HTTPStatus.UNPROCESSABLE_CONTENT
    assert read_errors(response) == [("amount", "missing")]


@pytest.mark.usefixtures("signed_in_user")
def test_create_operation_rejects_foreign_account_and_category(send_json: JsonSender, foreign_account: Account, other_user: User) -> None:
    foreign_category = Category.objects.create(user=other_user, name="Рыбалка", kind="expense")
    response = send_json("POST", OPERATIONS_URL, build_operation_body(foreign_account, foreign_category))

    assert response.status_code == HTTPStatus.UNPROCESSABLE_CONTENT
    assert read_messages(response) == {"account_id": "Счёт не найден", "category_id": "Категория не найдена"}
    assert not Operation.objects.exists()


@pytest.mark.usefixtures("signed_in_user")
def test_create_operation_rejects_missing_objects(send_json: JsonSender, card_account: Account, groceries: Category) -> None:
    body = build_operation_body(card_account, groceries, account_id=card_account.id + 1000, category_id=groceries.id + 1000)
    response = send_json("POST", OPERATIONS_URL, body)

    assert response.status_code == HTTPStatus.UNPROCESSABLE_CONTENT
    assert read_messages(response) == {"account_id": "Счёт не найден", "category_id": "Категория не найдена"}


@pytest.mark.usefixtures("signed_in_user")
def test_create_operation_rejects_archived_account(send_json: JsonSender, user: User, groceries: Category) -> None:
    archived_account = make_account(user, is_archived=True)
    response = send_json("POST", OPERATIONS_URL, build_operation_body(archived_account, groceries))

    assert response.status_code == HTTPStatus.UNPROCESSABLE_CONTENT
    assert read_messages(response) == {"account_id": "Счёт в архиве"}


@pytest.mark.usefixtures("signed_in_user")
def test_create_operation_rejects_category_of_other_kind(send_json: JsonSender, card_account: Account, salary: Category) -> None:
    response = send_json("POST", OPERATIONS_URL, build_operation_body(card_account, salary))

    assert response.status_code == HTTPStatus.UNPROCESSABLE_CONTENT
    assert read_messages(response) == {"category_id": "Вид категории не совпадает с видом операции"}


@pytest.mark.usefixtures("signed_in_user")
def test_create_income_with_own_category(send_json: JsonSender, user: User, card_account: Account) -> None:
    side_job = Category.objects.create(user=user, name="Подработка", kind="income")
    body = build_operation_body(card_account, side_job, kind="income")
    response = send_json("POST", OPERATIONS_URL, body)

    assert response.status_code == HTTPStatus.CREATED
    assert response.json()["kind"] == "income"


@pytest.mark.usefixtures("signed_in_user", "paged_operations")
@pytest.mark.parametrize(
    ("query", "expected_count"),
    [
        ("", PAGE_SIZE),
        ("?page=2", PAGED_OPERATION_COUNT - PAGE_SIZE),
        ("?page_size=10", 10),
        ("?page=3", 0),
    ],
    ids=["first-page", "second-page", "small-page", "after-end"],
)
def test_list_operations_is_paged(send_json: JsonSender, query: str, expected_count: int) -> None:
    response = send_json("GET", f"{OPERATIONS_URL}{query}")

    assert response.status_code == HTTPStatus.OK
    assert response.json()["count"] == PAGED_OPERATION_COUNT
    assert len(response.json()["items"]) == expected_count


@pytest.mark.usefixtures("signed_in_user")
def test_page_size_above_limit_is_cut_to_maximum(send_json: JsonSender, card_account: Account, groceries: Category) -> None:
    operation_count = MAX_PAGE_SIZE + 5
    operations = [build_unsaved_expense(card_account, groceries) for _ in range(operation_count)]
    Operation.objects.bulk_create(operations)
    response = send_json("GET", f"{OPERATIONS_URL}?page_size=500")

    assert response.status_code == HTTPStatus.OK
    assert response.json()["count"] == operation_count
    assert len(response.json()["items"]) == MAX_PAGE_SIZE


@pytest.mark.usefixtures("signed_in_user")
@pytest.mark.parametrize(
    ("query", "expected_error"),
    [("?page=0", ("page", "greater_than_equal")), ("?page_size=0", ("page_size", "greater_than_equal"))],
)
def test_list_operations_rejects_bad_page(send_json: JsonSender, query: str, expected_error: tuple[str, str]) -> None:
    response = send_json("GET", f"{OPERATIONS_URL}{query}")

    assert response.status_code == HTTPStatus.UNPROCESSABLE_CONTENT
    assert read_errors(response) == [expected_error]


@pytest.mark.usefixtures("signed_in_user")
def test_list_operations_sorts_by_date_then_id(send_json: JsonSender, card_account: Account, groceries: Category) -> None:
    older = make_operation(card_account, groceries, operation_date=date(2026, 11, 1))
    first_of_day = make_operation(card_account, groceries, operation_date=date(2026, 11, 5))
    second_of_day = make_operation(card_account, groceries, operation_date=date(2026, 11, 5))
    newest_first = send_json("GET", OPERATIONS_URL)
    oldest_first = send_json("GET", f"{OPERATIONS_URL}?sort=date")

    assert read_item_ids(newest_first) == [second_of_day.id, first_of_day.id, older.id]
    assert read_item_ids(oldest_first) == [older.id, first_of_day.id, second_of_day.id]


@pytest.mark.usefixtures("signed_in_user")
def test_list_operations_filters(send_json: JsonSender, user: User, card_account: Account, groceries: Category, salary: Category) -> None:
    cash_account = make_account(user, name="Наличные", kind="cash")
    early = make_operation(card_account, groceries, operation_date=date(2026, 11, 1))
    middle = make_operation(card_account, salary, operation_date=date(2026, 11, 10))
    late = make_operation(cash_account, groceries, operation_date=date(2026, 11, 20))
    transfer = make_transfer(card_account, cash_account, "50.00", operation_date=date(2026, 11, 15))
    transfer_out = transfer.operations.get(kind="transfer_out")

    period_query = f"{OPERATIONS_URL}?date_from=2026-11-01&date_to=2026-11-10&sort=date"
    account_query = f"{OPERATIONS_URL}?account_id={cash_account.id}&sort=date"
    category_query = f"{OPERATIONS_URL}?category_id={groceries.id}&sort=date"
    kind_query = f"{OPERATIONS_URL}?kind=transfer_out&unknown=1"

    assert read_item_ids(send_json("GET", period_query)) == [early.id, middle.id]
    assert read_item_ids(send_json("GET", account_query)) == [transfer.operations.get(kind="transfer_in").id, late.id]
    assert read_item_ids(send_json("GET", category_query)) == [early.id, late.id]
    assert read_item_ids(send_json("GET", kind_query)) == [transfer_out.id]


@pytest.mark.usefixtures("signed_in_user")
def test_list_operations_hides_foreign_rows(send_json: JsonSender, card_account: Account, foreign_account: Account, groceries: Category) -> None:
    own_operation = make_operation(card_account, groceries)
    make_operation(foreign_account, groceries)
    all_response = send_json("GET", OPERATIONS_URL)
    foreign_filter_response = send_json("GET", f"{OPERATIONS_URL}?account_id={foreign_account.id}")

    assert read_item_ids(all_response) == [own_operation.id]
    assert foreign_filter_response.json() == {"items": [], "count": 0}


@pytest.mark.usefixtures("signed_in_user")
@pytest.mark.parametrize(
    ("query", "expected_error"),
    [
        ("?date_from=2026-11-10&date_to=2026-11-01", ("date_to", "planner_rule")),
        ("?date_from=01.11.2026", ("date_from", "planner_format")),
        ("?kind=refund", ("kind", "literal_error")),
        ("?account_id=card", ("account_id", "int_parsing")),
        ("?sort=amount", ("sort", "literal_error")),
    ],
    ids=["reversed-period", "date-format", "kind", "account-id", "sort"],
)
def test_list_operations_rejects_bad_filters(send_json: JsonSender, query: str, expected_error: tuple[str, str]) -> None:
    response = send_json("GET", f"{OPERATIONS_URL}{query}")

    assert response.status_code == HTTPStatus.UNPROCESSABLE_CONTENT
    assert read_errors(response) == [expected_error]


@pytest.mark.usefixtures("signed_in_user")
def test_read_operation(send_json: JsonSender, card_account: Account, groceries: Category) -> None:
    operation = make_operation(card_account, groceries, "42.00")
    response = send_json("GET", build_operation_url(operation))

    assert response.status_code == HTTPStatus.OK
    assert response.json()["amount"] == "42.00"


@pytest.mark.usefixtures("signed_in_user")
def test_update_operation_changes_fields_and_balance(send_json: JsonSender, user: User, card_account: Account, groceries: Category) -> None:
    cafe = Category.objects.get(user=None, kind="expense", name="Кафе")
    cash_account = make_account(user, name="Наличные", kind="cash", initial_balance="200.00")
    operation = make_operation(card_account, groceries, "100.00")
    body = {"account_id": cash_account.id, "category_id": cafe.id, "amount": "150", "date": "2026-11-17", "note": "Обед"}
    response = send_json("PATCH", build_operation_url(operation), body)
    accounts_response = send_json("GET", "/api/accounts")
    balances = {item["name"]: item["balance"] for item in accounts_response.json()["items"]}
    changed_fields = {field_name: response.json()[field_name] for field_name in ("account_id", "category_id", "amount", "date", "note")}

    expected_fields = {"account_id": cash_account.id, "category_id": cafe.id, "amount": "150.00", "date": "2026-11-17", "note": "Обед"}

    assert response.status_code == HTTPStatus.OK
    assert changed_fields == expected_fields
    assert balances == {"Карта": "1000.00", "Наличные": "50.00"}


@pytest.mark.usefixtures("signed_in_user")
def test_update_operation_keeps_its_archived_account(send_json: JsonSender, user: User, groceries: Category) -> None:
    archived_account = make_account(user, is_archived=True)
    operation = make_operation(archived_account, groceries)
    response = send_json("PATCH", build_operation_url(operation), {"account_id": archived_account.id, "amount": "90.00"})

    assert response.status_code == HTTPStatus.OK
    assert response.json()["amount"] == "90.00"


@pytest.mark.usefixtures("signed_in_user", "frozen_now")
@pytest.mark.parametrize(
    ("field_name", "expected_message"),
    [
        ("account_id", "Счёт в архиве"),
        ("category_id", "Вид категории не совпадает с видом операции"),
        ("date", "Дата не может быть позже сегодняшнего дня"),
    ],
)
def test_update_operation_checks_new_values(
    send_json: JsonSender,
    user: User,
    card_account: Account,
    groceries: Category,
    salary: Category,
    field_name: str,
    expected_message: str,
) -> None:
    archived_account = make_account(user, name="Архив", is_archived=True)
    new_values = {"account_id": archived_account.id, "category_id": salary.id, "date": "2026-11-22"}
    operation = make_operation(card_account, groceries)
    response = send_json("PATCH", build_operation_url(operation), {field_name: new_values[field_name]})

    assert response.status_code == HTTPStatus.UNPROCESSABLE_CONTENT
    assert read_messages(response) == {field_name: expected_message}


@pytest.mark.usefixtures("signed_in_user")
def test_update_operation_rejects_kind_change(send_json: JsonSender, card_account: Account, groceries: Category) -> None:
    operation = make_operation(card_account, groceries)
    response = send_json("PATCH", build_operation_url(operation), {"kind": "income"})

    assert response.status_code == HTTPStatus.UNPROCESSABLE_CONTENT
    assert read_errors(response) == [("kind", "extra_forbidden")]


@pytest.mark.usefixtures("signed_in_user")
@pytest.mark.parametrize("method", ["PATCH", "DELETE"])
def test_transfer_operation_is_changed_only_with_transfer(send_json: JsonSender, user: User, card_account: Account, method: str) -> None:
    savings_account = make_account(user, name="Копилка", kind="savings")
    transfer = make_transfer(card_account, savings_account, "300.00")
    transfer_out = transfer.operations.get(kind="transfer_out")
    body = {"amount": "1.00"} if method == "PATCH" else None
    response = send_json(method, build_operation_url(transfer_out), body)
    transfer_out.refresh_from_db()

    assert response.status_code == HTTPStatus.CONFLICT
    assert response.json() == {"code": "transfer_operation", "detail": "Операция входит в перевод и меняется только вместе с ним"}
    assert transfer_out.amount == Decimal("300.00")


@pytest.mark.usefixtures("signed_in_user")
def test_delete_operation(send_json: JsonSender, card_account: Account, groceries: Category) -> None:
    operation = make_operation(card_account, groceries)
    response = send_json("DELETE", build_operation_url(operation))

    assert response.status_code == HTTPStatus.NO_CONTENT
    assert not Operation.objects.filter(id=operation.id).exists()


@pytest.mark.usefixtures("signed_in_user")
@pytest.mark.parametrize("method", ["GET", "PATCH", "DELETE"])
def test_foreign_operation_is_not_found(send_json: JsonSender, foreign_account: Account, groceries: Category, method: str) -> None:
    foreign_operation = make_operation(foreign_account, groceries, "77.00")
    body = {"amount": "1.00"} if method == "PATCH" else None
    response = send_json(method, build_operation_url(foreign_operation), body)
    foreign_operation.refresh_from_db()

    assert response.status_code == HTTPStatus.NOT_FOUND
    assert response.json()["code"] == "not_found"
    assert foreign_operation.amount == Decimal("77.00")


@pytest.mark.usefixtures("signed_in_user")
def test_balance_matches_operations_after_series(
    send_json: JsonSender,
    user: User,
    card_account: Account,
    groceries: Category,
    salary: Category,
) -> None:
    savings_account = make_account(user, name="Копилка", kind="savings", initial_balance="10.00")

    created_bodies = [
        build_operation_body(card_account, salary, kind="income", amount="35000"),
        build_operation_body(card_account, groceries, amount="1250.50"),
        build_operation_body(card_account, groceries, amount="0.01"),
        build_operation_body(savings_account, groceries, amount="5.99"),
    ]

    for body in created_bodies:
        assert send_json("POST", OPERATIONS_URL, body).status_code == HTTPStatus.CREATED

    make_transfer(card_account, savings_account, "4000.00")
    response = send_json("GET", "/api/accounts")
    balances = {item["name"]: Decimal(item["balance"]) for item in response.json()["items"]}
    expected_balances = {}

    # Независимый пересчёт по строкам операций, без агрегата из модели
    for account in (card_account, savings_account):
        incoming = sum(operation.amount for operation in account.operations.filter(kind__in=["income", "transfer_in"]))
        outgoing = sum(operation.amount for operation in account.operations.filter(kind__in=["expense", "transfer_out"]))
        expected_balances[account.name] = account.initial_balance + incoming - outgoing

    assert balances == expected_balances
    assert balances == {"Карта": Decimal("30749.49"), "Копилка": Decimal("4004.01")}
    assert Decimal(response.json()["total_balance"]) == sum(expected_balances.values())


@pytest.mark.usefixtures("signed_in_user")
def test_update_operation_rejects_foreign_and_missing_references(
    send_json: JsonSender,
    card_account: Account,
    foreign_account: Account,
    groceries: Category,
    other_user: User,
) -> None:
    foreign_category = Category.objects.create(user=other_user, name="Рыбалка", kind="expense")
    operation = make_operation(card_account, groceries)
    foreign_body = {"account_id": foreign_account.id, "category_id": foreign_category.id}
    foreign_response = send_json("PATCH", build_operation_url(operation), foreign_body)
    missing_body = {"account_id": card_account.id + 1000, "category_id": groceries.id + 1000}
    missing_response = send_json("PATCH", build_operation_url(operation), missing_body)
    operation.refresh_from_db()

    assert foreign_response.status_code == HTTPStatus.UNPROCESSABLE_CONTENT
    assert read_messages(foreign_response) == {"account_id": "Счёт не найден", "category_id": "Категория не найдена"}
    assert read_messages(missing_response) == {"account_id": "Счёт не найден", "category_id": "Категория не найдена"}
    assert operation.account_id == card_account.id
    assert operation.category_id == groceries.id


@pytest.mark.usefixtures("signed_in_user")
def test_update_operation_keeps_account_currency(send_json: JsonSender, user: User, card_account: Account, groceries: Category) -> None:
    # Счёт в валюте API пока не открывает, поэтому он создаётся напрямую, как появится после загрузки курсов
    dollar_account = Account.objects.create(user=user, name="Доллары", kind="cash", currency="USD")
    operation = make_operation(card_account, groceries)
    response = send_json("PATCH", build_operation_url(operation), {"account_id": dollar_account.id})

    assert response.status_code == HTTPStatus.UNPROCESSABLE_CONTENT
    assert read_messages(response) == {"account_id": "Счёт можно сменить только на счёт в той же валюте"}


@pytest.mark.usefixtures("signed_in_user")
def test_update_operation_with_empty_body_changes_nothing(send_json: JsonSender, card_account: Account, groceries: Category) -> None:
    operation = make_operation(card_account, groceries, "42.00", note="Хлеб")
    response = send_json("PATCH", build_operation_url(operation), {})
    operation.refresh_from_db()

    assert response.status_code == HTTPStatus.OK
    assert response.json()["amount"] == "42.00"
    assert operation.note == "Хлеб"


@pytest.mark.usefixtures("signed_in_user")
@pytest.mark.parametrize(
    ("query", "expected_dates"),
    [("?date_from=2026-11-10", ["2026-11-20", "2026-11-10"]), ("?date_to=2026-11-10", ["2026-11-10", "2026-11-01"])],
    ids=["from-only", "to-only"],
)
def test_list_operations_accepts_one_period_boundary(
    send_json: JsonSender,
    card_account: Account,
    groceries: Category,
    query: str,
    expected_dates: list[str],
) -> None:
    for operation_date in (date(2026, 11, 1), date(2026, 11, 10), date(2026, 11, 20)):
        make_operation(card_account, groceries, operation_date=operation_date)

    response = send_json("GET", f"{OPERATIONS_URL}{query}")
    dates = [item["date"] for item in response.json()["items"]]

    assert response.status_code == HTTPStatus.OK
    assert dates == expected_dates


@pytest.mark.usefixtures("signed_in_user")
def test_list_operations_page_far_beyond_end_is_empty(send_json: JsonSender, card_account: Account, groceries: Category) -> None:
    # Без своей пагинации такой номер давал OFFSET больше bigint и ответ 500
    make_operation(card_account, groceries)
    response = send_json("GET", f"{OPERATIONS_URL}?page=200000000000000000")

    assert response.status_code == HTTPStatus.OK
    assert response.json() == {"items": [], "count": 1}
