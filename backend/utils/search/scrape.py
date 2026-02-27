import re
from urllib.parse import urlparse
from config import logger
 
def clean_domain_name(url: str) -> str | None:
    """Extracts the hostname from a URL and removes the "www." prefix."""
 
    if not url:
        logger.warning("URL is None or empty.")
        return None
    try:
        hostname = urlparse(url).hostname
        return hostname.replace("www.", "")

    except Exception as e:
        logger.error(f"Error parsing URL: {url}. Error: {e}")
        return None
    
def clean_scraped_content(text: str) -> str:
    """
    Clean scraped web content by removing navigation, menus, and common website elements.
    Case-insensitive pattern matching for better coverage.
    
    Args:
        text (str): Raw scraped text content
        
    Returns:
        str: Cleaned text with main content only
    """
    # Common website elements to remove (using raw strings for better readability)
    patterns = [
        # Navigation elements
        r"Skip\s+to\s+(?:main\s+)?content",
        r"Search.*?",
        r"Subscribe",
        r"Sign\s+(?:in|up).*?",
        r"Menu",
        r"Navigation",
        
        # Section headers
        r"(?:Sections|subscribe|Categories|Topics)",
        
        # Region/language selectors
        r"(?:US|UK|EN|Australia)(?:\s+Edition)?",
        
        # Common footer/header items
        r"(?:Home|About|Contact|Newsletter|RSS|Pricing|Price|FAQ|Forums?)",
        
        # Browser warnings and app installation
        r"You\s+are\s+using\s+an?\s+out\s+of\s+date\s+browser",
        r"It\s+may\s+not\s+display\s+this\s+or\s+other\s+websites\s+correctly",
        r"You\s+should\s+upgrade\s+or\s+use\s+an\s+alternative\s+browser",
        r"Install\s+(?:the\s+)?app",
        
        # User metrics and engagement
        r"(?:Messages|Reaction score|Upvote)\s+\d+(?:,\d+)*",
        r"Subscriptor\+{2}",
        
        # Pagination elements
        r"(?:Go\s+to\s+page|Next|Previous|Last)",
        r"\d+\s+of\s+\d+",
        r"Sort\s+by\s+(?:date|votes)",
        
        # Social sharing and interaction elements
        r"(?:Share|Report|Quote|Add\s+bookmark)",
        r"More\s+options",
        
        # Voting patterns with positive/negative scores
        r"(?:Upvotes?|Downvotes?|Score):\s*-?\d+",

    ]
    
    # Combine patterns with word boundaries and optional whitespace/newlines
    combined_pattern = '|'.join(fr'\b{pattern}\b\s*' for pattern in patterns)
    
    # Apply cleaning with case-insensitive flag
    cleaned_text = re.sub(
        combined_pattern, 
        '', 
        text, 
        flags=re.IGNORECASE | re.MULTILINE
    )
    
    # Remove excessive whitespace and normalize spacing
    cleaned_text = re.sub(r'\s+', ' ', cleaned_text)
    cleaned_text = cleaned_text.strip()
    
    return cleaned_text