import enum
import uuid
from datetime import date, datetime

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    LargeBinary,
    String,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.event import PHOTO_CONTENT_TYPES

ABOUT_MAX_LENGTH = 500


class Role(enum.StrEnum):
    PARTICIPANT = "participant"
    ORGANIZER = "organizer"
    ADMIN = "admin"


role_enum = Enum(
    Role,
    name="user_role",
    values_callable=lambda roles: [role.value for role in roles],
)

EMAIL_UNIQUE_INDEX = "uq_users_email_lower"
PHONE_UNIQUE_CONSTRAINT = "uq_users_phone"


class User(Base):
    __tablename__ = "users"
    __table_args__ = (Index(EMAIL_UNIQUE_INDEX, func.lower(text("email")), unique=True),)

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()")
    )
    phone: Mapped[str] = mapped_column(String(16), unique=True)
    name: Mapped[str | None] = mapped_column(String(100))
    birth_date: Mapped[date | None] = mapped_column(Date)
    email: Mapped[str | None] = mapped_column(String(320))
    telegram: Mapped[str | None] = mapped_column(String(33))
    about: Mapped[str | None] = mapped_column(String(ABOUT_MAX_LENGTH))
    city_id: Mapped[int | None] = mapped_column(ForeignKey("cities.id", ondelete="SET NULL"))
    # users <-> user_images ссылаются друг на друга: FK картинок создаются отдельным ALTER
    avatar_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("user_images.id", ondelete="SET NULL", use_alter=True)
    )
    cover_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("user_images.id", ondelete="SET NULL", use_alter=True)
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    role_rows: Mapped[list["UserRole"]] = relationship(
        back_populates="user", cascade="all, delete-orphan", lazy="selectin"
    )

    @property
    def roles(self) -> set[Role]:
        return {row.role for row in self.role_rows}

    @property
    def is_admin(self) -> bool:
        return Role.ADMIN in self.roles

    @property
    def profile_completed(self) -> bool:
        return self.name is not None and self.birth_date is not None


class UserRole(Base):
    __tablename__ = "user_roles"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    role: Mapped[Role] = mapped_column(role_enum, primary_key=True)

    user: Mapped[User] = relationship(back_populates="role_rows")


class UserImage(Base):
    """Аватар или обложка пользователя: роль задаёт ссылка users.avatar_id / cover_id."""

    __tablename__ = "user_images"
    __table_args__ = (
        CheckConstraint(
            f"content_type IN ({', '.join(repr(t) for t in PHOTO_CONTENT_TYPES)})",
            name="content_type_values",
        ),
        Index("ix_user_images_user_id", "user_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()")
    )
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    content_type: Mapped[str] = mapped_column(String(20))
    data: Mapped[bytes] = mapped_column(LargeBinary)
    thumb: Mapped[bytes] = mapped_column(LargeBinary)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class UserInterest(Base):
    """Интерес пользователя — категория мероприятий."""

    __tablename__ = "user_interests"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    category_id: Mapped[int] = mapped_column(
        ForeignKey("categories.id", ondelete="CASCADE"), primary_key=True
    )
