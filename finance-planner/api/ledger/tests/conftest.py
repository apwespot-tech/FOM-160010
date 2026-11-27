from collections.abc import Iterator
from datetime import datetime, UTC
from unittest import mock

from django.test import Client
import pytest

from ledger.models import Account, Category
from ledger.tests.factories import make_account
from users.models import User

# В Екатеринбурге в этот момент уже 21 ноября, а в UTC ещё 20-е: «сегодня» у пользователей с разными поясами разное
FROZEN_NOW = datetime(2026, 11, 20, 20, 30, tzinfo=UTC)


@pytest.fixture
def frozen_now() -> Iterator[datetime]:
    with mock.patch("django.utils.timezone.now", return_value=FROZEN_NOW):
        yield FROZEN_NOW


@pytest.fixture
def signed_in_user(csrf_client: Client, user: User) -> User:
    csrf_client.force_login(user)

    return user


@pytest.fixture
def other_user(db: None) -> User:
    return User.objects.create_user("boris", password="lantern-orbit-58", time_zone="UTC")


@pytest.fixture
def card_account(user: User) -> Account:
    return make_account(user, initial_balance="1000.00")


@pytest.fixture
def foreign_account(other_user: User) -> Account:
    return make_account(other_user, name="Чужая карта")


@pytest.fixture
def groceries(db: None) -> Category:
    return Category.objects.get(user=None, kind="expense", name="Продукты")


@pytest.fixture
def salary(db: None) -> Category:
    return Category.objects.get(user=None, kind="income", name="Зарплата")
