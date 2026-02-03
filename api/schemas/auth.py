from pydantic import BaseModel


class LoginRequest(BaseModel):
    password: str


class SetupRequest(BaseModel):
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    username: str
    settings: dict


# Account management
class UsernameChangeRequest(BaseModel):
    username: str


class PasswordChangeRequest(BaseModel):
    current_password: str
    new_password: str


# Token / API key management
class CreateApiKeyRequest(BaseModel):
    name: str
    scope: str = "read_write"  # read | read_write


class TokenListItem(BaseModel):
    id: str
    token_type: str
    name: str | None
    scope: str
    ip_address: str | None
    user_agent: str | None
    last_used_at: str | None
    created_at: str
    is_current: bool


class ApiKeyCreatedResponse(BaseModel):
    id: str
    name: str
    scope: str
    raw_token: str
