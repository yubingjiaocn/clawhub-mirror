"""Authentication router: login/logout and API key management."""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel

from .. import dynamodb
from ..auth import verify_password, generate_api_token, get_current_user

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    token: str
    username: str
    role: str


class CreateApiKeyRequest(BaseModel):
    label: str = ""


class ApiKeyResponse(BaseModel):
    keyId: str
    label: str
    tokenPrefix: str
    createdAt: int


class ApiKeyCreatedResponse(BaseModel):
    keyId: str
    label: str
    token: str
    createdAt: int


@router.post("/login", response_model=LoginResponse)
async def login(body: LoginRequest) -> LoginResponse:
    user = dynamodb.get_user(body.username)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password.",
        )
    if not user.get("isActive", True):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Account is deactivated.",
        )
    stored_hash = user.get("hashedPassword", "")
    if not stored_hash or not verify_password(body.password, stored_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password.",
        )

    session_token = generate_api_token()
    dynamodb.put_session(username=body.username, session_token=session_token)

    return LoginResponse(
        token=session_token,
        username=user["username"],
        role=user["role"],
    )


@router.post("/logout")
async def logout(request: Request) -> dict:
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header.removeprefix("Bearer ").strip()
        if token:
            dynamodb.delete_session(token)
    return {"detail": "Logged out."}


# --- API Key Management ---

@router.get("/keys", response_model=list[ApiKeyResponse])
async def list_api_keys(user: dict = Depends(get_current_user)) -> list[ApiKeyResponse]:
    keys = dynamodb.list_api_keys(user["username"])
    return [
        ApiKeyResponse(
            keyId=k["keyId"],
            label=k.get("label", ""),
            tokenPrefix=k.get("tokenPrefix", ""),
            createdAt=k.get("createdAt", 0),
        )
        for k in keys
    ]


@router.post("/keys", response_model=ApiKeyCreatedResponse)
async def create_api_key(
    body: CreateApiKeyRequest,
    user: dict = Depends(get_current_user),
) -> ApiKeyCreatedResponse:
    # Limit to 10 active keys per user
    existing = dynamodb.list_api_keys(user["username"])
    if len(existing) >= 10:
        raise HTTPException(
            status_code=400,
            detail="Maximum of 10 API keys per user.",
        )

    token = generate_api_token()
    item = dynamodb.put_api_key(
        username=user["username"],
        token=token,
        label=body.label,
    )

    return ApiKeyCreatedResponse(
        keyId=item["keyId"],
        label=item.get("label", ""),
        token=token,
        createdAt=item["createdAt"],
    )


@router.delete("/keys/{key_id}")
async def revoke_api_key(
    key_id: str,
    user: dict = Depends(get_current_user),
) -> dict:
    success = dynamodb.revoke_api_key(user["username"], key_id)
    if not success:
        raise HTTPException(status_code=404, detail="API key not found.")
    return {"detail": "API key revoked."}
