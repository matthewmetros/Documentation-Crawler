"""
Web Crawler Module for Documentation Scraping
"""

import re
import time
import random
import logging
import requests
from urllib.parse import urljoin, urlparse, parse_qs
from urllib.robotparser import RobotFileParser
from typing import Set, List, Dict, Optional, Tuple
from dataclasses import dataclass
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

import trafilatura
from bs4 import BeautifulSoup
from tqdm import tqdm

from .content_extractor import ContentExtractor
from .output_manager import OutputManager
from .config import Config
from .utils import normalize_url, is_same_domain, get_domain

@dataclass
class CrawlResult:
    """Result of a crawling operation."""
    url: str
    title: str
    content: str
    links: List[str]
    status_code: int
    error: Optional[str] = None

class DocumentationCrawler:
    """Main crawler class for documentation websites."""
    
    def __init__(self, config: Config):
        self.config = config
        self.session = requests.Session()
        self.content_extractor = ContentExtractor(config)
        self.output_manager = OutputManager(config)
        self.logger = logging.getLogger(__name__)
        
        # Crawling state
        self.visited_urls: Set[str] = set()
        self.failed_urls: Set[str] = set()
        self.crawl_queue: List[Tuple[str, int]] = []  # (url, depth)
        self.robots_cache: Dict[str, RobotFileParser] = {}
        
        # Setup session
        self._setup_session()
        
    def _setup_session(self):
        """Configure the requests session."""
        headers = {
            'User-Agent': self.config.user_agent,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
        self.session.headers.update(headers)
        self.session.timeout = self.config.timeout
        
        # Configure retries
        from requests.adapters import HTTPAdapter
        from urllib3.util.retry import Retry
        
        retry_strategy = Retry(
            total=self.config.retries,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
    
    def _check_robots_txt(self, url: str) -> bool:
        """Check if URL is allowed by robots.txt."""
        try:
            domain = get_domain(url)
            if domain not in self.robots_cache:
                robots_url = f"https://{domain}/robots.txt"
                rp = RobotFileParser()
                rp.set_url(robots_url)
                try:
                    rp.read()
                    self.robots_cache[domain] = rp
                except:
                    # If robots.txt can't be read, assume crawling is allowed
                    self.robots_cache[domain] = None
                    
            robots_parser = self.robots_cache[domain]
            if robots_parser:
                return robots_parser.can_fetch(self.config.user_agent, url)
            return True
            
        except Exception as e:
            self.logger.warning(f"Error checking robots.txt for {url}: {e}")
            return True
    
    def _should_crawl_url(self, url: str, base_url: str, depth: int) -> bool:
        """Determine if a URL should be crawled."""
        # Check depth limit
        if depth > self.config.max_depth:
            return False
            
        # Check if already visited
        normalized_url = normalize_url(url)
        if normalized_url in self.visited_urls or normalized_url in self.failed_urls:
            return False
            
        # Check domain restrictions
        if not is_same_domain(url, base_url):
            return False
            
        # Check robots.txt
        if not self._check_robots_txt(url):
            self.logger.info(f"URL blocked by robots.txt: {url}")
            return False
            
        # Check include patterns
        if self.config.include_patterns:
            if not any(re.search(pattern, url, re.IGNORECASE) for pattern in self.config.include_patterns):
                return False
                
        # Check exclude patterns
        if self.config.exclude_patterns:
            if any(re.search(pattern, url, re.IGNORECASE) for pattern in self.config.exclude_patterns):
                return False
                
        return True
    
    def _extract_links(self, html_content: str, base_url: str) -> List[str]:
        """Extract all links from HTML content."""
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            links = []
            
            for link in soup.find_all('a', href=True):
                href = link['href'].strip()
                if not href or href.startswith('#'):
                    continue
                    
                # Convert relative URLs to absolute
                absolute_url = urljoin(base_url, href)
                
                # Remove fragments and query parameters for documentation
                parsed = urlparse(absolute_url)
                clean_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
                
                # Remove trailing slashes for consistency
                clean_url = clean_url.rstrip('/')
                
                if clean_url and clean_url not in links:
                    links.append(clean_url)
                    
            return links
            
        except Exception as e:
            self.logger.error(f"Error extracting links from {base_url}: {e}")
            return []
    
    def _fetch_page(self, url: str) -> CrawlResult:
        """Fetch and process a single page."""
        try:
            self.logger.info(f"Fetching: {url}")
            
            # Add delay to be polite
            if not self.config.no_delay:
                delay = random.uniform(self.config.delay, self.config.max_delay)
                time.sleep(delay)
            
            # Fetch the page
            response = self.session.get(url)
            response.raise_for_status()
            
            # Extract content using trafilatura for better text extraction
            downloaded = trafilatura.fetch_url(url)
            extracted_text = trafilatura.extract(downloaded)
            
            if not extracted_text:
                # Fallback to BeautifulSoup extraction
                extracted_text = self.content_extractor.extract_content(response.text, url)
            
            # Extract title
            soup = BeautifulSoup(response.text, 'html.parser')
            title = ""
            if soup.title:
                title = soup.title.get_text().strip()
            
            # Extract links for crawling
            links = self._extract_links(response.text, url)
            
            return CrawlResult(
                url=url,
                title=title,
                content=extracted_text or "",
                links=links,
                status_code=response.status_code
            )
            
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Request error for {url}: {e}")
            return CrawlResult(
                url=url,
                title="",
                content="",
                links=[],
                status_code=0,
                error=str(e)
            )
        except Exception as e:
            self.logger.error(f"Unexpected error for {url}: {e}")
            return CrawlResult(
                url=url,
                title="",
                content="",
                links=[],
                status_code=0,
                error=str(e)
            )
    
    def scrape_single_page(self, url: str) -> str:
        """Scrape a single page and return its content."""
        self.logger.info(f"Scraping single page: {url}")
        
        result = self._fetch_page(url)
        
        if result.error:
            raise Exception(f"Failed to scrape page: {result.error}")
            
        if not result.content:
            raise Exception("No content extracted from page")
            
        # Format content based on output format
        return self.output_manager.format_single_page(result)
    
    def crawl_documentation(self, start_url: str) -> Dict:
        """Crawl entire documentation starting from the given URL."""
        self.logger.info(f"Starting documentation crawl from: {start_url}")
        
        # Initialize crawling
        self.visited_urls.clear()
        self.failed_urls.clear()
        self.crawl_queue = [(normalize_url(start_url), 0)]
        
        crawled_pages = []
        progress_bar = tqdm(desc="Crawling pages", unit="page")
        
        try:
            while self.crawl_queue and len(crawled_pages) < self.config.max_pages:
                url, depth = self.crawl_queue.pop(0)
                
                # Skip if already processed or shouldn't be crawled
                if not self._should_crawl_url(url, start_url, depth):
                    continue
                
                # Mark as visited
                self.visited_urls.add(url)
                
                # Fetch the page
                result = self._fetch_page(url)
                progress_bar.update(1)
                progress_bar.set_description(f"Crawling: {url[:50]}...")
                
                if result.error:
                    self.failed_urls.add(url)
                    self.logger.error(f"Failed to crawl {url}: {result.error}")
                    continue
                
                if not result.content.strip():
                    self.logger.warning(f"No content extracted from {url}")
                    continue
                
                # Add successful result
                crawled_pages.append(result)
                
                # Add new links to queue
                for link in result.links:
                    if self._should_crawl_url(link, start_url, depth + 1):
                        self.crawl_queue.append((normalize_url(link), depth + 1))
                
                self.logger.info(f"Crawled {len(crawled_pages)} pages, {len(self.crawl_queue)} in queue")
                
        except KeyboardInterrupt:
            self.logger.info("Crawling interrupted by user")
        finally:
            progress_bar.close()
        
        if not crawled_pages:
            raise Exception("No pages were successfully crawled")
        
        self.logger.info(f"Crawling completed. Processed {len(crawled_pages)} pages")
        
        # Process results with output manager
        content = self.output_manager.process_crawled_pages(crawled_pages)
        
        return {
            'content': content,
            'pages_scraped': len(crawled_pages),
            'urls_processed': list(self.visited_urls),
            'failed_urls': list(self.failed_urls)
        }
    
    def crawl_with_sitemap(self, start_url: str) -> Dict:
        """Crawl documentation using sitemap if available."""
        try:
            # Try to find sitemap
            domain = get_domain(start_url)
            sitemap_urls = [
                f"https://{domain}/sitemap.xml",
                f"https://{domain}/robots.txt"  # Extract sitemap from robots.txt
            ]
            
            found_urls = []
            
            for sitemap_url in sitemap_urls:
                try:
                    response = self.session.get(sitemap_url)
                    if response.status_code == 200:
                        if 'sitemap.xml' in sitemap_url:
                            # Parse XML sitemap
                            soup = BeautifulSoup(response.text, 'xml')
                            for loc in soup.find_all('loc'):
                                url = loc.get_text().strip()
                                if url and is_same_domain(url, start_url):
                                    found_urls.append(url)
                        else:
                            # Extract sitemap URLs from robots.txt
                            for line in response.text.split('\n'):
                                if line.strip().lower().startswith('sitemap:'):
                                    sitemap_url = line.split(':', 1)[1].strip()
                                    found_urls.append(sitemap_url)
                except:
                    continue
            
            if found_urls:
                self.logger.info(f"Found {len(found_urls)} URLs in sitemap")
                # Process sitemap URLs
                return self._crawl_url_list(found_urls[:self.config.max_pages])
            else:
                # Fallback to regular crawling
                return self.crawl_documentation(start_url)
                
        except Exception as e:
            self.logger.warning(f"Sitemap crawling failed: {e}, falling back to regular crawling")
            return self.crawl_documentation(start_url)
    
    def _crawl_url_list(self, urls: List[str]) -> Dict:
        """Crawl a specific list of URLs."""
        crawled_pages = []
        progress_bar = tqdm(urls, desc="Crawling sitemap URLs")
        
        for url in progress_bar:
            progress_bar.set_description(f"Crawling: {url[:50]}...")
            
            if normalize_url(url) in self.visited_urls:
                continue
                
            result = self._fetch_page(url)
            self.visited_urls.add(normalize_url(url))
            
            if result.error:
                self.failed_urls.add(url)
                continue
                
            if result.content.strip():
                crawled_pages.append(result)
        
        progress_bar.close()
        
        if not crawled_pages:
            raise Exception("No pages were successfully crawled from sitemap")
        
        content = self.output_manager.process_crawled_pages(crawled_pages)
        
        return {
            'content': content,
            'pages_scraped': len(crawled_pages),
            'urls_processed': list(self.visited_urls),
            'failed_urls': list(self.failed_urls)
        }
