import os
import logging

logger = logging.getLogger(__name__)
from fastapi import APIRouter, Depends, HTTPException, Request
from authlib.integrations.starlette_client import OAuth
from starlette.config import Config
from .auth import create_access_token

router = APIRouter(prefix="/auth", tags=["Authentication"])

# Replace with your actual Google Client ID and Secret
GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET")

if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
    logger.error("MISSING GOOGLE_CLIENT_ID or GOOGLE_CLIENT_SECRET in environment variables!")

config_data = {
    'GOOGLE_CLIENT_ID': GOOGLE_CLIENT_ID or "",
    'GOOGLE_CLIENT_SECRET': GOOGLE_CLIENT_SECRET or ""
}
starlette_config = Config(environ=config_data)
oauth = OAuth(starlette_config)

oauth.register(
    name='google',
    client_id=GOOGLE_CLIENT_ID,
    client_secret=GOOGLE_CLIENT_SECRET,
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    access_token_url='https://oauth2.googleapis.com/token',
    authorize_url='https://accounts.google.com/o/oauth2/v2/auth',
    userinfo_endpoint='https://openidconnect.googleapis.com/v1/userinfo',
    jwks_uri='https://www.googleapis.com/oauth2/v3/certs',
    client_kwargs={
        'scope': 'openid email profile'
    }
)

@router.get('/login')
async def login(request: Request):
    # Force https for the redirect_uri in production
    url = str(request.url_for('auth_callback'))
    if "localhost" not in url:
        url = url.replace("http://", "https://")
    logger.info(f"Initiating Google login. Redirect URI: {url}")
    return await oauth.google.authorize_redirect(request, url)

from fastapi.responses import RedirectResponse
import json
import urllib.parse

FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://localhost:4200")

@router.get('/callback', name='auth_callback')
async def auth_callback(request: Request):
    try:
        token = await oauth.google.authorize_access_token(request)
        user_info = token.get('userinfo')
        if not user_info:
            raise HTTPException(status_code=400, detail="Failed to get user info from Google")
        
        user_id = user_info['sub']
        access_token = create_access_token(data={
            "sub": user_id, 
            "email": user_info.get("email"), 
            "name": user_info.get("name")
        })
        
        # Redirect back to frontend with token and user info
        params = {
            "token": access_token,
            "id": user_id,
            "name": user_info.get("name"),
            "email": user_info.get("email"),
            "picture": user_info.get("picture")
        }
        query_string = urllib.parse.urlencode(params)
        return RedirectResponse(url=f"{FRONTEND_URL}?{query_string}")
        
    except Exception as e:
        logger.error(f"OAuth error: {e}")
        return RedirectResponse(url=f"{FRONTEND_URL}?error=auth_failed")

# In-memory user database for demo purposes
# In production, use a real database
USERS_DB = {}

from pydantic import BaseModel, EmailStr
from .auth import get_password_hash, verify_password

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    name: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

@router.post('/local/register')
async def local_register(user: UserCreate):
    if user.email in USERS_DB:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    hashed_password = get_password_hash(user.password)
    USERS_DB[user.email] = {
        "email": user.email,
        "hashed_password": hashed_password,
        "name": user.name,
        "id": user.email # Using email as ID for local auth
    }
    
    return {"message": "User registered successfully"}

@router.post('/local/login')
async def local_login(user: UserLogin):
    db_user = USERS_DB.get(user.email)
    if not db_user or not verify_password(user.password, db_user["hashed_password"]):
        raise HTTPException(status_code=401, detail="Incorrect email or password")
        
    access_token = create_access_token(data={
        "sub": db_user["id"],
        "email": db_user["email"],
        "name": db_user["name"]
    })
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": db_user["id"],
            "email": db_user["email"],
            "name": db_user["name"],
            "picture": ""
        }
    }
