from uuid import UUID

from fastapi import APIRouter, Depends, File, Response, UploadFile, status

from app.core.security import get_current_user
from app.schemas.auth import AuthenticatedUser
from app.schemas.document import (
    DocumentCreate,
    DocumentListItem,
    DocumentResponse,
    DocumentUpdate,
)
from app.services.document_service import DocumentService
from app.services.permission_service import (
    AuthorizationService,
    get_authorization_service,
)

router = APIRouter(prefix="/documents", tags=["documents"])


def get_document_service(
    authorization_service: AuthorizationService = Depends(get_authorization_service),
) -> DocumentService:
    return DocumentService(authorization_service)


@router.post(
    "",
    response_model=DocumentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_document(
    document_create: DocumentCreate,
    current_user: AuthenticatedUser = Depends(get_current_user),
    document_service: DocumentService = Depends(get_document_service),
) -> DocumentResponse:
    return document_service.create_document(current_user.id, document_create)


@router.get("", response_model=list[DocumentListItem])
async def list_documents(
    current_user: AuthenticatedUser = Depends(get_current_user),
    document_service: DocumentService = Depends(get_document_service),
) -> list[DocumentListItem]:
    return document_service.list_documents(current_user.id)


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: UUID,
    current_user: AuthenticatedUser = Depends(get_current_user),
    document_service: DocumentService = Depends(get_document_service),
) -> DocumentResponse:
    return document_service.get_document(current_user.id, document_id)


@router.patch("/{document_id}", response_model=DocumentResponse)
async def update_document(
    document_id: UUID,
    document_update: DocumentUpdate,
    current_user: AuthenticatedUser = Depends(get_current_user),
    document_service: DocumentService = Depends(get_document_service),
) -> DocumentResponse:
    return document_service.update_document(
        current_user.id,
        document_id,
        document_update,
    )


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    document_id: UUID,
    current_user: AuthenticatedUser = Depends(get_current_user),
    document_service: DocumentService = Depends(get_document_service),
) -> Response:
    document_service.delete_document(current_user.id, document_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{document_id}/file", response_model=DocumentResponse)
async def upload_document_file(
    document_id: UUID,
    file: UploadFile = File(...),
    current_user: AuthenticatedUser = Depends(get_current_user),
    document_service: DocumentService = Depends(get_document_service),
) -> DocumentResponse:
    content = await file.read()
    return document_service.upload_document_file(
        current_user.id,
        document_id,
        filename=file.filename,
        content_type=file.content_type,
        content=content,
    )


@router.get("/{document_id}/file")
async def download_document_file(
    document_id: UUID,
    current_user: AuthenticatedUser = Depends(get_current_user),
    document_service: DocumentService = Depends(get_document_service),
) -> Response:
    document_file = document_service.download_document_file(
        current_user.id,
        document_id,
    )
    return Response(
        content=document_file.content,
        media_type=document_file.mime_type,
        headers={
            "Content-Disposition": (
                f'attachment; filename="{document_file.filename}"'
            ),
        },
    )