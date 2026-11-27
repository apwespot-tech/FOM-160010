from typing import get_args

from django.db.models import TextChoices
import pytest

from ledger.models import AccountKind, CategoryKind, OperationKind
from ledger.schemas import AccountKindValue, CategoryKindValue, OperationKindValue

# Схемы перечисляют виды через Literal ради понятной ошибки literal_error, поэтому совпадение с вариантами моделей проверяет тест
KIND_PAIRS = [
    (AccountKindValue, AccountKind),
    (CategoryKindValue, CategoryKind),
    (OperationKindValue, OperationKind),
]


@pytest.mark.parametrize(("schema_kinds", "model_kinds"), KIND_PAIRS)
def test_schema_kinds_match_model_choices(schema_kinds: object, model_kinds: type[TextChoices]) -> None:
    assert set(get_args(schema_kinds)) == set(model_kinds.values)
