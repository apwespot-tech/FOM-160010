from datetime import date
from decimal import Decimal

from django.db import IntegrityError, transaction

from ledger.models import Account, Category, DEFAULT_CURRENCY, Operation
from users.models import User

ACCOUNT_NOT_FOUND_MESSAGE = "Счёт не найден"
ACCOUNT_ARCHIVED_MESSAGE = "Счёт в архиве"
ACCOUNT_CURRENCY_MISMATCH_MESSAGE = "Счёт можно сменить только на счёт в той же валюте"
CURRENCY_NOT_SUPPORTED_MESSAGE = "Пока счёт можно открыть только в рублях"
CATEGORY_NOT_FOUND_MESSAGE = "Категория не найдена"
CATEGORY_KIND_MISMATCH_MESSAGE = "Вид категории не совпадает с видом операции"
CATEGORY_NAME_TAKEN_MESSAGE = "Категория с таким названием уже есть"
FUTURE_DATE_MESSAGE = "Дата не может быть позже сегодняшнего дня"

FieldErrors = list[tuple[str, str]]


class LedgerRuleError(Exception):
    def __init__(self, field_errors: FieldErrors) -> None:
        super().__init__(field_errors)
        self.field_errors = field_errors


class AccountInUseError(Exception):
    pass


class CategoryInUseError(Exception):
    pass


class CommonCategoryError(Exception):
    pass


class TransferOperationError(Exception):
    pass


def raise_if_errors(field_errors: FieldErrors) -> None:
    if field_errors:
        raise LedgerRuleError(field_errors)


def sum_balances(accounts: list[Account]) -> Decimal:
    balances = [account.balance for account in accounts]

    return sum(balances, Decimal("0"))


def read_account_with_balance(user_id: int, account_id: int) -> Account:
    return Account.objects.filter(user_id=user_id).with_balance().get(id=account_id)


def create_account(user: User, name: str, kind: str, currency: str, initial_balance: Decimal) -> Account:
    # Счета в других валютах появятся вместе с курсами Банка России
    if currency != DEFAULT_CURRENCY:
        raise LedgerRuleError([("currency", CURRENCY_NOT_SUPPORTED_MESSAGE)])

    account = Account.objects.create(user=user, name=name, kind=kind, currency=currency, initial_balance=initial_balance)

    return read_account_with_balance(user.id, account.id)


def update_account(account: Account, changes: dict[str, object]) -> Account:
    for field_name, value in changes.items():
        setattr(account, field_name, value)

    if changes:
        account.save(update_fields=list(changes))

    return read_account_with_balance(account.user_id, account.id)


def delete_account(account: Account) -> None:
    try:
        with transaction.atomic():
            account.delete()
    except IntegrityError as error:
        # RestrictedError наследует IntegrityError, и тот же перехват ловит ссылку, появившуюся между проверкой Django и удалением
        raise AccountInUseError from error


def is_category_name_taken(user: User, kind: str, name: str, excluded_category_id: int | None = None) -> bool:
    # Своя категория не повторяет ни свою, ни общую категорию того же вида
    same_name_categories = Category.objects.visible_to(user).filter(kind=kind, name=name)

    if excluded_category_id is not None:
        same_name_categories = same_name_categories.exclude(id=excluded_category_id)

    return same_name_categories.exists()


def create_category(user: User, name: str, kind: str) -> Category:
    if is_category_name_taken(user, kind, name):
        raise LedgerRuleError([("name", CATEGORY_NAME_TAKEN_MESSAGE)])

    try:
        with transaction.atomic():
            return Category.objects.create(user=user, name=name, kind=kind)
    except IntegrityError as error:
        # Название могли занять между проверкой и записью
        raise LedgerRuleError([("name", CATEGORY_NAME_TAKEN_MESSAGE)]) from error


def rename_category(user: User, category: Category, name: str | None) -> Category:
    if category.is_common:
        raise CommonCategoryError

    if name is None or name == category.name:
        return category

    if is_category_name_taken(user, category.kind, name, excluded_category_id=category.id):
        raise LedgerRuleError([("name", CATEGORY_NAME_TAKEN_MESSAGE)])

    category.name = name

    try:
        with transaction.atomic():
            category.save(update_fields=["name"])
    except IntegrityError as error:
        raise LedgerRuleError([("name", CATEGORY_NAME_TAKEN_MESSAGE)]) from error

    return category


def delete_category(category: Category) -> None:
    if category.is_common:
        raise CommonCategoryError

    try:
        with transaction.atomic():
            category.delete()
    except IntegrityError as error:
        raise CategoryInUseError from error


