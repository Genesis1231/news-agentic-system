from config import logger
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage
from langchain_perplexity import ChatPerplexity

from backend.utils.search.whitelist import (
    POLICY_MEDIA, NEWS_MEDIA, TECH_MEDIA, RESEARCH_MEDIA
)

# Shared Perplexity client
_perplexity = ChatPerplexity(model="sonar-pro", temperature=0.1, timeout=30)

SOCIAL_MEDIA = ["reddit.com", "news.ycombinator.com", "x.com", "threads.net"]


PERPLEXITY_MAX_DOMAINS = 20


async def _search_perplexity(query: str, domains: list[str]) -> str:
    """Search Perplexity with domain filter and return synthesized text."""
    try:
        response = await _perplexity.ainvoke(
            [HumanMessage(content=query)],
            extra_body={
                "search_domain_filter": [d.lower() for d in domains[:PERPLEXITY_MAX_DOMAINS]],
                "search_recency_filter": "month",
            },
        )
        return response.content
    except Exception as e:
        logger.error(f"Perplexity search failed for '{query}': {e}")
        return f"Search failed: {e}"


@tool
async def search_official(query: str, domain: str) -> str:
    """Search a specific organization's official website for primary source information.
    Use for official announcements, documentation, blog posts, or press releases
    from a specific company or organization.

    Args:
        query: The search query.
        domain: The official domain to search (e.g., 'openai.com', 'ai.meta.com').
    """
    return await _search_perplexity(query, [domain])


@tool
async def search_academic(query: str) -> str:
    """Search academic and research sources (arXiv, Nature, IEEE, ACM, university sites).
    Use for research papers, scientific findings, technical benchmarks, and academic analysis.

    Args:
        query: The search query.
    """
    return await _search_perplexity(query, RESEARCH_MEDIA)


@tool
async def search_tech_media(query: str) -> str:
    """Search technology news outlets (TechCrunch, The Verge, Wired, Ars Technica, etc.).
    Use for tech industry reporting, product reviews, startup coverage, and market analysis.

    Args:
        query: The search query.
    """
    return await _search_perplexity(query, TECH_MEDIA)


@tool
async def search_broad_media(query: str) -> str:
    """Search major global news outlets (Reuters, Bloomberg, BBC, NYT, etc.).
    Use for mainstream news coverage, financial analysis, geopolitical context, and societal impact.

    Args:
        query: The search query.
    """
    return await _search_perplexity(query, NEWS_MEDIA)


@tool
async def search_social(query: str) -> str:
    """Search social platforms and forums (Reddit, Hacker News, X/Twitter, Threads).
    Use for community reactions, expert commentary, public sentiment, and emerging narratives.

    Args:
        query: The search query.
    """
    return await _search_perplexity(query, SOCIAL_MEDIA)


@tool
async def search_policy(query: str) -> str:
    """Search government and policy sources (gov sites, EU, OECD, UN, FCC, etc.).
    Use for regulatory decisions, policy documents, legal frameworks, and government statements.

    Args:
        query: The search query.
    """
    return await _search_perplexity(query, POLICY_MEDIA)


ALL_RESEARCH_TOOLS = [
    search_official,
    search_academic,
    search_tech_media,
    search_broad_media,
    search_social,
    search_policy,
]
