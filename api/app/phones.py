from typing import Annotated

import phonenumbers
from pydantic import AfterValidator

DEFAULT_REGION = "RU"


def normalize_phone(raw: str) -> str:
    """Приводит номер к E.164. Бросает ValueError для некорректного номера."""
    try:
        number = phonenumbers.parse(raw, DEFAULT_REGION)
    except phonenumbers.NumberParseException as exc:
        raise ValueError("Некорректный номер телефона") from exc
    if not phonenumbers.is_valid_number(number):
        raise ValueError("Некорректный номер телефона")
    return phonenumbers.format_number(number, phonenumbers.PhoneNumberFormat.E164)


Phone = Annotated[str, AfterValidator(normalize_phone)]
