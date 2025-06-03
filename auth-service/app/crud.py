from sqlalchemy.orm import Session
from app import models, schemas
from passlib.context import CryptContext
from datetime import datetime
from uuid import uuid4
import logging

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
logger = logging.getLogger(__name__)

def get_user_by_email(db: Session, email: str):
    return db.query(models.User).filter(models.User.email == email).first()

def get_user_by_username(db: Session, username: str):
    return db.query(models.User).filter(models.User.username == username).first()

def get_user_by_id(db: Session, user_id: str):
    return db.query(models.User).filter(models.User.user_id == user_id).first()

def create_user(db: Session, user: schemas.UserCreate):
    hashed_password = pwd_context.hash(user.password)
    db_user = models.User(
        user_id=uuid4(),
        username=user.username,
        email=user.email,
        first_name=user.first_name,
        last_name=user.last_name,
        contact_no=user.contact_no,
        password=hashed_password,
        is_verified=False,
        is_active=True,
        is_deleted=False,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    logger.info(f"Created user: {db_user.email}")
    return db_user

def get_refresh_token(db: Session, token: str):
    return db.query(models.RefreshToken).filter(models.RefreshToken.refresh_token == token).first()

def store_refresh_token(db: Session, user_id: str, token: str, expires_at: datetime):
    db_token = models.RefreshToken(
        token_id=uuid4(),
        user_id=user_id,
        refresh_token=token,
        expires_at=expires_at,
        created_at=datetime.utcnow(),
        revoked=False
    )
    db.add(db_token)
    db.commit()
    logger.info(f"Stored refresh token for user_id: {user_id}")

def update_refresh_token(db: Session, old_token: str, new_token: str, expires_at: datetime):
    db_token = db.query(models.RefreshToken).filter(models.RefreshToken.refresh_token == old_token).first()
    if db_token:
        db_token.refresh_token = new_token
        db_token.expires_at = expires_at
        db_token.created_at = datetime.utcnow()
        db_token.revoked = False
        db.commit()
        logger.info(f"Updated refresh token: {new_token}")

def revoke_refresh_token(db: Session, token: str):
    db_token = db.query(models.RefreshToken).filter(models.RefreshToken.refresh_token == token).first()
    if db_token:
        db_token.revoked = True
        db.commit()
        logger.info(f"Revoked refresh token: {token}")