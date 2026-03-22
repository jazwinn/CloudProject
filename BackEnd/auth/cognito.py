import httpx
from fastapi import HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt
from config import get_settings
from typing import Dict, Any

security = HTTPBearer()

def get_cognito_jwks() -> Dict[str, Any]:
    """Fetch the JSON Web Key Set from Cognito .well-known endpoint."""
    settings = get_settings()
    url = f"https://cognito-idp.{settings.COGNITO_REGION}.amazonaws.com/{settings.COGNITO_USER_POOL_ID}/.well-known/jwks.json"
    response = httpx.get(url)
    response.raise_for_status()
    return response.json()

jwks = None

def get_current_user(credentials: HTTPAuthorizationCredentials = Security(security)) -> str:
    """Dependency inject to parse the JWT Bearer token and extract user sub."""
    global jwks
    settings = get_settings()
    token = credentials.credentials
    
    if not jwks:
        try:
            jwks = get_cognito_jwks()
        except Exception as e:
            raise HTTPException(status_code=500, detail="Could not retrieve JWKS.")

    try:
        # Get unverified headers to parse the Kid
        unverified_header = jwt.get_unverified_header(token)
    except Exception as e:
        raise HTTPException(status_code=401, detail="Invalid token header.")
        
    rsa_key = {}
    for key in jwks["keys"]:
        if key["kid"] == unverified_header.get("kid"):
            rsa_key = {
                "kty": key["kty"],
                "kid": key["kid"],
                "use": key["use"],
                "n": key["n"],
                "e": key["e"]
            }
            break
            
    if not rsa_key:
        raise HTTPException(status_code=401, detail="Invalid kid configuration - matching key not found.")
        
    try:
        issuer = f"https://cognito-idp.{settings.COGNITO_REGION}.amazonaws.com/{settings.COGNITO_USER_POOL_ID}"
        verify_kwargs = {
            "issuer": issuer
        }
        
        # Verify audience/client ID based on token type (id vs access)
        unverified_claims = jwt.get_unverified_claims(token)
        token_use = unverified_claims.get("token_use")
        
        if settings.COGNITO_APP_CLIENT_ID:
            if token_use == "id":
                verify_kwargs["audience"] = settings.COGNITO_APP_CLIENT_ID
            elif token_use == "access":
                if unverified_claims.get("client_id") != settings.COGNITO_APP_CLIENT_ID:
                    raise HTTPException(status_code=401, detail="Invalid client_id claim in access token.")
                    
        payload = jwt.decode(
            token,
            rsa_key,
            algorithms=["RS256"],
            **verify_kwargs
        )
        
        if payload.get("token_use") not in ["id", "access"]:
            raise HTTPException(status_code=401, detail="Invalid token use.")
            
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="Missing sub claim.")
            
        return user_id
        
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token is expired.")
    except jwt.JWTClaimsError as e:
        raise HTTPException(status_code=401, detail=f"Invalid claims: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=401, detail="Invalid token.")
