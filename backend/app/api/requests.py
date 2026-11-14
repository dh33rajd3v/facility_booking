from fastapi import APIRouter, Depends, File, Response, UploadFile
from sqlalchemy.orm import Session

from app.api.deps import (
    document_response,
    get_app_settings,
    get_current_user,
    get_document_storage,
    get_notifier,
)
from app.core.config import Settings
from app.db.models import User
from app.db.session import get_db
from app.schemas.request import (
    EventDetailsIn,
    EventDetailsPatch,
    LineIn,
    LinePatch,
    RequestListOut,
    RequestOut,
    SubmitIn,
    TermsOut,
    TimelineEventOut,
)
from app.services import audit_service
from app.services.document_storage import LocalDocumentStorage
from app.services.notification_service import Notifier
from app.services.request_document_service import RequestDocumentService
from app.services.request_service import RequestService
from app.services.submission_service import SubmissionService, current_terms

router = APIRouter(prefix="/requests", tags=["requests"])


def get_request_service(db: Session = Depends(get_db)) -> RequestService:
    return RequestService(db)


def get_document_service(
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_app_settings),
    storage: LocalDocumentStorage = Depends(get_document_storage),
) -> RequestDocumentService:
    return RequestDocumentService(db, storage, max_bytes=settings.max_upload_mb * 1024 * 1024)


@router.get("/terms", response_model=TermsOut)
def get_terms() -> TermsOut:
    """Current terms and conditions the requester must accept to submit (declared before /{request_id})."""
    return current_terms()


@router.get("", response_model=RequestListOut)
def list_my_requests(
    user: User = Depends(get_current_user), service: RequestService = Depends(get_request_service)
) -> RequestListOut:
    items = service.list_for_user(user)
    return RequestListOut(items=items, total=len(items))


@router.post("", response_model=RequestOut, status_code=201)
def create_draft(
    body: EventDetailsIn,
    user: User = Depends(get_current_user),
    service: RequestService = Depends(get_request_service),
) -> RequestOut:
    return service.create(user, body)


@router.get("/{request_id}", response_model=RequestOut)
def get_request(
    request_id: int, user: User = Depends(get_current_user), service: RequestService = Depends(get_request_service)
) -> RequestOut:
    return service.detail(user, request_id)


@router.patch("/{request_id}", response_model=RequestOut)
def update_event_details(
    request_id: int,
    body: EventDetailsPatch,
    user: User = Depends(get_current_user),
    service: RequestService = Depends(get_request_service),
) -> RequestOut:
    return service.update_event(user, request_id, body)


@router.delete("/{request_id}", status_code=204)
def delete_draft(
    request_id: int,
    user: User = Depends(get_current_user),
    service: RequestService = Depends(get_request_service),
    storage: LocalDocumentStorage = Depends(get_document_storage),
) -> Response:
    stored_name = service.delete(user, request_id)
    if stored_name:
        storage.delete(stored_name)  # the draft's proof document goes with it
    return Response(status_code=204)


@router.post("/{request_id}/lines", response_model=RequestOut, status_code=201)
def add_line(
    request_id: int,
    body: LineIn,
    user: User = Depends(get_current_user),
    service: RequestService = Depends(get_request_service),
) -> RequestOut:
    return service.add_line(user, request_id, body)


@router.patch("/{request_id}/lines/{line_id}", response_model=RequestOut)
def update_line(
    request_id: int,
    line_id: int,
    body: LinePatch,
    user: User = Depends(get_current_user),
    service: RequestService = Depends(get_request_service),
) -> RequestOut:
    return service.update_line(user, request_id, line_id, body)


@router.delete("/{request_id}/lines/{line_id}", response_model=RequestOut)
def delete_line(
    request_id: int,
    line_id: int,
    user: User = Depends(get_current_user),
    service: RequestService = Depends(get_request_service),
) -> RequestOut:
    return service.delete_line(user, request_id, line_id)


@router.post("/{request_id}/submit", response_model=RequestOut)
def submit_request(
    request_id: int,
    body: SubmitIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    notifier: Notifier = Depends(get_notifier),
) -> RequestOut:
    """Submit a draft (or a returned request) to Facilities. Assigns the reference number."""
    return SubmissionService(db, notifier).submit(user, request_id, body)


@router.get("/{request_id}/events", response_model=list[TimelineEventOut])
def get_request_events(
    request_id: int,
    user: User = Depends(get_current_user),
    service: RequestService = Depends(get_request_service),
    db: Session = Depends(get_db),
) -> list[TimelineEventOut]:
    """The requester's own timeline. Staff see timelines through /workflow/requests/{id}."""
    service.get(user, request_id)  # 404 unless it's the user's own request
    return audit_service.timeline(db, request_id)


@router.post("/{request_id}/document", response_model=RequestOut, status_code=201)
def upload_document(
    request_id: int,
    file: UploadFile = File(..., description="PDF, JPG or PNG proof that the organisation is Govt./PSU"),
    user: User = Depends(get_current_user),
    service: RequestDocumentService = Depends(get_document_service),
) -> RequestOut:
    """Attach (or replace) the Govt./PSU proof document of a draft or returned request."""
    data = file.file.read(service.max_bytes + 1)  # one byte more than allowed, to detect oversized files
    return service.upload(user, request_id, file.filename, data)


@router.get("/{request_id}/document")
def get_document(
    request_id: int,
    user: User = Depends(get_current_user),
    service: RequestDocumentService = Depends(get_document_service),
):
    """The requester's own proof document. Facilities opens it through /workflow/requests/{id}/document."""
    return document_response(*service.for_requester(user, request_id))
