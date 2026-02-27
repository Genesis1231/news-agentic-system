from config import logger
from pydantic import BaseModel, Field, field_validator
from typing import List


class ImageDescriptionOutput(BaseModel):
    """Output format for the image description"""
    type: str = Field(..., description="The type of the image. e.g. 'photo', 'painting', 'meme', etc.")
    description: str = Field(..., description="The description of the image.")

class ResearchPlan(BaseModel):
    """A single research plan"""
    type: str = Field(default="web_search", description="The type of the research.")
    domain_name: str = Field(default="", description="The appointed search domain name.")
    query: str = Field(..., description="The search query.")
    reason: str = Field(..., description="The reason for the search query.")

class ResearchOutput(BaseModel):
    """Output format for the research plans"""
    outlines: List[str] = Field(
        default_factory=list, 
        description="Requested research outlines."
        )
    research_plans: List[ResearchPlan] = Field(
        default_factory=list, 
        description="The research plans to be executed. Maximum 3 plans."
        )

class ResearchNoteOutput(BaseModel):
    """Output format for the research note"""
    analysis: str = Field(..., description="Concise curation analysis.")
    notes: str = Field(..., description="Comprehensive research notes.")
    

class ScriptOutput(BaseModel):
    """Output format for the news script"""
    strategy: str = Field(..., description="The content strategy before writing the script.")
    script: str = Field(..., description="The script for the news.")
    