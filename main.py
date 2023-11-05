from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.misc.constants import SECRETS
from app.data.db import db
from app.routes.routes import content_router, auth_router


# local
origins = [
    "http://127.0.0.1",
    "*"
]

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(content_router)
app.include_router(auth_router)

@app.on_event("startup")
async def startup():
    if SECRETS.ENV_NAME == "local":
        print("DOCS AVAILABLE ON http://127.0.0.1:8000/docs")
    await db.connect()
