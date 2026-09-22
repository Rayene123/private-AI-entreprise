from pydantic import BaseModel, ConfigDict


class ErrorDetail(BaseModel):
    code: str
    message: str
    request_id: str

    model_config = ConfigDict(extra="forbid")


class ErrorResponse(BaseModel):
    error: ErrorDetail

    model_config = ConfigDict(extra="forbid")
