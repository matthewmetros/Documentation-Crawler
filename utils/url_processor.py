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

        # Enhanced language detection for path-based routing
        if language == 'en':
            # For English, accept both no language parameter and explicit en
            if url_language is None:
                # Check for path-based language routing
                if f'/{language}/' in parsed_url.path or parsed_url.path.startswith(f'/{language}'):
                    logger.debug(f"  ✅ English path-based routing detected")
                    return True
                elif any(lang in parsed_url.path for lang in ['/fr/', '/de/', '/es/', '/pt/', '/ja/', '/ko/', '/zh/']):
                    logger.debug(f"  ❌ Non-English path-based routing detected")
                    return False
                else:
                    logger.debug(f"  ✅ Default English (no language indicator)")
                    return True
            else:
                result = url_language == 'en'
                logger.debug(f"  English query parameter result: {result}")
                return result

        # For non-English languages, check both query params and path
        if url_language == language:
            logger.debug(f"  ✅ Query parameter language match")
            return True
        elif f'/{language}/' in parsed_url.path or parsed_url.path.startswith(f'/{language}'):
            logger.debug(f"  ✅ Path-based language match")
            return True
        
        logger.debug(f"  ❌ No language match found")
        return False

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
        
        logger.warning(f"🚫 No XML sitemap found for {base_url}")
        logger.info(f"🔄 Falling back to HTML discovery method")
        return base_url  # Return base URL for HTML parsing

    def parse_sitemap(self, sitemap_url: str) -> List[str]:
        """Parse XML sitemap or HTML page and return list of URLs."""
        logger.info(f"📊 Starting sitemap parsing for: {sitemap_url}")
        
        # Check if this is HTML fallback (base URL) or XML sitemap
        if sitemap_url.endswith('.xml'):
            return self._parse_xml_sitemap(sitemap_url)
        else:
            logger.info(f"🔄 Using HTML discovery method for: {sitemap_url}")
            return self.parse_html_sitemap(sitemap_url)
    
    def _parse_xml_sitemap(self, sitemap_url: str) -> List[str]:
        """Parse XML sitemap and return list of URLs."""
        try:
            logger.info(f"🌐 Fetching XML sitemap content...")
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
            logger.info(f"📋 Extracted {len(urls)} valid URLs from XML sitemap")
            
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
            logger.error(f"💥 Unexpected error parsing XML sitemap {sitemap_url}: {e}")
            return []

    def parse_html_sitemap(self, html_url: str) -> List[str]:
        """Parse HTML page to extract documentation links as fallback."""
        logger.info(f"🌐 TRACE: parse_html_sitemap() - Entry point")
        logger.info(f"🌐 Starting HTML discovery for: {html_url}")
        logger.warning(f"🌐 TRACE: CRITICAL DEPTH ISSUE - Only processing single level!")
        logger.warning(f"🌐 TRACE: This method will NOT follow discovered links recursively!")
        
        try:
            logger.info(f"📄 Fetching HTML content...")
            response = requests.get(html_url, headers=self.headers, timeout=self.timeout)
            logger.info(f"📡 HTML response: {response.status_code}, Content-Type: {response.headers.get('content-type', 'unknown')}")
            
            if response.status_code != 200:
                logger.error(f"❌ Failed to fetch HTML: {response.status_code}")
                return []
            
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(response.content, 'html.parser')
            logger.info(f"✅ HTML parsing successful")
            
            # Extract all links from the page
            links = soup.find_all('a', href=True)
            logger.info(f"🔍 Found {len(links)} total links in HTML")
            
            # Filter for relevant documentation links
            doc_urls = []
            for link in links:
                href = link.get('href')
                if href:
                    # Convert relative URLs to absolute
                    from urllib.parse import urljoin
                    absolute_url = urljoin(html_url, href)
                    
                    # Basic filtering for documentation-like URLs
                    if self.is_documentation_link(absolute_url, html_url):
                        doc_urls.append(absolute_url)
            
            # Remove duplicates
            unique_urls = list(set(doc_urls))
            logger.info(f"📋 Extracted {len(unique_urls)} unique documentation URLs")
            
            logger.warning(f"📋 TRACE: DEPTH LIMITATION - These are only FIRST-LEVEL URLs!")
            logger.warning(f"📋 TRACE: No recursive discovery will be performed on these URLs!")
            logger.warning(f"📋 TRACE: Missing potentially hundreds of deeper documentation pages!")
            
            # Log first few URLs for debugging
            for i, url in enumerate(unique_urls[:5]):
                logger.info(f"  {i+1}. {url}")
            if len(unique_urls) > 5:
                logger.info(f"  ... and {len(unique_urls) - 5} more URLs")
            
            logger.info(f"📋 TRACE: parse_html_sitemap() - Returning {len(unique_urls)} URLs (single level only)")
            return unique_urls
            
        except Exception as e:
            logger.error(f"💥 Error parsing HTML sitemap {html_url}: {e}")
            return []
    
    def is_documentation_link(self, url: str, base_url: str) -> bool:
        """Check if a link appears to be documentation content."""
        from urllib.parse import urlparse
        
        parsed_url = urlparse(url)
        parsed_base = urlparse(base_url)
        
        # Must be same domain
        if parsed_url.netloc != parsed_base.netloc:
            return False
        
        # Skip common non-documentation patterns
        skip_patterns = [
            '/login', '/signup', '/register', '/auth',
            '/api/', '/admin/', '/account/', '/profile/',
            'mailto:', 'tel:', 'javascript:',
            '.pdf', '.doc', '.zip', '.img', '.png', '.jpg', '.gif',
            '#', '?search=', '/search'
        ]
        
        url_lower = url.lower()
        for pattern in skip_patterns:
            if pattern in url_lower:
                return False
        
        # Look for documentation indicators
        doc_indicators = [
            '/article', '/articles', '/docs', '/help', '/guide', '/guides',
            '/documentation', '/tutorial', '/tutorials', '/kb', '/knowledge',
            '/support', '/faq', '/how-to', '/getting-started'
        ]
        
        for indicator in doc_indicators:
            if indicator in url_lower:
                return True
        
        # For Intercom-style help centers, check for article patterns
        if '/en/' in url and any(x in url_lower for x in ['article', 'collection']):
            return True
        
        # If path starts with base path and has content depth
        path_parts = parsed_url.path.strip('/').split('/')
        if len(path_parts) >= 2:  # Has some content depth
            for base_path in self.base_paths:
                if parsed_url.path.startswith(base_path.rstrip('/')):
                    return True
        
        return False