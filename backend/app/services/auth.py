# app/services/auth.py

import structlog
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.config import settings

log = structlog.get_logger(__name__)
security = HTTPBearer()

# Supabase Auth JWKS endpoint (public location)
JWKS_URL = f"{settings.supabase_url}/auth/v1/.well-known/jwks.json"
jwks_client = jwt.PyJWKClient(JWKS_URL)

def get_current_user(auth: HTTPAuthorizationCredentials = Depends(security)) -> str:
    """
    Decodes and verifies the Supabase JWT using dynamic JWKS.
    Supports both ES256 (asymmetric) and HS256 (symmetric).
    """
    token = auth.credentials
    try:
        # 1. Get the signing key from the JWKS (or project secret if HS256)
        # Note: PyJWKClient handles fetching and caching the keys
        unverified_header = jwt.get_unverified_header(token)
        alg = unverified_header.get("alg")
        
        if alg == "HS256":
            # Fallback to standard HS256 if the token is signed with project secret
            key = settings.supabase_jwt_secret
        else:
            # Fetch the public key from Supabase JWKS for ES256/RS256
            signing_key = jwks_client.get_signing_key_from_jwt(token)
            key = signing_key.key

        # 2. Decode and verify
        payload = jwt.decode(
            token, 
            key, 
            algorithms=["HS256", "ES256"],
            # Supabase uses 'authenticated' for the audience claim
            options={"verify_aud": False} 
        )
        
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token: missing sub",
            )
        return user_id

    except jwt.PyJWTError as e:
        log.warning("jwt_verification_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Could not validate credentials: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception as e:
        log.error("auth_system_error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal authentication system error",
        )
