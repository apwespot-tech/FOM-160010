from datetime import date
from decimal import Decimal

from django.db import IntegrityError, transaction
from django.db.models import RestrictedError
import pytest

from ledger.models import Account, Category, Operation, Transfer
from users.models import User

pytestmark = pytest.mark.django_db

OPERATION_DATE = date(2026, 11, 18)

COMMON_CATEGORIES = {
    ("income", "Зарплата"),
    ("income", "Подарки"),
    ("income", "Прочие доходы"),
    ("expense", "Продукты"),
    ("expense", "Транспорт"),
    ("expense", "Жильё"),
    ("expense", "Связь"),
    ("expense", "Здоровье"),
    ("expense", "Одежда"),
    ("expense", "Развлечения"),
    ("expense", "Образование"),
    ("expense", "Кафе"),
    ("expense", "Подписки"),
    ("expense", "Прочие расходы"),
}


@pytest.fixture
def savings_account(user: User) -> Account:
    return Account.objects.create(user=user, name="Копилка", kind="savings")


@pytest.fixture
def transfer(user: User, card_account: Account, savings_account: Account) -> Transfer:
    return Transfer.objects.create(
        user=user,
        from_account=card_account,
        to_account=savings_account,
        amount_out=Decimal("300.00"),
        amount_in=Decimal("300.00"),
        date=OPERATION_DATE,
    )


def create_expense(account: Account, category: Category, amount: str = "120.50") -> Operation:
    return Operation.objects.create(
        user=account.user,
        account=account,
        category=category,
        kind="expense",
        amount=Decimal(amount),
        date=OPERATION_DATE,
    )


def create_transfer_operation(account: Account, transfer: Transfer, kind: str) -> Operation:
    return Operation.objects.create(
        user=account.user,
        account=account,
        kind=kind,
        amount=transfer.amount_out,
        date=OPERATION_DATE,
        transfer=transfer,
    )


def test_migration_creates_common_categories() -> None:
    common_categories = set(Category.objects.filter(user__isnull=True).values_list("kind", "name"))

    assert common_categories == COMMON_CATEGORIES


def test_valid_rows_are_saved(card_account: Account, groceries: Category, transfer: Transfer) -> None:
    expense = create_expense(card_account, groceries)
    transfer_out = create_transfer_operation(card_account, transfer, "transfer_out")

    assert card_account.currency == "RUB"
    assert transfer.exchange_difference == Decimal("0")
    assert expense.note == ""
    assert transfer_out.category is None


def test_account_rejects_unknown_kind(user: User) -> None:
    with pytest.raises(IntegrityError, match="ledger_account_kind_valid"), transaction.atomic():
        Account.objects.create(user=user, name="Вклад", kind="deposit")


# Код из четырёх знаков отклоняет уже длина столбца varchar(3), поэтому здесь только трёхзнаковые и короче
@pytest.mark.parametrize("currency", ["rub", "RU", "R1B", "RU ", ""])
def test_account_rejects_malformed_currency(user: User, currency: str) -> None:
    with pytest.raises(IntegrityError, match="ledger_account_currency_code"), transaction.atomic():
        Account.objects.create(user=user, name="Карта", kind="card", currency=currency)


def test_category_rejects_unknown_kind(user: User) -> None:
    with pytest.raises(IntegrityError, match="ledger_category_kind_valid"), transaction.atomic():
        Category.objects.create(user=user, name="Возврат", kind="refund")


def test_category_name_is_unique_for_user_and_kind(user: User) -> None:
    Category.objects.create(user=user, name="Хобби", kind="expense")

    with pytest.raises(IntegrityError, match="ledger_category_unique_name"), transaction.atomic():
        Category.objects.create(user=user, name="Хобби", kind="expense")


def test_common_category_names_are_unique_within_kind() -> None:
    with pytest.raises(IntegrityError, match="ledger_category_unique_name"), transaction.atomic():
        Category.objects.create(user=None, name="Продукты", kind="expense")


def test_category_name_repeats_across_kinds_and_users(user: User) -> None:
    other_user = User.objects.create_user("boris", password="lantern-orbit-58")
    Category.objects.create(user=user, name="Хобби", kind="expense")
    Category.objects.create(user=user, name="Хобби", kind="income")
    Category.objects.create(user=other_user, name="Хобби", kind="expense")

    assert Category.objects.filter(name="Хобби").count() == 3


