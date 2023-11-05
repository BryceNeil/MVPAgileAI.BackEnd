from uuid import UUID

from fastapi import HTTPException

from app.data.db import db
from app.schemas.User import UserLoginData
from app.misc.utils import hash_password, verify_password, create_access_token


class User:
    def __init__(self, user_id: UUID):
        self.user_id = user_id

    @classmethod
    async def create_user(cls, login_info: UserLoginData):
        try: 
            hashed_pw = hash_password(login_info.password)
            params = {'email': login_info.email, 'pw': hashed_pw}
            await db.execute(INSERT_USER, params)
        except Exception as exc:
            msg, code = 'Something went wrong creating a user', 400
            if 'already exists' in str(exc):
                msg, code = 'User with that email already exists', 409
            raise HTTPException(status_code=code, detail=msg)

    @classmethod
    async def login(cls, login_info: UserLoginData):
        params ={'email': login_info.email}
        if not (user := await db.fetch_one(GET_USER, params)):
            msg = 'User does not exist'
            raise HTTPException(status_code=404, detail=msg)
        if verify_password(login_info.password, user.password):
            return create_access_token(
                {
                    'user_id': str(user.user_id),
                    'email': user.email
                }
            ) 


INSERT_USER = """
    INSERT INTO individual.account 
    (email, password)
    VALUES (:email, :pw)
"""

GET_USER = """
    SELECT user_id, email, password
    FROM individual.account
    WHERE email = :email
"""
