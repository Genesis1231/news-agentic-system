from config import logger
from pydantic import BaseModel, Field, field_validator
from typing import List


class Review(BaseModel):
    """Schema for review results"""
                
    editorial_analysis: str = Field(
        default="",
        description="The editorial analysis of the script."
    )
        
    source_integrity: int = Field(
        default=0, ge=0, le=10,
        description="The script's source integrity score."
    )

    hook_effectiveness: int = Field(
        default=0, ge=0, le=10,
        description="The score of the hook effectiveness."
    )
    storytelling: int = Field(
        default=0, ge=0, le=10,
        description="The script's storytelling score."
    )    

    value_density: int = Field(
        default=0, ge=0, le=10,  
        description="The script's value density score."
    )
    
    engagement_potential: int = Field(
        default=0, ge=0, le=10,
        description="The script's engagement potential score."
    )
    
    revision_notes: List[str] = Field(
        default_factory=list,
        description="Revisions to the script in list format."
    )
    
    @field_validator('source_integrity', 'value_density', 'hook_effectiveness',
                     'storytelling', 'engagement_potential', mode='before')
    def validate_score(cls, v):
        if not isinstance(v, int) or v < 0 or v > 10:
            logger.warning(f"Invalid score value: {v}")
            try:
                return max(0, min(10, int(v)))
            except (ValueError, TypeError):
                return 0
        return v

    @field_validator('revision_notes', mode='before')
    def validate_list_fields(cls, v):
        if isinstance(v, str):
            return [v]
        if isinstance(v, List):
            return v
        return []

