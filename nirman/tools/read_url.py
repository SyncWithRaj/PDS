"""
NirmanAI - ReadURL Tool
========================
Fetches and reads a webpage, returning its content as clean text.
Agents use this after finding a relevant URL from search to deep-read
AWS blogs, architecture docs, or benchmark reports.
"""

import logging
from typing import Dict, Any
from nirman.tools import Tool

logger = logging.getLogger("nirman.tools.read_url")


class ReadURLTool(Tool):
    """Fetch and read a webpage, returning clean text content."""

    MAX_CONTENT_LENGTH = 3000  # chars to return to avoid context overflow

    @property
    def name(self) -> str:
        return "read_url"

    @property
    def description(self) -> str:
        return (
            "Fetch and read a webpage. Returns the page content as clean text "
            "(max 3000 chars). Use this after finding a relevant URL from search_web "
            "to deep-read an AWS blog, architecture doc, or benchmark report."
        )

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "The URL to fetch and read (e.g., 'https://aws.amazon.com/blogs/...')"
                }
            },
            "required": ["url"]
        }

    def execute(self, **kwargs) -> str:
        """Fetch URL and return cleaned text content."""
        url = kwargs.get("url", "")
        if not url:
            return "Error: No URL provided."

        try:
            import requests
            from bs4 import BeautifulSoup

            logger.info(f"📖 Reading URL: {url}")

            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }
            response = requests.get(url, headers=headers, timeout=15)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, "html.parser")

            # Remove script, style, nav, footer elements
            for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
                tag.decompose()

            # Extract text
            text = soup.get_text(separator="\n", strip=True)

            # Clean up whitespace
            lines = [line.strip() for line in text.splitlines() if line.strip()]
            clean_text = "\n".join(lines)

            # Truncate to max length
            if len(clean_text) > self.MAX_CONTENT_LENGTH:
                clean_text = clean_text[:self.MAX_CONTENT_LENGTH] + "\n\n[... content truncated ...]"

            logger.info(f"✅ Read {len(clean_text)} chars from {url}")
            return f"Content from {url}:\n\n{clean_text}"

        except ImportError:
            return "Error: requests or beautifulsoup4 not installed."
        except requests.exceptions.Timeout:
            return f"Error: Timeout reading {url} (15s limit)"
        except requests.exceptions.HTTPError as e:
            return f"Error: HTTP {e.response.status_code} from {url}"
        except Exception as e:
            logger.warning(f"Failed to read URL {url}: {e}")
            return f"Failed to read URL: {str(e)}"
