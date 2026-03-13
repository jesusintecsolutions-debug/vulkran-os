"""VULKRAN OS — Web research service via Tavily Search API."""

import logging

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

TAVILY_API = "https://api.tavily.com/search"


async def search_web(
    query: str,
    max_results: int = 5,
    search_depth: str = "advanced",
    include_answer: bool = True,
) -> dict:
    """Search the web via Tavily API.

    Returns structured results optimized for LLM consumption.
    """
    if not settings.tavily_api_key:
        logger.warning("TAVILY_API_KEY not set — search skipped for: %s", query)
        return {
            "answer": "Búsqueda web no disponible (API key no configurada).",
            "results": [],
        }

    payload = {
        "api_key": settings.tavily_api_key,
        "query": query,
        "max_results": max_results,
        "search_depth": search_depth,
        "include_answer": include_answer,
        "include_raw_content": False,
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(TAVILY_API, json=payload)
        response.raise_for_status()
        data = response.json()

    results = []
    for r in data.get("results", []):
        results.append({
            "title": r.get("title", ""),
            "url": r.get("url", ""),
            "content": r.get("content", ""),
            "score": r.get("score", 0),
        })

    return {
        "answer": data.get("answer", ""),
        "results": results,
        "query": query,
    }


async def research_company(company_name: str) -> dict:
    """Research a company for lead enrichment.

    Searches for company info, sector, size, recent news.
    """
    queries = [
        f"{company_name} empresa España sector actividad",
        f"{company_name} últimas noticias novedades",
    ]

    all_results = []
    answer_parts = []

    for q in queries:
        data = await search_web(q, max_results=3)
        all_results.extend(data.get("results", []))
        if data.get("answer"):
            answer_parts.append(data["answer"])

    return {
        "company": company_name,
        "summary": " ".join(answer_parts) if answer_parts else "Sin resultados.",
        "sources": all_results[:6],
    }


async def research_topic(topic: str, context: str | None = None) -> dict:
    """Research a topic for content creation or briefing.

    Used by the agent to gather background info before generating content.
    """
    query = topic
    if context:
        query = f"{topic} — {context}"

    data = await search_web(query, max_results=5, search_depth="advanced")
    return {
        "topic": topic,
        "summary": data.get("answer", ""),
        "sources": data.get("results", []),
    }
