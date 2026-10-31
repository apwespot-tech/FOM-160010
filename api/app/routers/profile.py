import uuid

from fastapi import APIRouter

from app.deps import AdminUser, CompletedUser, CurrentUser, NowDep, SessionDep
from app.schemas.profile import AdminProfileUpdate, ProfileOut, ProfileUpdate
from app.services import profile_service

router = APIRouter(prefix="/profile", tags=["profile"])


@router.get("")
def get_own_profile(user: CurrentUser, now: NowDep) -> ProfileOut:
    return ProfileOut.from_user(user, now.date())


@router.patch("")
def update_own_profile(
    body: ProfileUpdate, user: CurrentUser, session: SessionDep, now: NowDep
) -> ProfileOut:
    updated = profile_service.update_own_profile(session, now, user, body)
    return ProfileOut.from_user(updated, now.date())


@router.get("/{user_id}")
def get_profile(
    user_id: uuid.UUID, viewer: CompletedUser, session: SessionDep, now: NowDep
) -> ProfileOut:
    user = profile_service.get_profile_for(session, viewer, user_id)
    return ProfileOut.from_user(user, now.date())


@router.patch("/{user_id}")
def update_profile(
    user_id: uuid.UUID,
    body: AdminProfileUpdate,
    _: AdminUser,
    session: SessionDep,
    now: NowDep,
) -> ProfileOut:
    updated = profile_service.update_profile_by_admin(session, now, user_id, body)
    return ProfileOut.from_user(updated, now.date())
