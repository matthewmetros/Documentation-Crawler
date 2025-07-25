import os
import concurrent.futures
import logging
import shutil
from bs4 import BeautifulSoup
from pathlib import Path
from typing import List, Tuple, Dict, Optional
from urllib.parse import urlparse
from threading import Lock
from xml.etree import ElementTree as ET
import requests
import time
import hashlib
import json

from utils.config import CrawlerConfig
from utils.display import UnifiedDisplay
from utils.url_processor import URLProcessor
from converters.html_to_md import HTMLToMarkdownConverter

logger = logging.getLogger(__name__)

class DocCrawler:
    """Main crawler class that orchestrates the documentation crawling process."""

    def __init__(self, config: CrawlerConfig, base_urls: List[str]):

        # Check if base URLs are from the same domain
        first_parsed_url = urlparse(base_urls[0])
        first_domain = first_parsed_url.netloc

        for url in base_urls:
            parsed_url = urlparse(url)
            if parsed_url.netloc != first_domain:
                raise ValueError(f"Base URLs must be from the same domain: {first_domain} != {parsed_url.netloc}")

        self.config = config
        self.base_urls = base_urls
        self.domain = first_domain

        # Initialize display
        self.display = UnifiedDisplay(debug=config.debug)

        # Extract base paths for filtering
        self.base_paths = []
        for url in base_urls:
          parsed_url = urlparse(url)
          path_parts = parsed_url.path.rstrip('/').split('/')
          if path_parts and path_parts[-1] in ['overview', 'introduction', 'docs']:
              path_parts.pop()
          self.base_paths.append('/'.join(path_parts))

        # Initialize components
        self.url_processor = URLProcessor(
            domain=self.domain,
            base_paths=self.base_paths,
            headers={'User-Agent': config.user_agent},
            timeout=config.timeout
        )

        self.converter = HTMLToMarkdownConverter()

        # State management
        self.visited_urls = set()
        self.sitemap = {}
        self.sitemap_lock = Lock()
        self.state_file = Path("crawler_state.json") # Path for storing crawler state
        self.page_states = self.load_state() # Load previous states if any.

        logger.info(f"Initializing crawler for domain: {self.domain}")
        logger.info(f"Base paths filter: {self.base_paths}")
        logger.info(f"Language filter: {config.language}")

    def make_request(self, url: str, method: str = 'get') -> requests.Response:
        """Make HTTP request with retry logic."""
        headers = {'User-Agent': self.config.user_agent}

        for attempt in range(self.config.max_retries):
            try:
                if method == 'get':
                    response = requests.get(
                        url,
                        headers=headers,
                        timeout=self.config.timeout
                    )
                response.raise_for_status()
                return response
            except requests.RequestException as e:
                if attempt + 1 < self.config.max_retries:
                    time.sleep(self.config.retry_delay * (attempt + 1))
                else:
                    raise

    def process_sitemap_url(self, url: str) -> List[Tuple[str, str]]:
        """Process a single sitemap URL."""
        logger.debug(f"🔄 Processing sitemap URL: {url}")
        
        try:
            if url.endswith('.xml'):
                logger.debug(f"📄 Processing as XML sitemap: {url}")
                response = self.make_request(url)
                root = ET.fromstring(response.content)
                namespaces = {'ns': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
                urls = root.findall('.//ns:loc', namespaces)
                logger.debug(f"🔍 Found {len(urls)} URLs in XML sitemap")

                results = []
                for i, loc in enumerate(urls):
                    page_url = loc.text
                    logger.debug(f"  {i+1}. Checking URL: {page_url}")
                    
                    self.display.update_stats(
                        processed=1,
                        current_url=page_url
                    )

                    if not page_url.endswith('.xml'):
                        is_relevant = self.url_processor.is_relevant_url(page_url, self.config.language)
                        logger.debug(f"    Relevance check: {is_relevant}")
                        
                        if is_relevant:
                            self.display.update_stats(relevant=1)
                            title = self.get_page_title(page_url)
                            results.append((page_url, title))
                            logger.debug(f"    ✅ Added to results: {title}")
                        else:
                            logger.debug(f"    ❌ Filtered out (not relevant)")
                    else:
                        logger.debug(f"    ⏭️ Skipped (XML file)")

                logger.debug(f"📊 XML processing complete: {len(results)} relevant URLs found")
                return results

            else:
                logger.debug(f"📄 Processing as regular URL: {url}")
                if self.url_processor.is_relevant_url(url, self.config.language):
                    logger.debug(f"✅ URL is relevant, adding to results")
                    self.display.update_stats(
                        processed=1,
                        relevant=1,
                        current_url=url
                    )
                    title = self.get_page_title(url)
                    return [(url, title)]
                else:
                    logger.debug(f"❌ URL not relevant, skipping")
                    self.display.update_stats(processed=1)
                    return []

        except Exception as e:
            self.display.update_stats(errors=1)
            logger.error(f"💥 Error processing URL {url}: {e}")
            import traceback
            logger.error(f"🔍 Full traceback: {traceback.format_exc()}")
            return []

    def get_page_title(self, url: str) -> str:
        """Extract and clean page title from URL."""
        try:
            response = self.make_request(url)
            soup = BeautifulSoup(response.text, 'html.parser')
            title = soup.title.string if soup.title else url
            return self.converter.clean_title(title, url)
        except Exception as e:
            logger.debug(f"Could not get title for {url}: {e}")
            return url

    def process_sitemap_chunk(self, urls: List[str]) -> List[Tuple[str, str]]:
        """Process a chunk of sitemap URLs."""
        results = []
        for url in urls:
            try:
                chunk_results = self.process_sitemap_url(url)
                results.extend(chunk_results)
            except Exception as e:
                self.display.update_stats(errors=1)
                logger.error(f"Error processing URL chunk: {e}")
        return results

    def parallel_sitemap_processing(self, sitemap_urls: List[str]) -> None:
        """Process sitemap URLs in parallel with unified display."""
        url_chunks = [
            sitemap_urls[i:i + self.config.chunk_size]
            for i in range(0, len(sitemap_urls), self.config.chunk_size)
        ]

        with concurrent.futures.ThreadPoolExecutor(max_workers=self.config.max_workers) as executor:
            future_to_chunk = {
                executor.submit(self.process_sitemap_chunk, chunk): chunk
                for chunk in url_chunks
            }

            with self.display.create_progress_bar(len(sitemap_urls)) as pbar:
                for future in concurrent.futures.as_completed(future_to_chunk):
                    try:
                        results = future.result()
                        with self.sitemap_lock:
                            for url, title in results:
                                self.sitemap[url] = title
                        pbar.update(len(future_to_chunk[future]))

                    except Exception as e:
                        self.display.update_stats(errors=1)
                        logger.error(f"Error processing chunk: {e}")

    def parse_sitemap(self, base_urls: List[str]) -> None:
        """Parse XML sitemap and collect URLs."""
        logger.info(f"🚀 Starting sitemap parsing for base URLs: {base_urls}")
        
        base_url = base_urls[0]  # use first url as the base
        logger.info(f"🎯 Using base URL for discovery: {base_url}")
        
        sitemap_url = self.url_processor.find_sitemap_url(base_url)
        if not sitemap_url:
            logger.error("❌ No sitemap found! Cannot proceed with crawling.")
            logger.error(f"🔧 Consider trying a different URL or checking if {base_url} has documentation")
            return
        
        # Detect discovery method being used
        if sitemap_url.endswith('.xml'):
            logger.info(f"📄 Using XML sitemap discovery method")
        else:
            logger.info(f"🌐 Using HTML discovery method (fallback)")
            logger.info(f"🔧 This is normal for modern documentation platforms like Intercom, Zendesk, etc.")

        try:
            logger.info(f"📊 Parsing main sitemap: {sitemap_url}")
            # Pass crawl depth configuration for recursive discovery
            if sitemap_url.endswith('.xml'):
                sitemap_urls = self.url_processor.parse_sitemap(sitemap_url)
            else:
                # Use recursive HTML discovery with configured depth
                max_depth = getattr(self.config, 'max_crawl_depth', 2)
                logger.info(f"🔧 Using recursive discovery with max_depth={max_depth}")
                sitemap_urls = self.url_processor.parse_html_sitemap(sitemap_url, max_depth)
            logger.info(f"📋 Found {len(sitemap_urls)} potential sitemaps/URLs")

            if len(sitemap_urls) == 0:
                logger.warning(f"⚠️ Sitemap parsing returned 0 URLs from {sitemap_url}")
                logger.warning(f"🔧 This might be due to XML parsing issues or empty sitemap")
                return

            logger.info(f"🔄 Starting parallel processing of {len(sitemap_urls)} URLs...")
            self.parallel_sitemap_processing(sitemap_urls)
            
            logger.info(f"✅ Sitemap processing complete. Found {len(self.sitemap)} relevant pages")

        except Exception as e:
            logger.error(f"💥 Error during sitemap parsing: {e}")
            import traceback
            logger.error(f"🔍 Full traceback: {traceback.format_exc()}")

    def calculate_hash(self, content: str) -> str:
        """Calculate the SHA256 hash of content."""
        return hashlib.sha256(content.encode('utf-8')).hexdigest()

    def load_state(self) -> dict:
        """Load previously stored state of crawled pages."""
        if self.state_file.exists():
            with self.state_file.open('r') as f:
                return json.load(f)
        return {}

    def save_state(self) -> None:
        """Save current state of crawled pages."""
        with self.state_file.open('w') as f:
            json.dump(self.page_states, f, indent=4)

    def _create_filepath(self, urlpath: str, store_flatten: bool, suffix: str) -> Path:
        """Create filepath based on flatten parameter."""
        path_parts = Path(urlpath).parts

        if store_flatten:
          if len(path_parts) > 1:
            filename = f"{'_'.join(path_parts[:-1])}_{path_parts[-1]}"
          else:
             filename = path_parts[-1]
        else:
           filename = Path(urlpath)

        filename = Path(filename).with_suffix(suffix)

        output_dir = Path('downloaded_docs')
        filepath = output_dir / filename

        if len(str(filepath)) > 255:
          truncated_filename = str(filename)[:200]
          filepath = output_dir / Path(f"{truncated_filename}_{hashlib.sha256(str(filepath).encode('utf-8')).hexdigest()[:5]}{suffix}")

        return filepath

    def process_page(self, url: str, store_raw_html: bool, store_markdown: bool, store_text: bool, store_flatten: bool) -> None:
        """Download, convert, and save a single page with change detection."""
        try:
            response = self.make_request(url)

            current_hash = self.calculate_hash(response.text)

            if url in self.page_states and self.page_states[url] == current_hash:
                logger.info(f"Skipping {url}: No changes detected")
                self.display.update_stats(processed=1)
                return

            urlpath = urlparse(url).path.strip('/')

            # Save markdown content if needed
            if store_markdown:
                markdown_content = self.converter.convert(response.text)
                filepath = self._create_filepath(urlpath, store_flatten, '.md')
                filepath.parent.mkdir(parents=True, exist_ok=True)
                filepath.write_text(markdown_content, encoding='utf-8')

            # Save raw HTML content if needed
            if store_raw_html:
                filepath = self._create_filepath(urlpath, store_flatten, '.html')
                filepath.parent.mkdir(parents=True, exist_ok=True)
                filepath.write_text(response.text, encoding='utf-8')

            # Save as plain text file if needed
            if store_text:
                filepath = self._create_filepath(urlpath, store_flatten, '.txt')
                filepath.parent.mkdir(parents=True, exist_ok=True)
                filepath.write_text(response.text, encoding='utf-8')

            self.page_states[url] = current_hash
            self.display.update_stats(processed=1)

        except Exception as e:
            self.display.update_stats(errors=1)
            logger.error(f"Error processing {url}: {e}")

    def process_selected_pages(self, selected_urls: List[str], store_raw_html: bool, store_markdown: bool, store_text: bool, store_flatten: bool) -> None:
        """Process selected pages in parallel with unified display and change detection."""
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.config.max_workers) as executor:
            futures = {
                executor.submit(self.process_page, url, store_raw_html, store_markdown, store_text, store_flatten): url
                for url in selected_urls
            }

            with self.display.create_progress_bar(len(selected_urls), desc="Processing pages") as pbar:
                for future in concurrent.futures.as_completed(futures):
                    try:
                        future.result()
                        pbar.update(1)
                    except Exception as e:
                        self.display.update_stats(errors=1)
                        logger.error(f"Error processing page: {e}")

        self.save_state()

    def store_urls(self, selected_urls: List[str]) -> None:
        """Store selected URLs to a file."""
        output_dir = Path('selected_urls')
        output_dir.mkdir(exist_ok=True)
        
        timestamp = int(time.time())
        filepath = output_dir / f"selected_urls_{timestamp}.txt"
        
        with filepath.open('w', encoding='utf-8') as f:
            for url in selected_urls:
                f.write(f"{url}\n")
        
        logger.info(f"Stored {len(selected_urls)} URLs to {filepath}")

    def get_scraped_content(self, selected_urls: List[str], formats: dict = None) -> Dict[str, dict]:
        """Scrape and return content for web interface in requested formats."""
        if formats is None:
            formats = {'store_markdown': True, 'store_raw_html': False, 'store_text': False}
            
        logger.info(f"🔧 TRACE: get_scraped_content() - Processing {len(selected_urls)} URLs with formats: {formats}")
        content = {}
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.config.max_workers) as executor:
            futures = {
                executor.submit(self._scrape_single_page, url, formats): url
                for url in selected_urls
            }

            for future in concurrent.futures.as_completed(futures):
                try:
                    url = futures[future]
                    page_content = future.result()
                    if page_content:
                        content[url] = page_content
                        logger.debug(f"✅ Successfully processed {url} in {len(page_content)} formats")
                except Exception as e:
                    logger.error(f"Error scraping page: {e}")

        logger.info(f"🔧 TRACE: get_scraped_content() - Completed {len(content)} pages successfully")
        return content

    def _scrape_single_page(self, url: str, formats: dict = None) -> dict:
        """Scrape a single page and return content in requested formats."""
        logger.info(f"🔧 TRACE: _scrape_single_page() - Entry point for {url}")
        
        if formats is None:
            formats = {'store_markdown': True, 'store_raw_html': False, 'store_text': False}
        
        logger.info(f"🔧 TRACE: NEW FEATURE - Multi-format processing enabled!")
        logger.info(f"🔧 TRACE: Requested formats: {[k for k, v in formats.items() if v]}")
        
        try:
            response = self.make_request(url)
            logger.info(f"🔧 TRACE: HTTP response received ({len(response.text)} chars)")
            
            result = {}
            
            # Generate Markdown content if requested
            if formats.get('store_markdown', True):
                markdown_content = self.converter.convert(response.text)
                result['markdown'] = markdown_content
                logger.info(f"🔧 TRACE: Generated Markdown content ({len(markdown_content)} chars)")
            
            # Store raw HTML content if requested
            if formats.get('store_raw_html', False):
                # Extract main content from HTML
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Try to find main content area
                main_content = soup.find('main') or soup.find('article') or soup.find('div', class_=['content', 'main-content'])
                if main_content:
                    html_content = str(main_content)
                else:
                    html_content = response.text
                    
                result['html'] = html_content
                logger.info(f"🔧 TRACE: Generated HTML content ({len(html_content)} chars)")
            
            # Generate plain text content if requested
            if formats.get('store_text', False):
                import trafilatura
                text_content = trafilatura.extract(response.text)
                if text_content:
                    result['text'] = text_content
                    logger.info(f"🔧 TRACE: Generated plain text content ({len(text_content)} chars)")
                else:
                    # Fallback to basic text extraction
                    from bs4 import BeautifulSoup
                    soup = BeautifulSoup(response.text, 'html.parser')
                    text_content = soup.get_text(separator=' ', strip=True)
                    result['text'] = text_content
                    logger.info(f"🔧 TRACE: Generated fallback text content ({len(text_content)} chars)")
            
            logger.info(f"🔧 TRACE: Multi-format processing complete: {len(result)} formats generated")
            return result
            
        except Exception as e:
            logger.error(f"Error scraping {url}: {e}")
            return {}