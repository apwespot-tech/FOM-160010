from datetime import date, datetime
from decimal import Decimal, ROUND_HALF_UP
import re
from typing import Annotated, Literal

from ninja import FilterLookup, FilterSchema, Schema
from pydantic import (
    AfterValidator,
    BeforeValidator,
    ConfigDict,
    Field,
    field_validator,
    PlainSerializer,
    StringConstraints,
    ValidationInfo,
    WithJsonSchema,
)
from pydantic_core import PydanticCustomError

from ledger.models import ACCOUNT_NAME_MAX_LENGTH, CATEGORY_NAME_MAX_LENGTH, NOTE_MAX_LENGTH
from users.schemas import StrictInput

# Пробелы, плюс, запятая и экспонента не допускаются: [0-9] вместо \d, потому что \d в Python принимает и цифры других алфавитов
POSITIVE_AMOUNT_PATTERN = re.compile(r"[0-9]{1,12}(\.[0-9]{1,2})?")
SIGNED_AMOUNT_PATTERN = re.compile(r"-?[0-9]{1,12}(\.[0-9]{1,2})?")
DATE_PATTERN = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}")
CURRENCY_PATTERN = re.compile(r"[A-Z]{3}")
CENT = Decimal("0.01")
NULL_CHARACTER = "\x00"

AMOUNT_FORMAT_MESSAGE = "Сумма записывается строкой вида 1250.50"
SIGNED_AMOUNT_FORMAT_MESSAGE = "Сумма записывается строкой вида 1250.50 или -1250.50"
DATE_FORMAT_MESSAGE = "Дата записывается строкой вида 2026-11-18"
CURRENCY_FORMAT_MESSAGE = "Код валюты записывается тремя заглавными латинскими буквами"
TEXT_CHARACTER_MESSAGE = "Текст содержит недопустимый знак"
PERIOD_ORDER_MESSAGE = "Начало периода позже конца"


def check_positive_amount_format(value: object) -> object:
    # Число JSON отклоняется вместе с неверной строкой: float для денег исключён самим контрактом
    if not isinstance(value, str) or POSITIVE_AMOUNT_PATTERN.fullmatch(value) is None:
        raise PydanticCustomError("planner_format", AMOUNT_FORMAT_MESSAGE)

    return value


def check_signed_amount_format(value: object) -> object:
    if not isinstance(value, str) or SIGNED_AMOUNT_PATTERN.fullmatch(value) is None:
        raise PydanticCustomError("planner_format", SIGNED_AMOUNT_FORMAT_MESSAGE)

    return value


def check_date_format(value: object) -> object:
    # Pydantic сам принял бы и число секунд, и дату со временем, поэтому вид строки проверяется заранее
    if not isinstance(value, str) or DATE_PATTERN.fullmatch(value) is None:
        raise PydanticCustomError("planner_format", DATE_FORMAT_MESSAGE)

    return value


def check_currency_code(value: str) -> str:
    if CURRENCY_PATTERN.fullmatch(value) is None:
        raise PydanticCustomError("planner_format", CURRENCY_FORMAT_MESSAGE)

    return value


def reject_null_character(text: str) -> str:
    # PostgreSQL не хранит знак NUL в тексте и ответил бы на такую запись ошибкой
    if NULL_CHARACTER in text:
        raise PydanticCustomError("planner_format", TEXT_CHARACTER_MESSAGE)

    return text


def format_money(value: Decimal) -> str:
    rounded_value = value.quantize(CENT, rounding=ROUND_HALF_UP)

    return str(rounded_value)


# Без явного описания OpenAPI показал бы у суммы «число или строку», хотя число JSON отклоняется
POSITIVE_AMOUNT_JSON_SCHEMA = {
    "type": "string",
    "pattern": r"^[0-9]{1,12}(\.[0-9]{1,2})?$",
    "description": "Больше нуля",
    "examples": ["1250.50"],
}

SIGNED_AMOUNT_JSON_SCHEMA = {
    "type": "string",
    "pattern": r"^-?[0-9]{1,12}(\.[0-9]{1,2})?$",
    "description": "Допускается минус",
    "examples": ["-250.00"],
}

# Ограничения стоят раньше BeforeValidator: так он выполняется первым, а ошибка «не больше нуля» остаётся greater_than
PositiveAmount = Annotated[Decimal, Field(gt=0), BeforeValidator(check_positive_amount_format), WithJsonSchema(POSITIVE_AMOUNT_JSON_SCHEMA)]
SignedAmount = Annotated[Decimal, BeforeValidator(check_signed_amount_format), WithJsonSchema(SIGNED_AMOUNT_JSON_SCHEMA)]
PlannerDate = Annotated[date, BeforeValidator(check_date_format)]
CurrencyCode = Annotated[str, AfterValidator(check_currency_code)]
StrictId = Annotated[int, Field(strict=True)]
StrictFlag = Annotated[bool, Field(strict=True)]
MoneyOut = Annotated[Decimal, PlainSerializer(format_money, return_type=str)]

