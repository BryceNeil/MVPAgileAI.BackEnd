from http.client import HTTPException
from typing import List
from uuid import UUID

from app.data.db import db
from app.models.GPT import GPT
from app.schemas.Case import CaseOutline, CaseQuestion, Answer
from app.misc.constants import SECRETS


class Case:
    def __init__(self, case_id: UUID):
        self.case_id = case_id

    # new case
    @staticmethod
    async def new_case(job_title):
        # need to check if topic exists in DB first (get_case and get_questions functions)
        # and then call GPT if it does not exist.
        print("DEBUG in here 2,", job_title)
        response = await GPT.get_new_case(job_title)  # Using await for async call
        # need to save job info to database
        return response
        
    @staticmethod
    async def get_top_cases(limit: int = 5) -> List[CaseOutline]:
        return [
            CaseOutline(**co)
            for co in await db.fetch_all(GET_CASES, {'lim': limit})
        ]

    async def get_case_outline(self):
        return CaseOutline(**db.fetch_one(GET_CASE, {'cid': self.case_id}))

    async def get_case_questions(self, page: int) -> List[CaseQuestion]:
        """Grab questions for a case, 5 at at time"""
        return [
            CaseQuestion(**cq) for cq 
            in await db.fetch_all(
                GET_CASE_QUESTIONS, {'cid': self.case_id, 'page': page}
            )
        ]
    
    async def enter_new_case(caseData, user_id):
        try: 
            params = {'title': caseData.get("jobTitle"), 'description': caseData.get("scenario")}
            cResult = await db.execute(INSERT_NEW_CASE, params)
            questions = caseData.get("questions")
            
            qResult = []
            i=0
            
            for question in questions:
                framework = question.get("framework")
                paramsQuestion = {'case_id': cResult, 'question': question.get("question"), 'details': '', 'questionnumber' : question.get('questionNumber'), 'difficultylevel': question.get("difficultyLevel"), 'fr_overview': framework.get('overview')}
                qResult.append(await db.execute(INSERT_NEW_QUESTION, paramsQuestion))
                
                for step in framework.get('steps'):
                    paramsFramework = {'step_number': int(step.get('stepNumber')), 'description': step.get('description'), 'details': step.get('details'), 'question_id': qResult[i]}
                    await db.execute(INSERT_FRAMEWORK, paramsFramework)
                i+=1
        
            params = {'case_id': cResult, 'user_id': user_id}
            await db.execute(INSERT_CASE_ID, params)

            return cResult, qResult
        except Exception as exc:
            msg, code = 'Something went wrong creating a user', 400
            if 'already exists' in str(exc):
                msg, code = 'User with that email already exists', 409
            raise HTTPException(status_code=code, detail=msg)

    async def grade_answer(answer: Answer):
        params = {
            'qid': answer.questionId, 'uid': answer.userId, 
            'a': answer.answer
        }
        qa_pin = await db.execute(INSERT_Q_ANSWER, params)


        # Use async for to iterate over the streamed response
        async for chunk in GPT.get_streamed_response(answer.answer, answer.questionId):
            params = {
                'g': chunk, 'qa_pin': qa_pin
            }
            await db.execute(INSERT_Q_GRADE_INCREMENTAL, params)
            yield "data: " + chunk + "\n\n"

    async def conversation(answer: Answer):
        params = {
            'qid': answer.questionId, 'uid': answer.userId, 
            'message': answer.answer
        }
        
        mid = await db.execute(INSERT_MESSAGE, params)

        gpt_generated_message = ""
        async for chunk in GPT.get_streamed_response(answer.answer, answer.questionId):
            print(chunk)
            gpt_generated_message += chunk
            yield "data: " + chunk + "\n\n"

        print(gpt_generated_message)
        await db.execute(INSERT_GPT_MESSAGE, {
        'qid': answer.questionId,
        'message': gpt_generated_message,  # Inserting the complete GPT-generated message
        'mid': mid
        })

    async def retrieve_case(userId):
        params = {'user_id': userId}
        cidResult = await db.fetch_one(RETRIEVE_CASE_ID, params)
        caseId = cidResult['latest_case_id']
        caseParams = {'case_id': caseId}
        result = await db.fetch_all(RETRIEVE_CASE, caseParams)
        return result

    @staticmethod
    async def get_chat_history(question_id: UUID, user_id: UUID):
        chat_history = []

        params = {'qid': question_id, 'uid': user_id}
        messages = await db.fetch_all(GET_CHAT_HISTORY, params)
        if(len(messages) > 0):
            for message in messages:
                gptParams = {'mid': message.message_id} 
                gptMessage = await db.fetch_one(GET_COMPUTER_HISTORY, gptParams)
                chat_history.append({"from": "user", "text": message.message})
                if(gptMessage):
                    chat_history.append({"from": "computer", "text": gptMessage.message})
            
        return chat_history


