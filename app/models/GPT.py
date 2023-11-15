import asyncio
import httpx

import io
import openai

from openai import AsyncOpenAI

from fastapi import UploadFile, HTTPException

from uuid import UUID

from pydub import AudioSegment

from app.data.db import db
from app.misc.constants import SECRETS, GPT_TEMPERATURE, GPT_MODEL

INITIAL_PROMPT = """
    You are a highly skilled and detail-orientied management consultant who has worked at top firms such as McKinsey, Bain, and BCG.
    You have been given the following case {{CASE_DETAILS}}.
    The following question is asked of your team: {{QUESTION}}.
    This answer is proposed: {{USER_ANSWER}}

"""

client = AsyncOpenAI(api_key=SECRETS.OPENAI_KEY)

class GPT:
    @classmethod
    async def get_new_case(cls, job_title):
        try:
            prompt = (
                f"Create a structured JSON response for a case interview scenario "
                f"for the job title '{job_title}'. The JSON structure should include:\n"
                f"- 'jobTitle' as a string,\n"
                f"- 'scenario' as a detailed case description,\n"
                f"- 'questions' 5 of them as a list of dictionaries. "
                f"Each dictionary in the list should have keys 'questionNumber', 'question', "
                f"'difficultyLevel', 'relevantSkills', 'rubric' (in the structure outlined below), and the 'framework' dictiionary (in the structure outlined below). "
                f"Format the questions as 'questionNumber': 1, 'question': '<question_text>', "
                f"'difficultyLevel': '<level>', 'relevantSkills': ['<skill1>', '<skill2>']."
                f"- 'rubric': a list of grading criteria, each as a dictionary with 'criterion', 'description', "
                f"and 'weight'.\n"
                f"- 'framework': a dictionary with the following keys:\n"
                f"  'overview': a brief description of the overall problem-solving approach,\n"
                f"  'steps': a list of specific, ordered steps for approaching the problem, each step as a dictionary "
                f"with 'stepNumber', 'description', and 'details'.\n"
                f"Ensure the scenario, questions, rubric, and framework are detailed, realistic, and aligned "
                f"with real-world complexities."
            )
            response = await client.chat.completions.create(
                model=GPT_MODEL,
                response_format={ "type": "json_object" },
                messages=[
                    {"role": "system", "content": "You are a helpful assistant designed to output structured JSON."},
                    {"role": "user", "content": prompt}    
                ]
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"GPT Error: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    @classmethod
    async def get_streamed_response(cls, answer: str, question_id: UUID):
        try:
            # Generate the prompt
            prompt = await cls.get_prompt(answer, question_id)
            print("Prompt: ", prompt)

            # Start the stream
            openai_stream = await client.chat.completions.create(
                model="gpt-4-1106-preview",
                messages=[
                    {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": prompt}
                ],
                stream=True
            )

            # Iterate over the stream asynchronously
            async for chunk in openai_stream:
                print("Stream Chunk Received: ", chunk)
                
                # Checking if 'choices' exists in the chunk and is not empty
                if chunk.choices:
                    first_choice = chunk.choices[0]

                    # Checking if 'delta' exists in the first choice
                    if hasattr(first_choice, 'delta') and first_choice.delta:
                        delta = first_choice.delta

                        # Checking if 'content' exists in delta
                        if hasattr(delta, 'content') and delta.content:
                            print("Chunk Content: ", delta.content)
                            yield delta.content


        except Exception as e:
            print(f"GPT Error: {e}")
            raise HTTPException(status_code=500, detail=str(e))


        # The code block below is useful for debugging the Frontend. It provides
        # A streamed response similar to the type that would be seen from the OpenAI call
        # Comment out the below code when you uncomment the above

        # t = ['really long text', ' really long text', ' really long text',' really long text',' really long text',' really long text',' really long text',' really long text',' really long text',' really long text',' really long text',' really long text']
        # open_ai_stream = (o for o in t + t + t + t + t + t + t)
        # for chunk in open_ai_stream:
        #     await asyncio.sleep(0.25)
        #     yield chunk


    # Text to speech
    @classmethod
    async def gpt_audio_bytes(cls, text: str):
        print("DEBUG HITS")
        response = client.audio.speech.create(
            model="tts-1",
            voice="alloy",
            input=text,
        )
        print("DEBUG TEXT:", text)

        # Convert the binary response content to a byte stream
        byte_stream = io.BytesIO(response.content)

        # Read the audio data from the byte stream
        audio = AudioSegment.from_file(byte_stream, format="mp3")

        # Convert the audio to bytes
        audio_bytes = io.BytesIO()
        audio.export(audio_bytes, format="mp3")

        # Reset the pointer to the beginning of the IO object
        audio_bytes.seek(0)

        return audio_bytes

    # Speech to text
    @classmethod
    async def get_transcription(cls, file: UploadFile):
        print("FILENAME: ", file)
        print("DEBUG 1 Tran")
        audio_bytes = await file.read()
        print("DEBUG 2 Tran")
        audio_stream = io.BytesIO(audio_bytes)
        print("DEBUG 3 Tran")
        transcript = client.audio.transcriptions.create(
            model="whisper-1", 
            file=audio_stream, 
            response_format="text"
        )
        print("DEBUG 4 Tran")
        return transcript["data"]["text"]



    async def get_prompt(answer: str, question_id: UUID) -> str:
        case_question_info = await db.fetch_one(
            GET_CASE_QUESTION_INFO, {'q_id': question_id}
        )
        return (
            INITIAL_PROMPT
            .replace("{{USER_ANSWER}}", answer)
            .replace("{{CASE_DETAILS}}", case_question_info.case_desc)
            .replace("{{QUESTION}}", case_question_info.question)
        )


"""QUERIES"""


GET_CASE_QUESTION_INFO = """
    SELECT 
    C.description AS case_desc,
    Q.title AS question
    FROM content.case AS C
    JOIN content.question AS Q
    ON Q.case_id = C.case_id
    WHERE Q.question_id = :q_id
"""