from datetime import date
from decimal import Decimal

from django.http import HttpResponse

from ledger.models import Account, Category, Operation, Transfer
from users.models import User

DEFAULT_OPERATION_DATE = date(2026, 11, 18)


def read_errors(response: HttpResponse) -> list[tuple[str, str]]:
    detail = response.json()["detail"]

    return [(error["loc"][-1], error["type"]) for error in detail]


def read_messages(response: HttpResponse) -> dict[str, str]:
    detail = response.json()["detail"]

    return {error["loc"][-1]: error["msg"] for error in detail}


def make_account(user: User, name: str = "Карта", kind: str = "card", initial_balance: str = "0", is_archived: bool = False) -> Account:
    return Account.objects.create(user=user, name=name, kind=kind, initial_balance=Decimal(initial_balance), is_archived=is_archived)


def make_operation(
    account: Account,
    category: Category,
    amount: str = "100.00",
    operation_date: date = DEFAULT_OPERATION_DATE,
    note: str = "",
) -> Operation:
    return Operation.objects.create(
        user=account.user,
        account=account,
        category=category,
        kind=category.kind,
        amount=Decimal(amount),
        date=operation_date,
        note=note,
    )


def make_transfer(from_account: Account, to_account: Account, amount: str, operation_date: date = DEFAULT_OPERATION_DATE) -> Transfer:
    # Маршрутов переводов ещё нет, поэтому пара операций перевода создаётся напрямую, как её создаст сервис переводов
    transfer_amount = Decimal(amount)

    transfer = Transfer.objects.create(
        user=from_account.user,
        from_account=from_account,
        to_account=to_account,
        amount_out=transfer_amount,
        amount_in=transfer_amount,
        date=operation_date,
    )

    Operation.objects.create(
        user=from_account.user,
        account=from_account,
        kind="transfer_out",
        amount=transfer_amount,
        date=operation_date,
        transfer=transfer,
    )

    Operation.objects.create(
        user=to_account.user,
        account=to_account,
        kind="transfer_in",
        amount=transfer_amount,
        date=operation_date,
        transfer=transfer,
    )

    return transfer
