from fastapi import APIRouter

from app.deps import CompletedUser, SessionDep
from app.schemas.event import CategoryOut
from app.services import event_service

router = APIRouter(prefix="/categories", tags=["events"])


@router.get("")
def list_categories(_: CompletedUser, session: SessionDep) -> list[CategoryOut]:
    return [CategoryOut.model_validate(c) for c in event_service.list_categories(session)]
