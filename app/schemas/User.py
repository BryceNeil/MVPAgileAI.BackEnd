from pydantic import BaseModel


class UserLoginData(BaseModel):
    email: str
    password: str
