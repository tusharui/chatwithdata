from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from jose import jwt, JWTError, jwk
from pydantic import BaseModel
import httpx
import json
from app.config import get_settings
from app.database import get_db
from app.models.user import User

router = APIRouter(prefix="/api/auth", tags=["auth"])
settings = get_settings()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

# Clerk JWKS cache
_jwks_cache: dict = {}
_jwks_cache_url: str = ""


async def _get_clerk_jwks() -> dict:
    """Fetch and cache Clerk's JSON Web Key Set."""
    global _jwks_cache, _jwks_cache_url

    # Extract Clerk domain from publishable key
    # pk_test_bG95YWwtZ29yaWxsYS05MS5jbGVyay5hY2NvdW50cy5kZXYk -> accounts.clerk.dev
    pk = settings.CLERK_PUBLISHABLE_KEY
    if not pk:
        raise HTTPException(status_code=500, detail="Clerk not configured")

    # The publishable key is base64 encoded, extract the issuer domain
    # For Clerk, the JWKS URL is https://<issuer>/.well-known/jwks.json
    # We use the Clerk frontend API URL pattern
    if not _jwks_cache:
        # Use Clerk's well-known JWKS endpoint
        # Decode the publishable key to get the domain
        import base64
        try:
            # pk_test_xxx is base64url encoded
            pk_data = pk.split("_")[-1] if "_" in pk else pk
            # Add padding
            pk_data += "=" * (4 - len(pk_data) % 4)
            decoded = base64.urlsafe_b64decode(pk_data).decode()
            # The decoded value is the Clerk domain
            clerk_domain = decoded.rstrip("$")
            jwks_url = f"https://{clerk_domain}/.well-known/jwks.json"
        except Exception:
            # Fallback: try common Clerk domains
            jwks_url = "https://accounts.clerk.dev/.well-known/jwks.json"

        async with httpx.AsyncClient() as client:
            resp = await client.get(jwks_url, timeout=10)
            if resp.status_code == 200:
                _jwks_cache = resp.json()
                _jwks_cache_url = jwks_url

    return _jwks_cache


async def verify_clerk_token(token: str) -> dict:
    """Verify a Clerk JWT and return the payload."""
    try:
        # First try decoding without verification to get the header
        unverified_header = jwt.get_unverified_header(token)
        kid = unverified_header.get("kid")

        # Get JWKS
        jwks = await _get_clerk_jwks()

        # Find the matching key
        public_keys = jwks.get("keys", [])
        signing_key = None
        for key_data in public_keys:
            if key_data.get("kid") == kid:
                signing_key = jwk.construct(key_data)
                break

        if not signing_key:
            raise HTTPException(status_code=401, detail="Invalid token: key not found")

        # Verify the token
        payload = jwt.decode(
            token,
            signing_key,
            algorithms=["RS256"],
            audience="accounts.clerk.dev",
            options={"verify_aud": False},
        )
        return payload

    except JWTError as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=401, detail="Could not validate credentials")


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = await verify_clerk_token(token)
        clerk_user_id = payload.get("sub")
        if clerk_user_id is None:
            raise credentials_exception
    except HTTPException:
        raise credentials_exception

    # Find or create user by clerk_id
    result = await db.execute(select(User).where(User.clerk_id == clerk_user_id))
    user = result.scalar_one_or_none()

    if user is None:
        # Auto-create user from Clerk token
        email = payload.get("email_addresses", [{}])
        if isinstance(email, list) and len(email) > 0:
            email = email[0].get("email_address", "") if isinstance(email[0], dict) else ""
        elif isinstance(email, str):
            pass
        else:
            email = ""

        name = payload.get("first_name", "") or payload.get("username", "") or email.split("@")[0] if email else "User"

        user = User(
            clerk_id=clerk_user_id,
            email=email,
            name=name,
            hashed_password="clerk_managed",
        )
        db.add(user)
        try:
            await db.flush()
            await db.commit()
        except Exception:
            await db.rollback()
            # Race condition: another request created the user
            result = await db.execute(select(User).where(User.clerk_id == clerk_user_id))
            user = result.scalar_one_or_none()
            if user is None:
                raise credentials_exception

    return user


@router.post("/sync")
async def sync_user(user: User = Depends(get_current_user)):
    """Sync Clerk user to the database. Creates the user if they don't exist."""
    return {"id": user.id, "email": user.email, "name": user.name}
