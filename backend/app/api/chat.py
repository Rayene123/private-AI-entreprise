from fastapi import APIRouter, Depends

from app.core.security import get_current_user
from app.schemas.auth import AuthenticatedUser
from app.schemas.generation import AskRequest, AnswerResponse
from app.schemas.retrieval import RetrievalRequest, RetrievalResponse
from app.services.document_service import DocumentService
from app.services.permission_service import (
    AuthorizationService,
    get_authorization_service,
)
from app.services.retrieval_service import RetrievalService
from app.services.generation_service import GenerationService

router = APIRouter(prefix="/chat", tags=["chat"])


def get_chat_retrieval_service(
    authorization_service: AuthorizationService = Depends(get_authorization_service),
) -> RetrievalService:
    return RetrievalService(
        DocumentService(authorization_service),
        authorization_service,
    )


def get_generation_service(
    retrieval_service: RetrievalService = Depends(get_chat_retrieval_service),
) -> GenerationService:
    return GenerationService(retrieval_service)


@router.post("/retrieve", response_model=RetrievalResponse)
async def retrieve(
    request: RetrievalRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
    retrieval_service: RetrievalService = Depends(get_chat_retrieval_service),
) -> RetrievalResponse:
    return retrieval_service.retrieve(
        current_user.id,
        request.query,
        request.top_k,
    )


@router.post("/ask", response_model=AnswerResponse)
async def ask(
    request: AskRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
    generation_service: GenerationService = Depends(get_generation_service),
) -> AnswerResponse:
    return generation_service.ask(current_user.id, request.query)