from datetime import timedelta, datetime
import time
from typing import Optional 
from uuid import UUID 
import hashlib
from fastapi import HTTPException, Request, Depends, status
from fastapi.security import (
    OAuth2PasswordBearer,
    OAuth2PasswordRequestForm,
    HTTPAuthorizationCredentials,
    HTTPBearer,
)
from jose import jwt
from pydantic import BaseModel
from passlib.context import CryptContext

from app.misc.constants import SECRETS

# Random secret key, will get a better approach to making it in prod
SECRET_KEY = "09d25e094faa6ca2556c818166b7a9563b93f7099f6f0f4caa6cf63b88e8d3e7"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
auth_login = OAuth2PasswordRequestForm
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


class UserProfile(BaseModel):
    user_id: UUID
    email: str = None


def get_profile():
    decoded = decode_token(global_token.jwt)
    return UserProfile(user_id=decoded["user_id"], email=decoded["email"])


def decode_token(access_token: str):
    return jwt.decode(access_token, SECRET_KEY, algorithms=[ALGORITHM])


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(days=365)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


class User(BaseModel):
    user_id: UUID 
    email: str | None = None


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(raw_password: str):
    md5_hash_object = hashlib.md5()

    # Update the hash object with the input string
    md5_hash_object.update(raw_password.encode('utf-8'))

    # Get the hexadecimal representation of the hash
    hashed_string = md5_hash_object.hexdigest()

    return hashed_string


def verify_password(raw_password: str, hashed_password: str):
    md5_hash_object = hashlib.md5()

    # Update the hash object with the input string
    md5_hash_object.update(raw_password.encode('utf-8'))

    # Get the hexadecimal representation of the hash
    hashed_string = md5_hash_object.hexdigest()
    if hashed_string == hashed_password:
        return True
    return False


class Token:
    def __init__(self, token: str):
        self.token = token
        self.claims = self.__get_claims()

    def validate(self):
        if exp_time := self.claims.get("exp"):
            if exp_time <= time.time():
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

    def __get_claims(self):
        try:
            return decode_token(self.token)
        except Exception as exc:
            raise HTTPException(status_code=400) from exc


def validate_token(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer())
):
    try:
        token = Token(credentials.credentials)
        token.validate()
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED) from exc
    else:
        global_token.jwt = credentials.credentials
        request.state.user_id = token.claims["user_id"]


class UserToken:
    _instance = None
    jwt = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(UserToken, cls).__new__(cls)
        return cls._instance


global_token = UserToken()
