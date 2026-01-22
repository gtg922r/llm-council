"""Firebase authentication middleware and utilities."""

import os
from functools import lru_cache
from typing import Optional

import firebase_admin
from firebase_admin import auth, credentials
from fastapi import HTTPException, Request, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from ..config import DEV_AUTH

# Security scheme for OpenAPI docs
security = HTTPBearer(auto_error=False)

# Dev auth constants
DEV_USER_UID = "dev-user-12345"
DEV_USER_EMAIL = "dev@symposia.local"
DEV_USER_NAME = "Dev User"
DEV_AUTH_TOKEN = "dev-token-symposia"


@lru_cache()
def get_firebase_app():
    """Initialize Firebase Admin SDK (singleton)."""
    # Check for service account file
    service_account_path = os.environ.get(
        'FIREBASE_SERVICE_ACCOUNT',
        'firebase-service-account.json'
    )
    
    if os.path.exists(service_account_path):
        cred = credentials.Certificate(service_account_path)
        return firebase_admin.initialize_app(cred)
    else:
        # Try default credentials (for Google Cloud environments)
        try:
            return firebase_admin.initialize_app()
        except Exception as e:
            raise RuntimeError(
                f"Firebase initialization failed. "
                f"Either set FIREBASE_SERVICE_ACCOUNT env var or "
                f"place firebase-service-account.json in project root. "
                f"Error: {e}"
            )


def verify_token(id_token: str) -> dict:
    """Verify a Firebase ID token and return the decoded token.
    
    Args:
        id_token: The Firebase ID token to verify
        
    Returns:
        Decoded token containing user info (uid, email, etc.)
        
    Raises:
        HTTPException: If token is invalid or expired
    """
    # Ensure Firebase is initialized
    get_firebase_app()
    
    try:
        decoded_token = auth.verify_id_token(id_token)
        return decoded_token
    except auth.ExpiredIdTokenError:
        raise HTTPException(
            status_code=401,
            detail="Token has expired. Please sign in again."
        )
    except auth.RevokedIdTokenError:
        raise HTTPException(
            status_code=401,
            detail="Token has been revoked. Please sign in again."
        )
    except auth.InvalidIdTokenError as e:
        raise HTTPException(
            status_code=401,
            detail=f"Invalid token: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=401,
            detail=f"Authentication failed: {str(e)}"
        )


class AuthenticatedUser:
    """Represents an authenticated user."""
    
    def __init__(self, uid: str, email: Optional[str] = None, name: Optional[str] = None):
        self.uid = uid
        self.email = email
        self.name = name
    
    def __repr__(self):
        return f"AuthenticatedUser(uid={self.uid}, email={self.email})"


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> AuthenticatedUser:
    """FastAPI dependency to get the current authenticated user.
    
    Usage:
        @app.get("/api/resource")
        async def get_resource(user: AuthenticatedUser = Depends(get_current_user)):
            return {"user_id": user.uid}
    """
    if credentials is None:
        raise HTTPException(
            status_code=401,
            detail="Authentication required. Please provide a valid token."
        )
    
    token = credentials.credentials
    
    # Dev auth bypass - only available when DEV_AUTH=true
    if DEV_AUTH and token == DEV_AUTH_TOKEN:
        return AuthenticatedUser(
            uid=DEV_USER_UID,
            email=DEV_USER_EMAIL,
            name=DEV_USER_NAME
        )
    
    decoded = verify_token(token)
    
    return AuthenticatedUser(
        uid=decoded['uid'],
        email=decoded.get('email'),
        name=decoded.get('name')
    )


# Optional: dependency that allows unauthenticated access
async def get_optional_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> Optional[AuthenticatedUser]:
    """FastAPI dependency that returns user if authenticated, None otherwise."""
    if credentials is None:
        return None
    
    try:
        token = credentials.credentials
        decoded = verify_token(token)
        return AuthenticatedUser(
            uid=decoded['uid'],
            email=decoded.get('email'),
            name=decoded.get('name')
        )
    except HTTPException:
        return None
