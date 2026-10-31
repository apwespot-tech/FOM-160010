import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import RefreshToken, Role, User, UserRole

NOW = datetime(2026, 10, 31, tzinfo=UTC)


def test_phone_is_unique(db: Session) -> None:
    db.add(User(phone="+79991110001"))
    db.commit()
    db.add(User(phone="+79991110001"))
    with pytest.raises(IntegrityError):
        db.commit()


def test_email_is_unique_case_insensitive(db: Session) -> None:
    db.add(User(phone="+79991110001", email="ann@example.com"))
    db.commit()
    db.add(User(phone="+79991110002", email="Ann@Example.com"))
    with pytest.raises(IntegrityError):
        db.commit()


def test_many_users_without_email(db: Session) -> None:
    db.add_all([User(phone="+79991110001"), User(phone="+79991110002")])
    db.commit()


def test_user_delete_cascades_roles_and_tokens(db: Session) -> None:
    user = User(phone="+79991110001", role_rows=[UserRole(role=Role.PARTICIPANT)])
    db.add(user)
    db.flush()
    db.add(
        RefreshToken(
            id=uuid.uuid4(),
            user_id=user.id,
            token_hash="a" * 64,
            created_at=NOW,
            expires_at=NOW,
        )
    )
    db.commit()

    # Удаляем на уровне SQL, чтобы проверить ON DELETE CASCADE, а не каскад ORM
    db.execute(delete(User).where(User.id == user.id))
    db.commit()

    assert db.scalar(select(func.count()).select_from(UserRole)) == 0
    assert db.scalar(select(func.count()).select_from(RefreshToken)) == 0
