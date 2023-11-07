import asyncio
from uuid import UUID

import openai

from app.data.db import db
from app.misc.constants import SECRETS, GPT_TEMPERATURE, GPT_MODEL

INITIAL_PROMPT = """
    You are a highly skilled and detail-orientied management consultant who has worked at top firms such as McKinsey, Bain, and BCG.
    You have been given the following case {{CASE_DETAILS}}.
    The following question is asked of your team: {{QUESTION}}.
    This answer is proposed: {{USER_ANSWER}}

"""

openai.api_key = SECRETS.OPENAI_KEY
class GPT:
    @classmethod
    async def get_streamed_response(cls, answer: str, question_id: UUID):
        # Uncomment when you want to use GPT for real
        openai_stream = await openai.ChatCompletion.acreate(
            model=GPT_MODEL,
            messages=[
                {
                    "role": "user",
                    "content": await cls.get_prompt(answer, question_id)
                }
            ],
            temperature=GPT_TEMPERATURE,
            stream=True
        )
        async for event in openai_stream:
            if "content" in event["choices"][0].delta:
                yield event["choices"][0].delta.content

        # The code block below is useful for debugging the Frontend. It provides
        # A streamed response similar to the type that would be seen from the OpenAI call
        # Comment out the below code when you uncomment the above

        # t = ['really long text', ' really long text', ' really long text',' really long text',' really long text',' really long text',' really long text',' really long text',' really long text',' really long text',' really long text',' really long text']
        # open_ai_stream = (o for o in t + t + t + t + t + t + t)
        # for chunk in open_ai_stream:
        #     await asyncio.sleep(0.25)
        #     yield chunk

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