ACCOUNT_NAME_CONSTRAINTS = StringConstraints(strip_whitespace=True, min_length=1, max_length=ACCOUNT_NAME_MAX_LENGTH)
CATEGORY_NAME_CONSTRAINTS = StringConstraints(strip_whitespace=True, min_length=1, max_length=CATEGORY_NAME_MAX_LENGTH)
NOTE_CONSTRAINTS = StringConstraints(strip_whitespace=True, max_length=NOTE_MAX_LENGTH)
TEXT_CHARACTER_CHECK = AfterValidator(reject_null_character)

AccountName = Annotated[str, ACCOUNT_NAME_CONSTRAINTS, TEXT_CHARACTER_CHECK]
CategoryName = Annotated[str, CATEGORY_NAME_CONSTRAINTS, TEXT_CHARACTER_CHECK]
NoteText = Annotated[str, NOTE_CONSTRAINTS, TEXT_CHARACTER_CHECK]

AccountKindValue = Literal["cash", "card", "savings"]
CategoryKindValue = Literal["income", "expense"]
OperationKindValue = Literal["income", "expense", "transfer_out", "transfer_in"]
OperationSort = Literal["-date", "date"]

OPERATION_EXAMPLE = {"kind": "expense", "account_id": 3, "category_id": 4, "amount": "1250.50", "date": "2026-11-18", "note": "Продукты на неделю"}


class AccountCreateInput(StrictInput):
    model_config = ConfigDict(json_schema_extra={"examples": [{"name": "Карта", "kind": "card", "initial_balance": "15000.00"}]})

    name: AccountName
    kind: AccountKindValue
    currency: CurrencyCode = "RUB"
    initial_balance: SignedAmount = Decimal("0")


class AccountUpdateInput(StrictInput):
    model_config = ConfigDict(json_schema_extra={"examples": [{"name": "Карта зарплатная"}, {"is_archived": True}]})

    # None значит, что поле не прислали. Типы без None нарочно: явный null не пройдёт проверку, как в профиле пользователя
    name: AccountName = None
    initial_balance: SignedAmount = None
    is_archived: StrictFlag = None


class AccountOut(Schema):
    id: int
    name: str
    kind: str
    currency: str
    initial_balance: MoneyOut
    balance: MoneyOut
    is_archived: bool
    created_at: datetime


class AccountListOut(Schema):
    items: list[AccountOut]
    total_balance: MoneyOut


class CategoryCreateInput(StrictInput):
    model_config = ConfigDict(json_schema_extra={"examples": [{"name": "Хобби", "kind": "expense"}]})

    name: CategoryName
    kind: CategoryKindValue


class CategoryUpdateInput(StrictInput):
    model_config = ConfigDict(json_schema_extra={"examples": [{"name": "Книги и хобби"}]})

    name: CategoryName = None


class CategoryOut(Schema):
    id: int
    name: str
    kind: str
    is_common: bool


class CategoryListOut(Schema):
    items: list[CategoryOut]


class OperationCreateInput(StrictInput):
    model_config = ConfigDict(json_schema_extra={"examples": [OPERATION_EXAMPLE]})

    kind: CategoryKindValue
    account_id: StrictId
    category_id: StrictId
    amount: PositiveAmount
    date: PlannerDate
    note: NoteText = ""


class OperationUpdateInput(StrictInput):
    model_config = ConfigDict(json_schema_extra={"examples": [{"amount": "1300.00", "note": "Продукты и бытовая химия"}]})

    account_id: StrictId = None
    category_id: StrictId = None
    amount: PositiveAmount = None
    date: PlannerDate = None
    note: NoteText = None


class OperationOut(Schema):
    id: int
    kind: str
    account_id: int
    category_id: int | None
    amount: MoneyOut
    date: date
    note: str
    transfer_id: int | None
    created_at: datetime


class OperationFilter(FilterSchema):
    date_from: Annotated[PlannerDate | None, FilterLookup("date__gte")] = None
    date_to: Annotated[PlannerDate | None, FilterLookup("date__lte")] = None
    account_id: int | None = None
    category_id: int | None = None
    kind: OperationKindValue | None = None

    @field_validator("date_to")
    @classmethod
    def check_period_order(cls, date_to: date | None, info: ValidationInfo) -> date | None:
        date_from = info.data.get("date_from")
        is_period_reversed = date_from is not None and date_to is not None and date_from > date_to

        if is_period_reversed:
            raise PydanticCustomError("planner_rule", PERIOD_ORDER_MESSAGE)

        return date_to
