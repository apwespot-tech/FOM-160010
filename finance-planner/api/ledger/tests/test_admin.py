from datetime import date
from decimal import Decimal
from http import HTTPStatus

from django.test import Client
import pytest

from ledger.models import Account, Category, Operation, Transfer
from ledger.tests.factories import make_account, make_transfer
from users.models import User

pytestmark = pytest.mark.django_db

MODEL_PATHS = ["account", "category", "operation", "transfer"]


@pytest.fixture
def expense(user: User) -> Operation:
    account = Account.objects.create(user=user, name="Карта", kind="card")
    groceries = Category.objects.get(user=None, kind="expense", name="Продукты")

    return Operation.objects.create(user=user, account=account, category=groceries, kind="expense", amount=Decimal("99.90"), date=date(2026, 11, 18))


@pytest.fixture
def ledger_rows(user: User, expense: Operation) -> dict[str, int]:
    hobby = Category.objects.create(user=user, name="Хобби", kind="expense")
    savings_account = make_account(user, name="Копилка", kind="savings")
    transfer = make_transfer(expense.account, savings_account, "10.00")

    return {"account": expense.account_id, "category": hobby.id, "operation": expense.id, "transfer": transfer.id}


@pytest.mark.parametrize("model_path", MODEL_PATHS)
def test_admin_ledger_lists_open(admin_client: Client, model_path: str) -> None:
    response = admin_client.get(f"/admin/ledger/{model_path}/")

    assert response.status_code == HTTPStatus.OK


@pytest.mark.parametrize("model_path", MODEL_PATHS)
def test_admin_cannot_add_ledger_rows(admin_client: Client, model_path: str) -> None:
    response = admin_client.get(f"/admin/ledger/{model_path}/add/")

    assert response.status_code == HTTPStatus.FORBIDDEN


def test_admin_shows_operation_read_only(admin_client: Client, expense: Operation) -> None:
    change_url = f"/admin/ledger/operation/{expense.id}/change/"
    page_response = admin_client.get(change_url)
    save_response = admin_client.post(change_url, {"amount": "1.00"})
    expense.refresh_from_db()

    assert page_response.status_code == HTTPStatus.OK
    assert "name=\"_save\"" not in page_response.content.decode()
    assert save_response.status_code == HTTPStatus.FORBIDDEN
    assert expense.amount == Decimal("99.90")


@pytest.mark.parametrize("model_path", MODEL_PATHS)
def test_admin_cannot_change_or_delete_ledger_rows(admin_client: Client, ledger_rows: dict[str, int], model_path: str) -> None:
    row_url = f"/admin/ledger/{model_path}/{ledger_rows[model_path]}"
    change_response = admin_client.post(f"{row_url}/change/", {})
    delete_response = admin_client.post(f"{row_url}/delete/", {"post": "yes"})

    assert change_response.status_code == HTTPStatus.FORBIDDEN
    assert delete_response.status_code == HTTPStatus.FORBIDDEN
    assert Operation.objects.exists()
    assert Transfer.objects.exists()


def test_admin_deletes_user_with_ledger_rows(admin_client: Client, user: User, ledger_rows: dict[str, int]) -> None:
    # Строки учёта нельзя удалить напрямую, но вместе с владельцем они уходят каскадом
    response = admin_client.post(f"/admin/users/user/{user.id}/delete/", {"post": "yes"})

    assert response.status_code == HTTPStatus.FOUND
    assert not User.objects.filter(id=user.id).exists()
    assert not Account.objects.exists()
    assert not Operation.objects.exists()
    assert not Category.objects.filter(user__isnull=False).exists()
