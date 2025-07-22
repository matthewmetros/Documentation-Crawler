"""
Content Extraction Module
Smart content extraction that removes navigation, ads, and non-content elements
"""

import re
import logging
from typing import List, Optional, Dict
from urllib.parse import urljoin, urlparse

import trafilatura
from bs4 import BeautifulSoup, Comment
from markdownify import markdownify as md

from .config import Config

class ContentExtractor:
    """Intelligent content extraction for documentation sites."""
    
    def __init__(self, config: Config):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Common content selectors for different documentation frameworks
        self.content_selectors = [
            # Custom selectors from config
            *self.config.content_selectors,
            # Common documentation selectors
            'main',
            '[role="main"]',
            '.main-content',
            '.content',
            '.documentation',
            '.docs-content',
            '.article-content',
            '.post-content',
            '.entry-content',
            '.page-content',
            # Framework-specific selectors
            '.markdown-body',  # GitHub
            '.rst-content',    # Read the Docs
            '.content-wrapper', # Gitbook
            '.article',        # Docusaurus
            '.theme-doc-markdown', # Docusaurus v2
            '#main-content',   # Generic
            '.md-content',     # MkDocs
            '.document',       # Sphinx
        ]
        
        # Elements to remove (navigation, ads, etc.)
        self.removal_selectors = [
            'nav', 'header', 'footer', 'aside',
            '.nav', '.navigation', '.navbar', '.menu',
            '.sidebar', '.toc', '.breadcrumb', '.breadcrumbs',
            '.ads', '.advertisement', '.ad', '.banner',
            '.social', '.share', '.sharing',
            '.comments', '.comment',
            '.feedback', '.rating',
            '.edit-page', '.edit-link',
            '.page-nav', '.prev-next',
            '.search', '.search-box',
            '[class*="ad-"]', '[id*="ad-"]',
            'script', 'style', 'noscript',
            '.cookie', '.gdpr',
        ]
        
        # Attributes to clean
        self.clean_attributes = [
            'class', 'id', 'style', 'onclick', 'onload',
            'data-*', 'ng-*', 'v-*', 'vue-*'
        ]
    
    def extract_content(self, html: str, url: str) -> str:
        """Extract main content from HTML."""
        try:
            # First, try trafilatura for best results
            content = self._extract_with_trafilatura(html, url)
            if content and len(content.strip()) > 100:
                return content
                
            # Fallback to custom extraction
            return self._extract_with_beautifulsoup(html, url)
            
        except Exception as e:
            self.logger.error(f"Content extraction failed for {url}: {e}")
            return ""
    
    def _extract_with_trafilatura(self, html: str, url: str) -> str:
        """Extract content using trafilatura library."""
        try:
            # Configure trafilatura extraction
            config = trafilatura.settings.use_config()
            config.set('DEFAULT', 'EXTRACTION_TIMEOUT', '30')
            config.set('DEFAULT', 'MIN_OUTPUT_SIZE', '25')
            config.set('DEFAULT', 'MIN_EXTRACTED_SIZE', '25')
            
            # Extract with various options
            content = trafilatura.extract(
                html,
                url=url,
                config=config,
                output_format=self.config.output_format if self.config.output_format != 'text' else 'txt',
                target_language='en',
                include_comments=False,
                include_tables=True,
                include_images=True,
                include_links=True,
                deduplicate=True,
                favor_precision=True
            )
            
            return content if content else ""
            
        except Exception as e:
            self.logger.warning(f"Trafilatura extraction failed: {e}")
            return ""
    
    def _extract_with_beautifulsoup(self, html: str, url: str) -> str:
        """Fallback content extraction using BeautifulSoup."""
        try:
            soup = BeautifulSoup(html, 'html.parser')
            
            # Remove unwanted elements
            self._remove_unwanted_elements(soup)
            
            # Find main content
            content_element = self._find_main_content(soup)
            
            if not content_element:
                # Fallback to body content
                content_element = soup.find('body')
                if content_element:
                    # Remove remaining navigation elements
                    for nav in content_element.find_all(['nav', 'header', 'footer']):
                        nav.decompose()
            
            if not content_element:
                return ""
                
            # Clean and extract content
            self._clean_content(content_element)
            
            # Convert to desired format
            if self.config.output_format == 'html':
                return str(content_element)
            elif self.config.output_format == 'markdown':
                return self._convert_to_markdown(content_element, url)
            else:  # text format
                return content_element.get_text(separator='\n', strip=True)
                
        except Exception as e:
            self.logger.error(f"BeautifulSoup extraction failed: {e}")
            return ""
    
    def _remove_unwanted_elements(self, soup: BeautifulSoup):
        """Remove navigation, ads, and other unwanted elements."""
        # Remove comments
        for comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
            comment.extract()
            
        # Remove elements by selector
        for selector in self.removal_selectors:
            for element in soup.select(selector):
                element.decompose()
                
        # Remove elements with specific patterns in class/id
        unwanted_patterns = [
            r'nav', r'menu', r'sidebar', r'toc', r'breadcrumb',
            r'ad', r'advertisement', r'banner', r'promo',
            r'social', r'share', r'comment', r'feedback',
            r'edit', r'search', r'cookie'
        ]
        
        for element in soup.find_all():
            if element.get('class') or element.get('id'):
                element_classes = ' '.join(element.get('class', []))
                element_id = element.get('id', '')
                text_to_check = f"{element_classes} {element_id}".lower()
                
                if any(re.search(pattern, text_to_check) for pattern in unwanted_patterns):
                    element.decompose()
    
    def _find_main_content(self, soup: BeautifulSoup):
        """Find the main content element using various selectors."""
        for selector in self.content_selectors:
            elements = soup.select(selector)
            if elements:
                # Return the element with most text content
                best_element = max(elements, key=lambda el: len(el.get_text(strip=True)))
                if len(best_element.get_text(strip=True)) > 100:  # Minimum content length
                    return best_element
        return None
    
    def _clean_content(self, element):
        """Clean the content element by removing attributes and empty elements."""
        # Remove specified attributes
        for tag in element.find_all():
            attrs_to_remove = []
            for attr in tag.attrs:
                if attr in self.clean_attributes or any(attr.startswith(pattern.replace('*', '')) for pattern in self.clean_attributes if '*' in pattern):
                    attrs_to_remove.append(attr)
            
            for attr in attrs_to_remove:
                del tag.attrs[attr]
                
        # Remove empty paragraphs and divs
        for tag in element.find_all(['p', 'div', 'span']):
            if not tag.get_text(strip=True) and not tag.find(['img', 'video', 'iframe']):
                tag.decompose()
    
    def _convert_to_markdown(self, element, url: str) -> str:
        """Convert HTML element to Markdown."""
        try:
            # Configure markdownify
            markdown_content = md(
                str(element),
                heading_style='ATX',  # Use # for headings
                bullets='-',  # Use - for bullet points
                strong_tag='**',  # Use ** for bold
                em_tag='*',  # Use * for italic
                code_tag='`',  # Use ` for inline code
                convert=['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
                        'ul', 'ol', 'li', 'blockquote',
                        'strong', 'b', 'em', 'i', 'code', 'pre',
                        'a', 'img', 'table', 'thead', 'tbody', 'tr', 'td', 'th'],
                strip=['script', 'style']
            )
            
            # Clean up the markdown
            markdown_content = self._clean_markdown(markdown_content)
            
            # Fix relative URLs
            markdown_content = self._fix_relative_urls(markdown_content, url)
            
            return markdown_content
            
        except Exception as e:
            self.logger.error(f"Markdown conversion failed: {e}")
            return element.get_text(separator='\n', strip=True)
    
    def _clean_markdown(self, markdown: str) -> str:
        """Clean and normalize markdown content."""
        # Remove excessive blank lines
        markdown = re.sub(r'\n\s*\n\s*\n', '\n\n', markdown)
        
        # Fix heading spacing
        markdown = re.sub(r'\n(#{1,6})', r'\n\n\1', markdown)
        markdown = re.sub(r'(#{1,6}.*)\n([^\n#])', r'\1\n\n\2', markdown)
        
        # Fix list spacing
        markdown = re.sub(r'\n(\s*[-*+])', r'\n\n\1', markdown)
        
        # Remove trailing whitespace
        lines = [line.rstrip() for line in markdown.split('\n')]
        markdown = '\n'.join(lines)
        
        return markdown.strip()
    
    def _fix_relative_urls(self, markdown: str, base_url: str) -> str:
        """Convert relative URLs to absolute URLs in markdown."""
        try:
            # Fix markdown links: [text](relative-url)
            def replace_link(match):
                link_text = match.group(1)
                link_url = match.group(2)
                if not link_url.startswith(('http://', 'https://', 'mailto:', '#')):
                    absolute_url = urljoin(base_url, link_url)
                    return f"[{link_text}]({absolute_url})"
                return match.group(0)
            
            markdown = re.sub(r'\[([^\]]*)\]\(([^)]*)\)', replace_link, markdown)
            
            # Fix markdown images: ![alt](relative-url)
            def replace_image(match):
                alt_text = match.group(1)
                image_url = match.group(2)
                if not image_url.startswith(('http://', 'https://')):
                    absolute_url = urljoin(base_url, image_url)
                    return f"![{alt_text}]({absolute_url})"
                return match.group(0)
            
            markdown = re.sub(r'!\[([^\]]*)\]\(([^)]*)\)', replace_image, markdown)
            
            return markdown
            
        except Exception as e:
            self.logger.error(f"URL fixing failed: {e}")
            return markdown
    
    def extract_title(self, html: str) -> str:
        """Extract page title from HTML."""
        try:
            soup = BeautifulSoup(html, 'html.parser')
            
            # Try different title sources
            title_selectors = [
                'h1',
                '.title',
                '.page-title',
                '.content-title',
                '.article-title',
                '[data-title]',
                'title'
            ]
            
            for selector in title_selectors:
                element = soup.select_one(selector)
                if element:
                    title = element.get_text(strip=True)
                    if title and len(title) < 200:  # Reasonable title length
                        return title
                        
            # Fallback to URL-based title
            return "Documentation Page"
            
        except Exception as e:
            self.logger.error(f"Title extraction failed: {e}")
            return "Documentation Page"
    
    def extract_metadata(self, html: str) -> Dict[str, str]:
        """Extract metadata from HTML."""
        metadata = {}
        
        try:
            soup = BeautifulSoup(html, 'html.parser')
            
            # Extract meta tags
            for meta in soup.find_all('meta'):
                name = meta.get('name') or meta.get('property') or meta.get('http-equiv')
                content = meta.get('content')
                if name and content:
                    metadata[name.lower()] = content
            
            # Extract title
            title = soup.find('title')
            if title:
                metadata['title'] = title.get_text(strip=True)
                
            # Extract canonical URL
            canonical = soup.find('link', rel='canonical')
            if canonical:
                metadata['canonical'] = canonical.get('href')
                
        except Exception as e:
            self.logger.error(f"Metadata extraction failed: {e}")
            
        return metadata
