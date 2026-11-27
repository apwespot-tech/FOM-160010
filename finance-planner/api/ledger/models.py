from decimal import Decimal

from django.conf import settings
from django.db import models
from django.db.models import F, Q

MONEY_MAX_DIGITS = 14
MONEY_DECIMAL_PLACES = 2
DEFAULT_CURRENCY = "RUB"
CURRENCY_CODE_PATTERN = r"^[A-Z]{3}$"
ACCOUNT_NAME_MAX_LENGTH = 100
CATEGORY_NAME_MAX_LENGTH = 60
NOTE_MAX_LENGTH = 255


class AccountKind(models.TextChoices):
    CASH = "cash", "Наличные"
    CARD = "card", "Карта"
    SAVINGS = "savings", "Накопительный"


class CategoryKind(models.TextChoices):
    INCOME = "income", "Доход"
    EXPENSE = "expense", "Расход"


class OperationKind(models.TextChoices):
    INCOME = "income", "Доход"
    EXPENSE = "expense", "Расход"
    TRANSFER_OUT = "transfer_out", "Списание перевода"
    TRANSFER_IN = "transfer_in", "Зачисление перевода"


CATEGORY_OPERATION_KINDS = [OperationKind.INCOME.value, OperationKind.EXPENSE.value]
TRANSFER_OPERATION_KINDS = [OperationKind.TRANSFER_OUT.value, OperationKind.TRANSFER_IN.value]

# Доход и расход относятся к категории, операции перевода к переводу. Две ветки заодно ограничивают и список видов
CATEGORY_OPERATION_CONDITION = Q(kind__in=CATEGORY_OPERATION_KINDS, category__isnull=False, transfer__isnull=True)
TRANSFER_OPERATION_CONDITION = Q(kind__in=TRANSFER_OPERATION_KINDS, category__isnull=True, transfer__isnull=False)


class Account(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="accounts", verbose_name="владелец")
    name = models.CharField("название", max_length=ACCOUNT_NAME_MAX_LENGTH)
    kind = models.CharField("тип", max_length=16, choices=AccountKind.choices)
    currency = models.CharField("валюта", max_length=3, default=DEFAULT_CURRENCY)
    initial_balance = models.DecimalField("начальный остаток", max_digits=MONEY_MAX_DIGITS, decimal_places=MONEY_DECIMAL_PLACES, default=Decimal("0"))
    is_archived = models.BooleanField("в архиве", default=False)
    created_at = models.DateTimeField("создан", auto_now_add=True)

    class Meta:
        verbose_name = "счёт"
        verbose_name_plural = "счета"

        constraints = [
            models.CheckConstraint(condition=Q(kind__in=AccountKind.values), name="ledger_account_kind_valid"),
            models.CheckConstraint(condition=Q(currency__regex=CURRENCY_CODE_PATTERN), name="ledger_account_currency_code"),
        ]

    def __str__(self) -> str:
        return self.name


class Category(models.Model):
    # У общей категории владельца нет: такие категории заводит миграция данных, и видны они всем пользователям
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="categories",
        verbose_name="владелец",
    )

    name = models.CharField("название", max_length=CATEGORY_NAME_MAX_LENGTH)
    kind = models.CharField("вид", max_length=8, choices=CategoryKind.choices)

    class Meta:
        verbose_name = "категория"
        verbose_name_plural = "категории"

        constraints = [
            models.CheckConstraint(condition=Q(kind__in=CategoryKind.values), name="ledger_category_kind_valid"),
            # Без nulls_distinct=False PostgreSQL считал бы пустых владельцев разными и пропускал повторы среди общих категорий
            models.UniqueConstraint(fields=["user", "kind", "name"], nulls_distinct=False, name="ledger_category_unique_name"),
        ]

    def __str__(self) -> str:
        return self.name

    @property
    def is_common(self) -> bool:
        return self.user_id is None


class Transfer(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="transfers", verbose_name="владелец")
    from_account = models.ForeignKey(Account, on_delete=models.RESTRICT, related_name="outgoing_transfers", verbose_name="счёт списания")
    to_account = models.ForeignKey(Account, on_delete=models.RESTRICT, related_name="incoming_transfers", verbose_name="счёт зачисления")
    amount_out = models.DecimalField("списано", max_digits=MONEY_MAX_DIGITS, decimal_places=MONEY_DECIMAL_PLACES)
    amount_in = models.DecimalField("зачислено", max_digits=MONEY_MAX_DIGITS, decimal_places=MONEY_DECIMAL_PLACES)

    # Разница в рублях появляется только у перевода между счетами в разных валютах
    exchange_difference = models.DecimalField(
        "курсовая разница",
        max_digits=MONEY_MAX_DIGITS,
        decimal_places=MONEY_DECIMAL_PLACES,
        default=Decimal("0"),
    )

    date = models.DateField("дата")
    note = models.CharField("заметка", max_length=NOTE_MAX_LENGTH, blank=True, default="")
    created_at = models.DateTimeField("создан", auto_now_add=True)

    class Meta:
        verbose_name = "перевод"
        verbose_name_plural = "переводы"

        constraints = [
            models.CheckConstraint(condition=~Q(from_account=F("to_account")), name="ledger_transfer_accounts_differ"),
            models.CheckConstraint(condition=Q(amount_out__gt=0) & Q(amount_in__gt=0), name="ledger_transfer_amounts_positive"),
        ]

    def __str__(self) -> str:
        return f"{self.date} {self.amount_out}"


class Operation(models.Model):
    # Отдельные индексы по владельцу и счёту не создаются: их покрывают составные индексы с датой в Meta.indexes
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        db_index=False,
        related_name="operations",
        verbose_name="владелец",
    )

    account = models.ForeignKey(Account, on_delete=models.RESTRICT, db_index=False, related_name="operations", verbose_name="счёт")

    category = models.ForeignKey(
        Category,
        on_delete=models.RESTRICT,
        null=True,
        blank=True,
        related_name="operations",
        verbose_name="категория",
    )

    kind = models.CharField("вид", max_length=12, choices=OperationKind.choices)
    amount = models.DecimalField("сумма", max_digits=MONEY_MAX_DIGITS, decimal_places=MONEY_DECIMAL_PLACES)
    date = models.DateField("дата")
    note = models.CharField("заметка", max_length=NOTE_MAX_LENGTH, blank=True, default="")

    transfer = models.ForeignKey(
        Transfer,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="operations",
        verbose_name="перевод",
    )

    created_at = models.DateTimeField("создана", auto_now_add=True)

    class Meta:
        verbose_name = "операция"
        verbose_name_plural = "операции"

        constraints = [
            models.CheckConstraint(condition=Q(amount__gt=0), name="ledger_operation_amount_positive"),
            models.CheckConstraint(
                condition=CATEGORY_OPERATION_CONDITION | TRANSFER_OPERATION_CONDITION,
                name="ledger_operation_category_or_transfer",
            ),
            models.UniqueConstraint(
                fields=["transfer", "kind"],
                condition=Q(transfer__isnull=False),
                name="ledger_operation_unique_transfer_kind",
            ),
        ]

        indexes = [
            models.Index(fields=["user", "date"], name="ledger_operation_user_date"),
            models.Index(fields=["account", "date"], name="ledger_operation_account_date"),
        ]

    def __str__(self) -> str:
        return f"{self.date} {self.amount}"
