from typing import List, Optional
from urllib.parse import urljoin, urlparse, parse_qs
import xml.etree.ElementTree as ET
import requests
import logging
import re

logger = logging.getLogger(__name__)

class URLProcessor:
    """Handles URL processing, validation, and sitemap parsing."""

    def __init__(self, domain: str, base_paths: List[str], headers: dict, timeout: int):
        self.domain = domain
        self.base_paths = base_paths
        self.headers = headers
        self.timeout = timeout

    def is_relevant_url(self, url: str, language: str) -> bool:
        """Check if URL is relevant based on domain, path, and language."""
        logger.debug(f"🔍 Checking URL relevance: {url}")
        
        parsed_url = urlparse(url)
        logger.debug(f"  Domain check: {parsed_url.netloc} vs {self.domain}")
        
        if parsed_url.netloc != self.domain:
            logger.debug(f"  ❌ Domain mismatch: {parsed_url.netloc} != {self.domain}")
            return False

        logger.debug(f"  Path check: {parsed_url.path} against base paths: {self.base_paths}")
        is_relevant = False
        for base_path in self.base_paths:
            if parsed_url.path.startswith(base_path):
                logger.debug(f"  ✅ Path matches base path: {base_path}")
                is_relevant = True
                break

        if not is_relevant:
            logger.debug(f"  ❌ Path doesn't match any base path")
            return False

        query_params = parse_qs(parsed_url.query)
        url_language = query_params.get('hl', [None])[0]
        logger.debug(f"  Language check: URL language={url_language}, target={language}")

        if language == 'en':
            result = url_language is None
            logger.debug(f"  English check result: {result}")
            return result

        result = url_language == language
        logger.debug(f"  Language match result: {result}")
        return result

    def find_sitemap_url(self, base_url: str) -> Optional[str]:
        """Try to find sitemap URL from robots.txt or common locations."""
        logger.info(f"🔍 Starting sitemap discovery for: {base_url}")
        
        try:
            robots_url = urljoin(base_url, '/robots.txt')
            logger.info(f"📄 Checking robots.txt at {robots_url}")
            response = requests.get(robots_url, headers=self.headers, timeout=self.timeout)
            logger.info(f"✅ robots.txt response: {response.status_code}")
            
            if response.status_code == 200:
                logger.info(f"📝 robots.txt content preview: {response.text[:200]}...")
                sitemap_match = re.search(r'Sitemap: (.*)', response.text)
                if sitemap_match:
                    sitemap_url = sitemap_match.group(1).strip()
                    logger.info(f"🎯 Found sitemap in robots.txt: {sitemap_url}")
                    return sitemap_url
                else:
                    logger.info("📄 No sitemap directive found in robots.txt")

            # Try common sitemap locations
            logger.info("🔎 Trying common sitemap locations...")
            common_paths = ['/sitemap.xml', '/sitemap_index.xml', '/sitemap/sitemap.xml']
            for path in common_paths:
                url = urljoin(base_url, path)
                logger.info(f"🌐 Trying: {url}")
                try:
                    test_response = requests.get(url, headers=self.headers, timeout=self.timeout)
                    logger.info(f"📡 Response for {url}: {test_response.status_code}")
                    if test_response.status_code == 200:
                        logger.info(f"✅ Found sitemap at: {url}")
                        return url
                except requests.RequestException as e:
                    logger.info(f"❌ Failed to access {url}: {e}")
                    continue

        except requests.RequestException as e:
            logger.error(f"💥 Error during sitemap discovery: {e}")
        
        logger.warning(f"🚫 No sitemap found for {base_url}")
        return None

    def parse_sitemap(self, sitemap_url: str) -> List[str]:
        """Parse XML sitemap and return list of URLs."""
        logger.info(f"📊 Starting sitemap parsing for: {sitemap_url}")
        
        try:
            logger.info(f"🌐 Fetching sitemap content...")
            response = requests.get(sitemap_url, headers=self.headers, timeout=self.timeout)
            logger.info(f"📡 Sitemap response: {response.status_code}, Content-Type: {response.headers.get('content-type', 'unknown')}")
            logger.info(f"📏 Content length: {len(response.content)} bytes")
            
            # Log first 500 chars to see what we're actually getting
            content_preview = response.content.decode('utf-8', errors='ignore')[:500]
            logger.info(f"📝 Content preview: {content_preview}...")
            
            logger.info(f"🔬 Attempting XML parsing...")
            root = ET.fromstring(response.content)
            logger.info(f"✅ XML parsing successful, root tag: {root.tag}")
            
            namespaces = {'ns': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
            loc_elements = root.findall('.//ns:loc', namespaces)
            logger.info(f"🔍 Found {len(loc_elements)} <loc> elements in sitemap")
            
            urls = [loc.text for loc in loc_elements if loc.text]
            logger.info(f"📋 Extracted {len(urls)} valid URLs from sitemap")
            
            # Log first few URLs for debugging
            for i, url in enumerate(urls[:5]):
                logger.info(f"  {i+1}. {url}")
            if len(urls) > 5:
                logger.info(f"  ... and {len(urls) - 5} more URLs")
            
            return urls

        except ET.ParseError as e:
            logger.error(f"❌ XML parsing error for {sitemap_url}: {e}")
            logger.error(f"🔧 This might be an HTML page instead of XML sitemap")
            return []
        except Exception as e:
            logger.error(f"💥 Unexpected error parsing sitemap {sitemap_url}: {e}")
            return []