from typing import Annotated, Any
from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, status
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from application.use_cases.abort import AbortUploadUseCase
from application.use_cases.finalize import FinalizeUploadUseCase
from application.use_cases.initiate import InitiateUploadUseCase
from application.use_cases.upload_chunk import UploadChunkUseCase
from configuration.dependencies import (
    get_abort_upload_use_case,
    get_finalize_upload_use_case,
    get_initiate_upload_use_case,
    get_session_repository,
    get_upload_chunk_use_case,
)
from domain.exceptions import (
    ChecksumMismatchError,
    EntityNotFoundError,
    LockAcquisitionError,
    MalwareDetectedError,
    ValidationError,
)
from domain.protocols.session_repository import SessionRepository
from presentation.api.v1.schemas.uploads import InitiateUploadRequest, InitiateUploadResponse


log = structlog.get_logger(__name__)

router = APIRouter(prefix="/v1/uploads", tags=["Uploads"])

security = HTTPBearer()


def get_tenant_id(credentials: HTTPAuthorizationCredentials = Depends(security)) -> UUID:
    """Security dependency to extract and validate tenant UUID from Bearer token."""
    token = credentials.credentials
    try:
        return UUID(token)
    except ValueError:
        # Simple logical fallback for JSON decoding if standard token used
        try:
            import jwt  # type: ignore[import-not-found]

            payload = jwt.decode(token, options={"verify_signature": False})
            return UUID(payload["tenant_id"])
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid Bearer Token. Must be a valid UUID string.",
            )


@router.post("", response_model=InitiateUploadResponse, status_code=status.HTTP_201_CREATED)
async def initiate_upload(
    payload: InitiateUploadRequest,
    tenant_id: Annotated[UUID, Depends(get_tenant_id)],
    use_case: Annotated[InitiateUploadUseCase, Depends(get_initiate_upload_use_case)],
) -> Any:
    """Initiate a new chunked upload session or resolve via pre-upload deduplication."""
    session, s3_uri = await use_case.execute(
        tenant_id=tenant_id,
        file_id=payload.file_id,
        total_size=payload.total_size,
        checksum=payload.checksum,
    )

    if s3_uri:
        # 200 OK indicating deduplication match
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "upload_session_id": None,
                "s3_uri": s3_uri,
                "deduplicated": True,
            },
        )

    assert session is not None
    return {
        "upload_session_id": session.session_id,
        "s3_uri": None,
        "deduplicated": False,
    }


@router.patch("/{session_id}", status_code=status.HTTP_200_OK, response_model=None)
async def upload_chunk(
    session_id: UUID,
    request: Request,
    chunk_index: Annotated[int, Query(alias="index")],
    x_chunk_checksum: Annotated[str, Header()],
    use_case: Annotated[UploadChunkUseCase, Depends(get_upload_chunk_use_case)],
) -> dict[str, Any] | JSONResponse:
    """Upload a raw binary chunk segment of a file."""
    # Read the raw body stream
    data = await request.body()

    try:
        session = await use_case.execute(
            session_id=session_id,
            chunk_index=chunk_index,
            checksum=x_chunk_checksum,
            data=data,
        )
        status_str = "completed" if session.current_offset == session.total_size else "active"
        return {
            "current_offset": session.current_offset,
            "status": status_str,
        }
    except EntityNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ChecksumMismatchError as e:
        # Special Tus-inspired response for integrity conflict
        log.warning(
            "Checksum mismatch during chunk upload",
            session_id=str(session_id),
            chunk_index=chunk_index,
            error=str(e),
        )
        return JSONResponse(status_code=460, content={"detail": "Checksum mismatch."})
    except (ValidationError, LockAcquisitionError) as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.head("/{session_id}", status_code=status.HTTP_200_OK)
async def query_session(
    session_id: UUID,
    repo: Annotated[SessionRepository, Depends(get_session_repository)],
) -> JSONResponse:
    """Query the current state and byte offset of an active upload session."""
    session = await repo.get(session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"UploadSession with id {session_id} not found.",
        )

    status_str = "completed" if session.current_offset == session.total_size else "active"
    headers = {
        "Upload-Offset": str(session.current_offset),
        "Upload-Length": str(session.total_size),
        "Upload-Status": status_str,
    }
    return JSONResponse(
        content={
            "session_id": str(session.session_id),
            "current_offset": session.current_offset,
            "total_size": session.total_size,
            "status": status_str,
        },
        headers=headers,
    )


@router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def abort_upload(
    session_id: UUID,
    use_case: Annotated[AbortUploadUseCase, Depends(get_abort_upload_use_case)],
) -> None:
    """Abort the active session and clean up all cached data."""
    try:
        await use_case.execute(session_id)
    except EntityNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except (ValidationError, LockAcquisitionError) as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/{session_id}/finalize", status_code=status.HTTP_200_OK)
async def finalize_upload(
    session_id: UUID,
    use_case: Annotated[FinalizeUploadUseCase, Depends(get_finalize_upload_use_case)],
) -> dict[str, Any]:
    """Scan, assemble, commit the upload to S3, and trigger downstream processing."""
    try:
        s3_uri = await use_case.execute(session_id)
        return {"s3_uri": s3_uri}
    except EntityNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except MalwareDetectedError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(e))
    except (ValidationError, LockAcquisitionError) as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
