import os
from fastapi import APIRouter, Depends, HTTPException, Request
from authlib.integrations.starlette_client import OAuth
from starlette.config import Config
from .auth import create_access_token

router = APIRouter(prefix="/api/auth", tags=["Authentication"])

# Replace with your actual Google Client ID and Secret
GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET")

config_data = {
    'GOOGLE_CLIENT_ID': GOOGLE_CLIENT_ID,
    'GOOGLE_CLIENT_SECRET': GOOGLE_CLIENT_SECRET
}
starlette_config = Config(environ=config_data)
oauth = OAuth(starlette_config)

oauth.register(
    name='google',
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={
        'scope': 'openid email profile'
    }
)

@router.get('/login')
async def login(request: Request):
    redirect_uri = request.url_for('auth_callback')
    return await oauth.google.authorize_redirect(request, redirect_uri)

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
