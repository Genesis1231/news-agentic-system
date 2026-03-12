from config import logger
from pydantic import BaseModel, Field, field_validator
from typing import List, Literal, Optional

ENUM_NEWS_CATEGORY = Literal[
    "AI", "ROBOTICS", "QUANTUM", "SPACE", "BIOTECH", "BLOCKCHAIN", 
    "HARDWARE", "SOFTWARE", "SECURITY", "STARTUP", "INVESTMENT", "BUSINESS", 
    "EDUCATION", "POLICY", "COMMUNITY", "OTHER"
]

ENUM_NEWS_TYPE = Literal[
    "ANNOUNCEMENT",    # Official statements, releases
    "RESEARCH",        # Research papers, technical reports
    "ANALYSIS",        # Insights, analysis
    "OPINION",         # Opinions, editorials
    "INTERVIEW",       # Interviews, Q&As
    "EVENT",           # Events, conferences, workshops
    "DISCUSSION",      # Discussions, debates
    "PERSONAL",        # Personal opinions, blogs, diaries
    "HUMOR",           # Humor, satire
    "OTHER"
]

ENUM_GEOLOCATION = Literal["CHINA", "APAC", "EUROPE", "US", "AFRICA", "MIDEAST", "LATIN_AMERICA", "RUSSIA", "GLOBAL"]
ENUM_SOURCE_LEVEL = Literal["PRIMARY", "SECONDARY", "TERTIARY"]
ENUM_SENTIMENT = Literal["POSITIVE", "NEGATIVE", "NEUTRAL"]

class Classification(BaseModel):
    """Output format for the classification"""
    
    headline: str = Field(..., description="The headline of the story.")
    
    analysis: str = Field(..., description="The analysis for the content classification.")

    news_category: List[ENUM_NEWS_CATEGORY] = Field(
        default_factory=lambda: ["OTHER"],
        description="The category of the news",
        min_length=1
    )
    
    news_type: List[ENUM_NEWS_TYPE] = Field(
        default_factory=lambda: ["OTHER"],
        description="The type of the news",
        min_length=1
    )
    
    relevance: float = Field(
        ...,
        ge=0, 
        le=1, 
        description="Relevance score to the target audience, from 0 to 1"
    )
        
    source_level: ENUM_SOURCE_LEVEL | None = Field(
        None,
        description="The source level of the content", 
    )
    
    sentiment: ENUM_SENTIMENT | None = Field(
        None,
        description="The sentiment of the content", 
    )
    
    entities: List[str] = Field(..., description="The entities mentioned in the content")  
    
    
    @field_validator('news_category', 'geolocation', 'entities', mode='before')
    def ensure_list(cls, v):
        if isinstance(v, str):
            logger.warning(f"Invalid single value {v}, converted to list")
            return [v]
        
        return v
    
    @field_validator('relevance', mode='before')
    def ensure_float(cls, v):
        if not isinstance(v, float):
            logger.warning(f"Invalid relevance value, converted to float")
            try:
                return float(v)
            except (ValueError, TypeError):
                logger.error(f"Invalid relevance value {v}, returning 0")
                return 0
            
        return max(0, min(1, v))
        
    @field_validator('sentiment', mode='before')
    def validate_priority(cls, v):
        if not isinstance(v, str) or v not in ENUM_SENTIMENT:
            logger.warning(f"Invalid sentiment value: {v}, defaulting to NEUTRAL")
            return "NEUTRAL"
        return v
    
    @field_validator('source_level', mode='before')
    def validate_source_level(cls, v):
        if not isinstance(v, str) or v not in ENUM_SOURCE_LEVEL:
            logger.warning(f"Invalid source level value: {v}, defaulting to TERTIARY")
            return "TERTIARY"
        return v
