from uuid import UUID
from fastapi import APIRouter, Depends, Form, UploadFile, File, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.requests import Request

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
@content_router.post('/conversation')
async def post_convo(answer: Answer):
    return StreamingResponse(
        Case.conversation(answer), media_type='text/event-stream'
    )

@content_router.get('/question/{question_id}/chat')
async def get_chat_history(question_id: UUID, profile: UserProfile = Depends(get_profile)):
    return await Case.get_chat_history(question_id, profile.user_id)



# @content_router.get("/question/chat/audio")
# async def get_chat_audio(): 
#     return StreamingResponse(
#         GPT.stream_tts_audio("sample input text"), media_type="audio/mpeg"
#     )



# TTS - text to speech
@content_router.post("/chat/audio")
async def synthesize_speech(text: str = Form(...)):
    print("DEBUG HERE!!!!")
    return StreamingResponse(
        await GPT.gpt_audio_bytes(text), media_type="audio/mpeg"
    )

# STT - speech to text
@content_router.post("/transcribe")
async def transcribe_audio(file: UploadFile = File(...)):
    print("DEBUG: in transcribe")
    return await GPT.get_transcription(file)

# Creating new case 
@content_router.post("/create/case")
async def create_case(request: Request):
    try:
        # Extract job title from request body
        job_title = await request.body()
        job_title = job_title.decode('utf-8')  # Decode bytes to string

        print("recieved: ", job_title)
        
        # Pass job title to the Case.new_case method
        response = await Case.new_case(job_title)
        # print("DEBUG: new_case method returned successfully.", response)  # Print after successful execution
        return response 
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@content_router.post("/enter/case")
async def enter_case(request: Request):
    try:
        case_data = await request.json()  # Retrieve JSON data from the request body
        # print("Received case data:", case_data.get("jobTitle"))
        resp_data = await Case.enter_new_case(case_data)
        print(resp_data)
        return resp_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    

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
