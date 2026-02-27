from enum import Enum

class AuthorType(str, Enum):
    TECH_LEADER = "tech_leader"
    POLI_LEADER = "poli_leader"
    FOUNDER = "founder"
    INFLUENCER = "influencer"
    RESEARCHER = "researcher"
    INVESTOR = "investor"
    COMPANY = "company"
    ORGANIZATION = "organization"
    MEDIA = "media"
    JOURNALIST = "journalist"
    GOVERNMENT = "government"
    DIPLOMAT = "diplomat"
    POLITICIAN = "politician"
    ACADEMIC = "academic"
    SCHOLAR = "scholar"
    OTHER = "other"

class NewsDepth(str, Enum):
    FLASH = "FLASH"
    BRIEF = "BRIEF"
    SCOOP = "SCOOP"
    ANALYSIS = "ANALYSIS"
    DEEP_DIVE = "DEEP_DIVE"