@pytest.mark.parametrize("amount", ["0", "-10.00"])
def test_operation_amount_must_be_positive(card_account: Account, groceries: Category, amount: str) -> None:
    with pytest.raises(IntegrityError, match="ledger_operation_amount_positive"), transaction.atomic():
        create_expense(card_account, groceries, amount)


@pytest.mark.parametrize(
    ("kind", "has_category", "has_transfer"),
    [
        ("expense", False, False),
        ("income", True, True),
        ("transfer_out", True, True),
        ("transfer_in", False, False),
        ("refund", True, False),
    ],
    ids=["expense-without-category", "income-with-transfer", "transfer-with-category", "transfer-without-transfer", "unknown-kind"],
)
def test_operation_links_category_or_transfer(
    card_account: Account,
    groceries: Category,
    transfer: Transfer,
    kind: str,
    has_category: bool,
    has_transfer: bool,
) -> None:
    category = groceries if has_category else None
    linked_transfer = transfer if has_transfer else None

    with pytest.raises(IntegrityError, match="ledger_operation_category_or_transfer"), transaction.atomic():
        Operation.objects.create(
            user=card_account.user,
            account=card_account,
            category=category,
            kind=kind,
            amount=Decimal("10.00"),
            date=OPERATION_DATE,
            transfer=linked_transfer,
        )


def test_transfer_has_one_operation_of_each_kind(card_account: Account, transfer: Transfer) -> None:
    create_transfer_operation(card_account, transfer, "transfer_out")

    with pytest.raises(IntegrityError, match="ledger_operation_unique_transfer_kind"), transaction.atomic():
        create_transfer_operation(card_account, transfer, "transfer_out")


def test_transfer_accounts_must_differ(user: User, card_account: Account) -> None:
    with pytest.raises(IntegrityError, match="ledger_transfer_accounts_differ"), transaction.atomic():
        Transfer.objects.create(
            user=user,
            from_account=card_account,
            to_account=card_account,
            amount_out=Decimal("10.00"),
            amount_in=Decimal("10.00"),
            date=OPERATION_DATE,
        )


@pytest.mark.parametrize(("amount_out", "amount_in"), [("0", "10.00"), ("10.00", "0"), ("-10.00", "-10.00")])
def test_transfer_amounts_must_be_positive(user: User, card_account: Account, savings_account: Account, amount_out: str, amount_in: str) -> None:
    with pytest.raises(IntegrityError, match="ledger_transfer_amounts_positive"), transaction.atomic():
        Transfer.objects.create(
            user=user,
            from_account=card_account,
            to_account=savings_account,
            amount_out=Decimal(amount_out),
            amount_in=Decimal(amount_in),
            date=OPERATION_DATE,
        )


def test_account_with_operations_is_not_deleted(card_account: Account, groceries: Category) -> None:
    create_expense(card_account, groceries)

    with pytest.raises(RestrictedError), transaction.atomic():
        card_account.delete()

    assert Account.objects.filter(id=card_account.id).exists()


def test_account_with_transfers_is_not_deleted(savings_account: Account, transfer: Transfer) -> None:
    with pytest.raises(RestrictedError), transaction.atomic():
        savings_account.delete()

    assert Account.objects.filter(id=savings_account.id).exists()


def test_category_with_operations_is_not_deleted(user: User, card_account: Account) -> None:
    hobby = Category.objects.create(user=user, name="Хобби", kind="expense")
    create_expense(card_account, hobby)

    with pytest.raises(RestrictedError), transaction.atomic():
        hobby.delete()

    assert Category.objects.filter(id=hobby.id).exists()


def test_transfer_deletion_removes_its_operations(user: User, card_account: Account, savings_account: Account, transfer: Transfer) -> None:
    create_transfer_operation(card_account, transfer, "transfer_out")
    create_transfer_operation(savings_account, transfer, "transfer_in")
    transfer.delete()

    assert not Operation.objects.filter(user=user).exists()


def test_user_deletion_removes_own_ledger_rows(user: User, card_account: Account, groceries: Category, transfer: Transfer) -> None:
    Category.objects.create(user=user, name="Хобби", kind="expense")
    create_expense(card_account, groceries)
    user.delete()

    assert not Account.objects.exists()
    assert not Operation.objects.exists()
    assert not Transfer.objects.exists()
    assert not Category.objects.filter(user__isnull=False).exists()
    assert Category.objects.filter(user__isnull=True).count() == len(COMMON_CATEGORIES)
