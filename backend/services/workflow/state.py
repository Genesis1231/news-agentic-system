from typing import Dict, List, Any, Annotated
from typing_extensions import TypedDict
from operator import add
from enum import Enum, StrEnum
from datetime import datetime

from backend.models.data import RawNewsItem, NewsItem

class NewsStatus(StrEnum):
    """News operational status."""
    PENDING = "Pending"
    CLASSIFIED = "Classified"
    EVALUATED = "Evaluated"
    RESEARCHED = "Researched"   
    COMPOSED = "Composed"
    REVIEWED = "Reviewed"
    APPROVED = "Approved"
    REJECTED = "Rejected"
    FAILED = "Failed"
    
class NewsPriority(Enum):
    BREAKING = 1
    IMPORTANT = 2
    SCOOP = 3
    REGULAR = 4
    IRRELEVANT = 5

class NewsState(TypedDict):
    status: NewsStatus
    id: str
    raw_news: RawNewsItem  
    evaluation: Dict[str, Any]  
    output: Annotated[NewsItem, add]
    created_at: datetime  

class SubNewsState(TypedDict):
    status: NewsStatus
    depth: str
    raw_news: RawNewsItem 
    evaluation: Dict[str, Any]
    research: Dict[str, Any]
    draft: str
    review: str
    revision: Dict[str, Any]
    output: List[NewsItem]
    