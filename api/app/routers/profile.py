import uuid
from typing import Annotated

from fastapi import APIRouter, File, UploadFile

from app.deps import AdminUser, CompletedUser, CurrentUser, NowDep, SessionDep
from app.schemas.profile import AdminProfileUpdate, ProfileOut, ProfileUpdate
from app.services import profile_image_service, profile_service
from app.services.profile_image_service import ProfileImageKind

router = APIRouter(prefix="/profile", tags=["profile"])


@router.get("")
def get_own_profile(user: CurrentUser, session: SessionDep, now: NowDep) -> ProfileOut:
    return profile_service.build_profile(session, user, now)


@router.patch("")
def update_own_profile(
    body: ProfileUpdate, user: CurrentUser, session: SessionDep, now: NowDep
) -> ProfileOut:
    updated = profile_service.update_own_profile(session, now, user, body)
    return profile_service.build_profile(session, updated, now)


@router.put("/{kind}")
def upload_profile_image(
    kind: ProfileImageKind,
    file: Annotated[UploadFile, File(description="JPEG, PNG или WebP до 2 МБ")],
    user: CompletedUser,
    session: SessionDep,
    now: NowDep,
) -> ProfileOut:
    """Аватар (`avatar`) или обложка (`cover`): новая картинка заменяет прежнюю."""
    profile_image_service.set_image(session, now, user, kind, file.file)
    return profile_service.build_profile(session, user, now)


@router.delete("/{kind}")
def delete_profile_image(
    kind: ProfileImageKind, user: CompletedUser, session: SessionDep, now: NowDep
) -> ProfileOut:
    profile_image_service.delete_image(session, user, kind)
    return profile_service.build_profile(session, user, now)


@router.get("/{user_id}")
def get_profile(
    user_id: uuid.UUID, viewer: CompletedUser, session: SessionDep, now: NowDep
) -> ProfileOut:
    user = profile_service.get_profile_for(session, viewer, user_id)
    return profile_service.build_profile(session, user, now)


@router.patch("/{user_id}")
def update_profile(
    user_id: uuid.UUID,
    body: AdminProfileUpdate,
    _: AdminUser,
    session: SessionDep,
    now: NowDep,
) -> ProfileOut:
    updated = profile_service.update_profile_by_admin(session, now, user_id, body)
    return profile_service.build_profile(session, updated, now)
