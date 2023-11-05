from typing import List
from uuid import UUID
from pydantic import BaseModel

class CaseOutline(BaseModel):
    caseId: UUID
    title: str
    description: str
    categories: List[str] = []

class CaseQuestion(BaseModel):
    questionId: UUID
    title: str
    description: str
    skills: List[str] = []


class Answer(BaseModel):
    questionId: UUID
    userId: UUID
    answer: str
