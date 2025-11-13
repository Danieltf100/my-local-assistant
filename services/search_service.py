"""
Web search service using DuckDuckGo API.

This module provides web search functionality using the DuckDuckGo Instant Answer API.
"""

import logging
import httpx
from typing import Dict, Any

logger = logging.getLogger(__name__)


async def search_web(query: str, max_results: int = 5) -> Dict[str, Any]:
    """
    Search the web using DuckDuckGo Instant Answer API.
    
    The API provides instant answers, abstracts, and related topics for search queries.
    Returns structured information including abstracts from Wikipedia, official websites,
    and related topics.
    
    Args:
        query: The search query string
        max_results: Maximum number of related topics to return (default: 5)
        
    Returns:
        Dictionary containing search results with abstract, related topics, and sources
    """
    try:
        logger.info(f"Searching web for: {query}")
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://api.duckduckgo.com/",
                params={
                    "q": query,
                    "format": "json",
                    "no_html": 1,
                    "skip_disambig": 1
                },
                timeout=10.0,
                headers={"User-Agent": "GraniteChat/1.0"}
            )
            
            if response.status_code != 200:
                logger.error(f"DuckDuckGo API error: {response.status_code}")
                return {
                    "error": f"Search API returned status {response.status_code}",
                    "query": query
                }
            
            # Check if response has content
            response_text = response.text.strip()
            if not response_text:
                logger.warning(f"DuckDuckGo API returned empty response for: {query}")
                return {
                    "query": query,
                    "abstract": "",
                    "summary": f"No instant answer available for '{query}'. The search API returned an empty response. This query may require a more specific search or the information may not be available in the instant answer database."
                }
            
            try:
                data = response.json()
            except Exception as json_error:
                logger.error(f"Failed to parse JSON response: {json_error}")
                return {
                    "query": query,
                    "error": "Failed to parse search results",
                    "summary": f"Unable to retrieve search results for '{query}'. Please try rephrasing your query."
                }
            
            logger.info(f"DuckDuckGo API response received for query: {query}")
            
            # Extract relevant information
            result = {
                "query": query,
                "abstract": data.get("Abstract", ""),
                "abstract_source": data.get("AbstractSource", ""),
                "abstract_url": data.get("AbstractURL", ""),
                "answer": data.get("Answer", ""),
                "heading": data.get("Heading", ""),
                "entity": data.get("Entity", ""),
                "related_topics": [],
                "results": []
            }
            
            # Add image if available
            if data.get("Image"):
                result["image_url"] = f"https://duckduckgo.com{data['Image']}"
            
            # Add official website if available
            if data.get("OfficialWebsite"):
                result["official_website"] = data["OfficialWebsite"]
            
            # Extract related topics (limit to max_results)
            related_topics = data.get("RelatedTopics", [])
            for topic in related_topics[:max_results]:
                if isinstance(topic, dict) and "Text" in topic:
                    result["related_topics"].append({
                        "text": topic.get("Text", ""),
                        "url": topic.get("FirstURL", "")
                    })
            
            # Extract instant answer results
            results = data.get("Results", [])
            for res in results[:max_results]:
                if isinstance(res, dict):
                    result["results"].append({
                        "text": res.get("Text", ""),
                        "url": res.get("FirstURL", "")
                    })
            
            # Create a summary description
            if result["abstract"]:
                summary = f"Search results for '{query}':\n\n"
                summary += f"{result['abstract']}\n\n"
                if result["abstract_source"]:
                    summary += f"Source: {result['abstract_source']}"
                    if result["abstract_url"]:
                        summary += f" ({result['abstract_url']})"
                    summary += "\n\n"
                
                if result.get("official_website"):
                    summary += f"Official Website: {result['official_website']}\n\n"
                
                if result["related_topics"]:
                    summary += "Related Topics:\n"
                    for i, topic in enumerate(result["related_topics"], 1):
                        summary += f"{i}. {topic['text']}\n"
                
                result["summary"] = summary
            elif result["answer"]:
                result["summary"] = f"Answer for '{query}': {result['answer']}"
            else:
                result["summary"] = f"No detailed information found for '{query}'. Try rephrasing your search query."
            
            return result
            
    except httpx.TimeoutException:
        logger.error(f"DuckDuckGo API timeout for query: {query}")
        return {"error": "Search API request timed out", "query": query}
    except Exception as e:
        logger.error(f"Error searching web with DuckDuckGo: {str(e)}", exc_info=True)
        return {"error": str(e), "query": query}

# Made with Bob
