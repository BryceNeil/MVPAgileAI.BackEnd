from uuid import UUID
from fastapi import APIRouter, Depends, Form
from fastapi.responses import StreamingResponse

from app.misc.utils import get_profile, validate_token, User as UserProfile
from app.models.Case import Case 
from app.models.GPT import GPT
from app.models.User import User 
from app.schemas.Case import Answer
from app.schemas.User import UserLoginData


"""CONTENT ROUTES"""


content_router = APIRouter(prefix="/api/content")


@content_router.get('/cases')
async def get_topics():
    """Returns a list of cases, and their IDs"""
    return await Case.get_top_cases()


@content_router.get('/case/{case_id}')
async def get_case_questions(case_id: UUID, page: int = 0):
    return await Case(case_id).get_case_questions(page)


@content_router.post('/answer')
async def post_question_answer(answer: Answer):
    return StreamingResponse(
        Case.grade_answer(answer), media_type='text/event-stream'
    )

@content_router.get('/question/{question_id}/chat')
async def get_chat_history(
    question_id: UUID, profile: UserProfile = Depends(get_profile)
):
    return await Case.get_chat_history(question_id, profile.user_id)

# @content_router.get("/question/chat/audio")
# async def get_chat_audio(): 
#     return StreamingResponse(
#         GPT.stream_tts_audio("sample input text"), media_type="audio/mpeg"
#     )

# trial 
@content_router.post("/chat/audio")
async def synthesize_speech(text: str = Form(...)):
    print("DEBUG HERE!!!!")
    return StreamingResponse(
        await GPT.gpt_audio_bytes(text), media_type="audio/mpeg"
    )

    


"""AUTH ROUTES"""


auth_router = APIRouter(prefix="/api/auth")


@auth_router.get('/profile', dependencies=[Depends(validate_token)])
async def get_token(profile: UserProfile = Depends(get_profile)):
    return profile


@auth_router.post('/login')
async def login_user(login_info: UserLoginData):
    return await User.login(login_info)


@auth_router.post('/signup')
async def create_user(login_info: UserLoginData):
    return await User.create_user(login_info)


"""MISC ROUTES"""