def find_own_account(user: User, account_id: int) -> Account | None:
    return Account.objects.for_user(user).filter(id=account_id).first()


def find_visible_category(user: User, category_id: int) -> Category | None:
    return Category.objects.visible_to(user).filter(id=category_id).first()


def check_selected_account(account: Account | None) -> FieldErrors:
    if account is None:
        return [("account_id", ACCOUNT_NOT_FOUND_MESSAGE)]

    if account.is_archived:
        return [("account_id", ACCOUNT_ARCHIVED_MESSAGE)]

    return []


def check_selected_category(category: Category | None, operation_kind: str) -> FieldErrors:
    if category is None:
        return [("category_id", CATEGORY_NOT_FOUND_MESSAGE)]

    if category.kind != operation_kind:
        return [("category_id", CATEGORY_KIND_MISMATCH_MESSAGE)]

    return []


def check_operation_date(user: User, operation_date: date) -> FieldErrors:
    if operation_date > user.get_today():
        return [("date", FUTURE_DATE_MESSAGE)]

    return []


def check_account_change(user: User, operation: Operation, new_account_id: int) -> FieldErrors:
    new_account = find_own_account(user, new_account_id)
    account_errors = check_selected_account(new_account)

    if account_errors:
        return account_errors

    if new_account.currency != operation.account.currency:
        return [("account_id", ACCOUNT_CURRENCY_MISMATCH_MESSAGE)]

    return []


def recheck_references(user: User, account_id: int, category_id: int, operation_kind: str) -> FieldErrors:
    # Внешний ключ проверяется при фиксации транзакции: счёт или категорию могли удалить между проверкой и записью
    account_errors = check_selected_account(find_own_account(user, account_id))
    category_errors = check_selected_category(find_visible_category(user, category_id), operation_kind)

    return account_errors + category_errors


def create_operation(user: User, kind: str, account_id: int, category_id: int, amount: Decimal, operation_date: date, note: str) -> Operation:
    account = find_own_account(user, account_id)
    category = find_visible_category(user, category_id)
    field_errors = check_selected_account(account) + check_selected_category(category, kind) + check_operation_date(user, operation_date)
    raise_if_errors(field_errors)

    try:
        with transaction.atomic():
            # Владелец операции берётся из проверенного счёта: так он всегда совпадает с владельцем счёта
            return Operation.objects.create(
                user_id=account.user_id,
                account=account,
                category=category,
                kind=kind,
                amount=amount,
                date=operation_date,
                note=note,
            )
    except IntegrityError as error:
        reference_errors = recheck_references(user, account_id, category_id, kind)

        if reference_errors:
            raise LedgerRuleError(reference_errors) from error

        raise


def check_reference_changes(user: User, operation: Operation, new_account_id: int, new_category_id: int | None) -> FieldErrors:
    field_errors = []

    # Уже выбранный архивный счёт остаётся допустимым: проверяется только новый счёт
    if new_account_id != operation.account_id:
        field_errors.extend(check_account_change(user, operation, new_account_id))

    if new_category_id != operation.category_id:
        new_category = find_visible_category(user, new_category_id)
        field_errors.extend(check_selected_category(new_category, operation.kind))

    return field_errors


def update_operation(user: User, operation: Operation, changes: dict[str, object]) -> Operation:
    if operation.transfer_id is not None:
        raise TransferOperationError

    new_account_id = changes.get("account_id", operation.account_id)
    new_category_id = changes.get("category_id", operation.category_id)
    new_date = changes.get("date", operation.date)
    field_errors = check_reference_changes(user, operation, new_account_id, new_category_id)

    if new_date != operation.date:
        field_errors.extend(check_operation_date(user, new_date))

    raise_if_errors(field_errors)

    for field_name, value in changes.items():
        setattr(operation, field_name, value)

    if not changes:
        return operation

    try:
        with transaction.atomic():
            operation.save(update_fields=list(changes))
    except IntegrityError as error:
        # Запись откатилась: операция перечитывается из базы, и проверяются те же изменённые ссылки, что и до записи
        operation.refresh_from_db()
        reference_errors = check_reference_changes(user, operation, new_account_id, new_category_id)

        if reference_errors:
            raise LedgerRuleError(reference_errors) from error

        raise

    return operation


def delete_operation(operation: Operation) -> None:
    if operation.transfer_id is not None:
        raise TransferOperationError

    operation.delete()
