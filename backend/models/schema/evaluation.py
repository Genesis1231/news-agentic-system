from config import logger
from pydantic import BaseModel, Field, field_validator
from typing import Literal 

# Enums for evaluation fields
ENUM_DECISION = Literal["YES", "NO"]

class Evaluation(BaseModel):
    """Schema for content evaluation results"""

    evaluation_analysis: str = Field(..., description="Analysis of the evaluation.")

    final_decision: ENUM_DECISION = Field(
        ...,
        description="Final decision on content acceptance. YES or NO?",
    )

    editorial_note: str = Field(..., description="Editorial notes.")

    deep_dive: bool = Field(
        default=False,
        description="Whether this news warrants in-depth research and analysis beyond a flash report."
    )

    additional_research: list[str] = Field(
        default_factory=list,
        description="Additional researches in short phrases."
    )

    @field_validator('final_decision', mode='before')
    def validate_decision(cls, v):
        """Normalize casing — Pydantic's Literal type handles invalid values."""
        if isinstance(v, str):
            return v.upper()
        return "NO"

    @field_validator('additional_research', mode='before')
    def validate_research(cls, v):
        """Validate the additional research list."""
        if isinstance(v, str):
            logger.warning(f"Invalid single value {v}, converted to list")
            return [v]
        if isinstance(v, list):
            return v
        return []
        