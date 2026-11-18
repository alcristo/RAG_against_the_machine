from pydantic import BaseModel, Field, model_validator
from typing import List
from typing_extensions import Self
import uuid


class MinimalSource(BaseModel):
    """Single source of information"""
    file_path: str
    first_character_index: int
    last_character_index: int

    @model_validator(mode="after")
    def validate_length(self) -> Self:
        if self.last_character_index <= self.first_character_index:
            raise IndexError("end character index is before start")
        return self


class UnansweredQuestion(BaseModel):
    question_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    question: str


class AnsweredQuestion(UnansweredQuestion):
    sources: List[MinimalSource]
    answer: str


class RagDataset(BaseModel):
    """Dataset of RAG questions"""
    rag_questions: List[AnsweredQuestion | UnansweredQuestion]


class MinimalSearchResults(BaseModel):
    """Search results"""
    question_id: str
    question: str
    retrieved_sources: List[MinimalSource]


class MinimalAnswer(MinimalSearchResults):
    """Answer"""
    answer: str


class StudentSearchResults(BaseModel):
    """Search results from the query"""
    search_results: List[MinimalSearchResults]
    k: int


class StudentSearchResultsAndAnswer(BaseModel):
    """Search results and answer"""
    search_results: List[MinimalAnswer]
    k: int