"""QUERIES"""

GET_CHAT_HISTORY = """
    SELECT message_id, message
    FROM content.messages
    WHERE question_id = :qid AND user_id = :uid
"""
GET_COMPUTER_HISTORY = """
    SELECT message
    FROM content.gptmessages
    WHERE m_id = :mid
"""


GET_CASES = """
    SELECT 
        case_id AS "caseId", title, description, 
        COALESCE(categories, '{}') AS categories
    FROM content.case
    LIMIT :lim
"""

GET_CASE = """
    SELECT case_id as "caseId", title, description, categories
    FROM content.case
    WHERE case_id = :cid
"""

GET_CASE_QUESTIONS = """
    SELECT 
        question_id as "questionId", title, description,
        COALESCE(skills, '{}') AS skills
    FROM content.question
    WHERE case_id = :cid
    ORDER BY question_id
    LIMIT 5
    OFFSET (:page * 5)
"""

INSERT_Q_ANSWER = """
    INSERT INTO content.question_answer
    (question_id, user_id, answer)
    VALUES (:qid, :uid, :a)
    RETURNING pin
"""

INSERT_Q_GRADE_INCREMENTAL = """
    UPDATE content.question_answer
    SET grade = COALESCE(grade || :g, :g)
    WHERE pin = :qa_pin 
"""

INSERT_NEW_CASE = """
    INSERT INTO content.case 
    (title, description)
    VALUES (:title, :description)
    RETURNING case_id
"""

INSERT_NEW_QUESTION = """
    INSERT INTO content.question
    (case_id, question, details, questionnumber, difficultylevel, fr_overview)
    VALUES (:case_id, :question, :details, :questionnumber, :difficultylevel, :fr_overview)
    RETURNING question_id
"""

INSERT_MESSAGE = """
    INSERT INTO content.messages
    (question_id, user_id, message)
    VALUES (:qid, :uid, :message)
    RETURNING message_id
"""

INSERT_GPT_MESSAGE = """
    INSERT INTO content.gptmessages
    (question_id, message, m_id)
    VALUES (:qid, :message, :mid)
"""

INSERT_CASE_ID = """
    UPDATE individual.account
    SET past_cases = array_append(past_cases, :case_id)
    WHERE user_id = :user_id;
 """

RETRIEVE_CASE_ID = """
    SELECT past_cases[array_length(past_cases, 1)] AS latest_case_id
    FROM individual.account
    WHERE user_id = :user_id;
"""

RETRIEVE_CASE ="""
    SELECT
        c.*,
        q.*,
        f.*
    FROM
        content.case c
    LEFT JOIN
        content.question q ON c.case_id = q.case_id
    LEFT JOIN
        content.framework f ON q.question_id = f.question_id
    WHERE
        c.case_id = :case_id;
"""

INSERT_FRAMEWORK = """
    INSERT INTO content.framework
    (step_number, description, details, question_id)
    VALUES (:step_number, :description, :details, :question_id)
"""