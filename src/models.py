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

    def __str__(self) -> str:
        return (
            f"{self.file_path} "
            f"[{self.first_character_index},{self.last_character_index}]"
        )


class UnansweredQuestion(BaseModel):
    question_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    question: str

    def __str__(self):
        return self.question


class AnsweredQuestion(UnansweredQuestion):
    sources: List[MinimalSource]
    answer: str

    def __str__(self):
        return super().__str__() + "\n\n" + self.answer


class RagDataset(BaseModel):
    """Dataset of RAG questions"""
    rag_questions: List[AnsweredQuestion | UnansweredQuestion]


class MinimalSearchResults(BaseModel):
    """Search results"""
    question_id: str
    question: str
    retrieved_sources: List[MinimalSource]

    def __str__(self):
        return "\n".join([s.__str__() for s in self.retrieved_sources])


class MinimalAnswer(MinimalSearchResults):
    """Answer"""
    answer: str

    def __str__(self):
        return super().__str__() + "\n\n" + self.answer


class StudentSearchResults(BaseModel):
    """Search results from the query"""
    search_results: List[MinimalSearchResults]
    k: int


class StudentSearchResultsAndAnswer(BaseModel):
    """Search results and answer"""
    search_results: List[MinimalAnswer]
    k: int
