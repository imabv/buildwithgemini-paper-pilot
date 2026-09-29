"""Academic search tool querying the arXiv public API."""
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from typing import Any, Dict, List


def search_academic_literature(query: str, max_results: int = 5) -> List[Dict[str, Any]]:
    """Search arXiv for academic papers and literature on a specific topic.

    Args:
        query: The academic topic, keywords, or paper title to search for (e.g., 'retrieval augmented generation').
        max_results: Maximum number of papers to retrieve (default is 5, max 10).

    Returns:
        A list of paper dictionaries containing title, authors, published date, summary/abstract, and link.
    """
    max_results = min(max(1, max_results), 10)
    encoded_query = urllib.parse.quote(query)
    url = f"https://export.arxiv.org/api/query?search_query=all:{encoded_query}&start=0&max_results={max_results}&sortBy=relevance&sortOrder=descending"

    req = urllib.request.Request(
        url,
        headers={"User-Agent": "PaperPilot/1.0 (academic-research-tool)"}
    )

    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            xml_data = response.read()
    except Exception as e:
        return [{"error": f"Failed to fetch literature from arXiv: {str(e)}"}]

    ns = {"atom": "http://www.w3.org/2005/Atom"}
    try:
        root = ET.fromstring(xml_data)
    except Exception as e:
        return [{"error": f"Failed to parse arXiv response: {str(e)}"}]

    papers = []
    for entry in root.findall("atom:entry", ns):
        title = entry.find("atom:title", ns)
        title_text = " ".join(title.text.split()) if title is not None and title.text else "Untitled"

        summary = entry.find("atom:summary", ns)
        summary_text = " ".join(summary.text.split()) if summary is not None and summary.text else ""

        published = entry.find("atom:published", ns)
        published_year = published.text[:4] if published is not None and published.text else "Unknown"

        authors = []
        for author in entry.findall("atom:author", ns):
            name = author.find("atom:name", ns)
            if name is not None and name.text:
                authors.append(name.text)

        link_elem = entry.find("atom:id", ns)
        link = link_elem.text if link_elem is not None and link_elem.text else ""

        papers.append({
            "title": title_text,
            "authors": authors,
            "year": published_year,
            "summary": summary_text,
            "link": link
        })

    return papers
