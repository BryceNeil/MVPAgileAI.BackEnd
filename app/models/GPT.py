import asyncio
import json
import httpx

import io
import openai

from openai import AsyncOpenAI

from fastapi import UploadFile, HTTPException

from uuid import UUID

from pydub import AudioSegment

from app.data.db import db
from app.misc.constants import SECRETS, GPT_TEMPERATURE, GPT_MODEL

# # need to feed in the case and given question here. 
# INITIAL_PROMPT = """
#     You are a highly knowledgable and helpful assistant to a person applying for a position at a top firm. He is trying to answer a question relating to a case given to him by a recruiter of a top firm interviewing him for a position.
#     He has been given the following case {{CASE_DETAILS}}.
#     The following question is asked of him: {{QUESTION}}.
#     While the person you are assisting works towards his answer, he will converse with you to assist him along the way. This means you should keep your answers brief, a maximum of four sentences, and only 
#     providing hints or small instructions. 
#     He inquires the following: 
#     {{USER_ANSWER}}

# """

INITIAL_CONVO_PROMPT = """
    You are a highly knowledgable and helpful assistant to a person applying for a position at a top firm. He is trying to answer a question relating to a case given to him by a recruiter of a top firm interviewing him for a position.
    He has been given the following case {{CASE_DETAILS}}.
    The following question is asked of him: {{QUESTION}}.
    While the person you are assisting works towards his answer, he will converse with you to assist him along the way. This means you should keep your answers brief, a maximum of three sentences but less is ideal, and only 
    providing hints or small instructions when directly asked.
    If not directly asked, provide short relevant small talk as if you were a friendly tutor, remind them you are there to assist.
    He inquires the following: 
    {{MESSAGE}}}
"""

EVAL_PROMPT = """
    You are a harsh professor grading a students response to a question relating to a case you've given them. The case scenario you've challenged them with is: 
    {{SCENARIO}} 
    and the question they are answering is
    {{QUESTION}}
    You need to evaluate the answer based on three criteria. The first of which is 
    {{CRITERIA_ONE}} 
    and you are to score the answer on weather or not the student {{DESCRIPTION_ONE}}.
    The seond of which is
    {{CRITERIA_TWO}}
    and you are to score this answer on weather or not the student {{DESCRIPTION_TWO}}.
    The final criterion is 
    {{CRITERIA_THREE}}
    and this is to be evaluated on weather or not the student {{DESCRIPTION_THREE}}.
    Assume all answers begin at zero and remain there unless the specific criteria is met. Grade them on all numbers on the set 0 to 100.
    The answer the student gave to the question is:    
    {{USER_ANSWER}}.
    For each of the three criteria, provide a specific grade out of 100 and return only the three grades as an array in a structured JSON format with one element: grades: [x,y,z]. Do not be afraid to give a zero if answer is blank or poorly crafted.
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
            # Generate the prompt - this is where DATA SCIENCE ERROR COMES FROM
            
            prompt = await cls.get_convo_prompt(answer, question_id)
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
                
                # Checking if 'choices' exists in the chunk and is not empty
                if chunk.choices:
                    first_choice = chunk.choices[0]

                    # Checking if 'delta' exists in the first choice
                    if hasattr(first_choice, 'delta') and first_choice.delta:
                        delta = first_choice.delta

                        # Checking if 'content' exists in delta
                        if hasattr(delta, 'content') and delta.content:
                            yield delta.content


        except Exception as e:
            print(f"GPT Error: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @classmethod
    async def evaluate(cls, answer, userId, questionId, rubric, question, case):
        try:
            print(rubric)
            prompt = await cls.get_eval_prompt(answer, rubric, question, case)
            response = await client.chat.completions.create(
                model=GPT_MODEL,
                response_format={"type": "json_object"},
                messages = [
                    {
                        "role": "system",
                        "content": "You are an evaluator designed to output structured three-element array of grades"
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )
            grades_vals = json.loads(response.choices[0].message.content)['grades']
            i=0
            for grade in grades_vals:
                params= {'grade': grade, 'question_id': questionId, 'criterion': rubric[i]['criterion']}
                print(params)
                await db.execute(INSERT_GRADE, params)
                i+=1
            paramsAnswer = {'question_id': questionId, 'user_id': userId, 'answer': answer}
            await db.execute(INSERT_ANSWER, paramsAnswer)
            return response.choices[0].message.content

        except Exception as e:
            print(f"Error in evaluate method: {e}")
            # Handle the error as needed, e.g., log the error, raise an HTTPException, etc.
            raise HTTPException(status_code=500, detail=str(e))


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

    async def get_convo_prompt(message: str, question_id: UUID) -> str:
        case_question_info = await db.fetch_one(
            GET_CASE_QUESTION_INFO, {'q_id': question_id}
        )
        return (
            INITIAL_CONVO_PROMPT
            .replace("{{CASE_DETAILS}}", case_question_info.case_desc)
            .replace("{{QUESTION}}", case_question_info.question)
            .replace("{{MESSAGE}}", message)
        )
    
    async def get_eval_prompt(answer: str, rubric, question, scenario) -> str:
        criteria = [item['criterion'] for item in rubric]
        descriptions = [item['description'] for item in rubric]
        return (
            EVAL_PROMPT
            .replace("{{SCENARIO}}", scenario)
            .replace("{{QUESTION}}", question)
            .replace("{{CRITERIA_ONE}}", criteria[0])
            .replace("{{DESCRIPTION_ONE}}", descriptions[0])
            .replace("{{CRITERIA_TWO}}", criteria[1])
            .replace("{{DESCRIPTION_TWO}}", descriptions[1])
            .replace("{{CRITERIA_THREE}}", criteria[2])
            .replace("{{DESCRIPTION_THREE}}", descriptions[2])
            .replace("{{USER_ANSWER}}", answer)
            )


    async def get_prompt(answer: str, question_id: UUID) -> str:
        case_question_info = await db.fetch_one(
            GET_CASE_QUESTION_INFO, {'q_id': question_id}
        )
        return (
            INITIAL_CONVO_PROMPT
            .replace("{{USER_ANSWER}}", answer)
            .replace("{{CASE_DETAILS}}", case_question_info.case_desc)
            .replace("{{QUESTION}}", case_question_info.question)
        )


"""QUERIES"""


GET_CASE_QUESTION_INFO = """
    SELECT 
    C.description AS case_desc,
    Q.question AS question
    FROM content.case AS C
    JOIN content.question AS Q
    ON Q.case_id = C.case_id
    WHERE Q.question_id = :q_id
"""

INSERT_GRADE = """
    UPDATE content.rubric
    SET grade = :grade
    WHERE question_id = :question_id AND criterion = :criterion;

"""

INSERT_ANSWER = """
    INSERT INTO content.question_answer
    (question_id, user_id, answer)
    VALUES (:question_id, :user_id, :answer)
"""