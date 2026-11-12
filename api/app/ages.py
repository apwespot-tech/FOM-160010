from datetime import date


def calculate_age(birth_date: date, today: date) -> int:
    """Полных лет на дату today."""
    had_birthday = (today.month, today.day) >= (birth_date.month, birth_date.day)
    return today.year - birth_date.year - (0 if had_birthday else 1)


def latest_birth_date(today: date, age: int) -> date:
    """Самая поздняя дата рождения, при которой на дату today исполнилось age полных лет.

    Если today — 29 февраля, а в году рождения его нет, граница — 28 февраля.
    """
    try:
        return today.replace(year=today.year - age)
    except ValueError:
        return today.replace(year=today.year - age, day=28)
