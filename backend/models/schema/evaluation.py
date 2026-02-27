from config import logger
from pydantic import BaseModel, Field, field_validator
from typing import List 

# Enums for evaluation fields
ENUM_COVERAGE = ["FLASH", "BRIEF", "SCOOP", "ANALYSIS", "DEEP_DIVE", "N/A"]
ENUM_DECISION = ["YES", "NO"]
ENUM_AUDIENCE = ["TECH_ENTHUSIASTS", "DEVELOPERS", "EXECUTIVES", "INVESTORS", "RESEARCHERS", "GENERAL_PUBLIC"]

class Evaluation(BaseModel):
    """Schema for content evaluation results"""
    
    evaluation_analysis: str = Field(..., description="Analysis of the evaluation.")
    
    final_decision: str = Field(
        ...,
        description="Final decision on content acceptance. YES or NO?",
        enum=ENUM_DECISION
    )
    
    # audience: str = Field( 
    #     default="TECH_ENTHUSIASTS",    
    #     description="Recommended target audience.",
    #     enum=ENUM_AUDIENCE
    # )
    
    editorial_note: str = Field(..., description="Editorial notes.")

    coverage_depth: str = Field(
        default="N/A",
        description="Recommended depth of coverage. ",
        enum=ENUM_COVERAGE
    )
        
    additional_research: List[str] = Field(
        default=[],
        description="Additional researches in short phrases."
    )

    @field_validator('final_decision', mode='before')
    def validate_decision(cls, v):
        """Validate the final decision."""
        if not isinstance(v, str) or v.upper() not in ENUM_DECISION:
            logger.warning(f"Invalid decision value: {v}, defaulting to NO")
            return "NO"
        return v.upper()
    
    @field_validator('coverage_depth', mode='before')
    def validate_coverage(cls, v):
        """Validate the coverage depth."""
        if not isinstance(v, str) or v.upper() not in ENUM_COVERAGE:
            logger.warning(f"Invalid coverage depth value: {v}, defaulting to FLASH")
            return "FLASH"
        return v.upper()

    @field_validator('additional_research', mode='before')
    def validate_research(cls, v):
        """Validate the additional research list."""
        if isinstance(v, str):
            logger.warning(f"Invalid single value {v}, converted to list")
            return [v]
        if isinstance(v, List):
            return v
        return []
        