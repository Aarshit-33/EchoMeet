from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from app import crud, schemas, models
from app.dependencies import get_db, create_access_token, create_refresh_token, verify_password
from datetime import timedelta
from authlib.integrations.starlette_client import OAuth
from starlette.config import Config
import os
from dotenv import load_dotenv
import logging

load_dotenv()

router = APIRouter()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Google OAuth configuration
config = Config(environ=os.environ)
oauth = OAuth(config)
oauth.register(
    name='google',
    client_id=os.getenv("GOOGLE_CLIENT_ID"),
    client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={'scope': 'openid email profile'}
)

@router.post("/register", response_model=schemas.User)
async def register(user: schemas.UserCreate, db: Session = Depends(get_db)):
    logger.info(f"Registering user: {user.email}")
    if crud.get_user_by_email(db, user.email):
        raise HTTPException(status_code=400, detail="Email already registered")
    if crud.get_user_by_username(db, user.username):
        raise HTTPException(status_code=400, detail="Username already registered")
    return crud.create_user(db, user)

@router.post("/token", response_model=schemas.Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    logger.info(f"Login attempt for username: {form_data.username}")
    user = crud.get_user_by_username(db, form_data.username)
    if not user or not verify_password(form_data.password, user.password):
        raise HTTPException(status_code=400, detail="Incorrect username or password")
    if not user.is_active or user.is_deleted:
        raise HTTPException(status_code=403, detail="Account inactive or deleted")
    access_token = create_access_token(data={"sub": str(user.user_id)})
    refresh_token, expires_at = create_refresh_token(data={"sub": str(user.user_id)})
    crud.store_refresh_token(db, user.user_id, refresh_token, expires_at)
    return {"access_token": access_token, "refresh_token": refresh_token, "token_type": "bearer"}

@router.post("/refresh", response_model=schemas.Token)
async def refresh_token(token: schemas.RefreshToken, db: Session = Depends(get_db)):
    logger.info("Refreshing token")
    refresh_token = crud.get_refresh_token(db, token.refresh_token)
    if not refresh_token or refresh_token.revoked:
        raise HTTPException(status_code=401, detail="Invalid or revoked refresh token")
    user = crud.get_user_by_id(db, refresh_token.user_id)
    if not user or not user.is_active or user.is_deleted:
        raise HTTPException(status_code=403, detail="Invalid user")
    access_token = create_access_token(data={"sub": str(user.user_id)})
    new_refresh_token, expires_at = create_refresh_token(data={"sub": str(user.user_id)})
    crud.update_refresh_token(db, token.refresh_token, new_refresh_token, expires_at)
    return {"access_token": access_token, "refresh_token": new_refresh_token, "token_type": "bearer"}

@router.post("/logout")
async def logout(token: schemas.RefreshToken, db: Session = Depends(get_db)):
    logger.info("Logging out user")
    refresh_token = crud.get_refresh_token(db, token.refresh_token)
    if not refresh_token:
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    crud.revoke_refresh_token(db, token.refresh_token)
    return {"message": "Logged out successfully"}

@router.get("/login/google")
async def login_google(request: Request):
    redirect_uri = os.getenv("GOOGLE_REDIRECT_URI")
    logger.info(f"Starting Google OAuth with redirect_uri: {redirect_uri}")
    response = await oauth.google.authorize_redirect(request, redirect_uri)
    logger.debug(f"Session after authorize_redirect: {request.session}")
    return response

@router.get("/google/callback")
async def auth_google(request: Request, db: Session = Depends(get_db)):
    try:
        logger.info("Processing Google OAuth callback")
        logger.debug(f"Session before authorize_access_token: {request.session}")
        token = await oauth.google.authorize_access_token(request)
        user_info = token.get('userinfo')
        if user_info:
            email = user_info['email']
            username = email.split('@')[0]
            first_name = user_info.get('given_name', '')
            last_name = user_info.get('family_name', '')
            user = crud.get_user_by_email(db, email)
            if not user:
                user_data = schemas.UserCreate(
                    username=username,
                    email=email,
                    password="google-oauth",
                    first_name=first_name,
                    last_name=last_name
                )
                user = crud.create_user(db, user_data)
            if not user.is_active or user.is_deleted:
                raise HTTPException(status_code=403, detail="Account inactive or deleted")
            access_token = create_access_token(data={"sub": str(user.user_id)})
            refresh_token, expires_at = create_refresh_token(data={"sub": str(user.user_id)})
            crud.store_refresh_token(db, user.user_id, refresh_token, expires_at)
            logger.info(f"Google OAuth successful for {email}")
            return {"access_token": access_token, "refresh_token": refresh_token, "token_type": "bearer"}
    except Exception as e:
        logger.error(f"Google OAuth error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))