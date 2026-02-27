import math
from datetime import datetime, timezone

def get_time_weight(minutes_since_post: float) -> float:
    """
    Enhanced time weighting focusing on first hour patterns:
    - 0-15min: Critical trending window (2.5x)
    - 15-30min: High potential window (2.0x)
    - 30-45min: Growth stability window (1.5x)
    - 45-60min: Baseline establishment (1.2x)
    - >60min: Decayed weight (0.5x)
    """
    
    if minutes_since_post <= 15:
        return 2.5
    elif minutes_since_post <= 30:
        return 2.0
    elif minutes_since_post <= 45:
        return 1.5
    elif minutes_since_post <= 60:
        return 1.2
    return max(0.5, 1.0 - (minutes_since_post - 60) / 120)
    
def potential_impact_score(
    timestamp: datetime,
    metrics_likes: int,
    metrics_comments: int,
    metrics_bookmarks: int,
    metrics_reposts: int,
    metrics_views: int
) -> float:
    """
    Data-driven viral potential score (0-100) based on measurable engagement metrics.
    
    Key components:
    1. Engagement Velocity (time-weighted interaction rate)
    2. View Acceleration (view growth pattern)
    3. Interaction Depth (quality of engagement)
    4. Early Performance Multiplier (first 3 hours critical window)
    
    Returns normalized score from 0-100
    """
    # Ensure we're using timezone-aware datetime for comparison
    current_time = datetime.now(timezone.utc)
    post_time = timestamp if timestamp.tzinfo else timestamp.replace(tzinfo=timezone.utc)
    
    minutes_since_post = max(
        1.0,
        (current_time - post_time).total_seconds() / 60.0
    )

    # Early Performance Indicators
    total_engagement = (
        metrics_likes +
        metrics_comments +
        metrics_bookmarks +
        metrics_reposts
    )
    
    weighted_engagement = (
        (1.0 * metrics_likes) +  
        (5.0 * metrics_comments) +
        (3.0 * metrics_bookmarks) +
        (5.0 * metrics_reposts)
    )
    
    # How fast the news is being engaged with   
    engagement_rate = weighted_engagement / minutes_since_post 
    
    # How fast the news is being viewed
    view_rate = max(1, metrics_views) / minutes_since_post
    
    # Engagement Quality with better protection
    high_value_ratio = min(1.0, (
        (metrics_comments * 2.0 + 
        metrics_reposts * 2.0 + 
        metrics_bookmarks) / max(1, total_engagement)
    ))

    # Normalize with controlled scaling
    norm_engagement = math.log10(1 + engagement_rate) / 2.0
    norm_views = math.log10(1 + view_rate) / 3.0

    raw_score = (
        (norm_engagement * 0.30) +
        (norm_views * 0.50) +
        (high_value_ratio * 0.20) 
    ) * get_time_weight(minutes_since_post)

    # Restore score normalization
    return min(100, raw_score * 40)
