"""
Output Management Module
Handles formatting and saving of scraped content in various formats
"""

import os
import json
import logging
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime
from urllib.parse import urlparse

from .config import Config
from .utils import sanitize_filename, create_table_of_contents

class OutputManager:
    """Manages output formatting and file operations."""
    
    def __init__(self, config: Config):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
    def format_single_page(self, result) -> str:
        """Format a single page result based on output format."""
        content = ""
        
        if self.config.output_format == 'markdown':
            content = self._format_markdown_page(result)
        elif self.config.output_format == 'html':
            content = self._format_html_page(result)
        else:  # text format
            content = self._format_text_page(result)
            
        return content
    
    def process_crawled_pages(self, crawled_pages: List) -> str:
        """Process multiple crawled pages based on organization method."""
        if not crawled_pages:
            return ""
            
        if self.config.organization == 'single':
            return self._create_single_file(crawled_pages)
        elif self.config.organization == 'chapters':
            return self._create_chapters(crawled_pages)
        elif self.config.organization == 'pages':
            return self._create_pages(crawled_pages)
        else:
            return self._create_single_file(crawled_pages)
    
    def _format_markdown_page(self, result) -> str:
        """Format a single page as Markdown."""
        content = []
        
        # Add title
        if result.title:
            content.append(f"# {result.title}")
            content.append("")
        
        # Add URL reference
        content.append(f"*Source: {result.url}*")
        content.append("")
        content.append("---")
        content.append("")
        
        # Add main content
        if result.content:
            content.append(result.content)
        else:
            content.append("*No content extracted*")
            
        return "\n".join(content)
    
    def _format_html_page(self, result) -> str:
        """Format a single page as HTML."""
        html_template = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; 
               line-height: 1.6; max-width: 800px; margin: 0 auto; padding: 20px; }}
        .source {{ color: #666; font-style: italic; margin-bottom: 20px; }}
        h1, h2, h3, h4, h5, h6 {{ color: #333; margin-top: 30px; }}
        code {{ background: #f4f4f4; padding: 2px 4px; border-radius: 3px; }}
        pre {{ background: #f4f4f4; padding: 15px; border-radius: 5px; overflow-x: auto; }}
        blockquote {{ border-left: 4px solid #ddd; margin: 0; padding-left: 20px; }}
    </style>
</head>
<body>
    <h1>{title}</h1>
    <div class="source">Source: <a href="{url}">{url}</a></div>
    <hr>
    <div class="content">
        {content}
    </div>
</body>
</html>"""
        
        return html_template.format(
            title=result.title or "Documentation Page",
            url=result.url,
            content=result.content or "<p><em>No content extracted</em></p>"
        )
    
    def _format_text_page(self, result) -> str:
        """Format a single page as plain text."""
        content = []
        
        if result.title:
            content.append(result.title)
            content.append("=" * len(result.title))
            content.append("")
        
        content.append(f"Source: {result.url}")
        content.append("-" * 50)
        content.append("")
        
        if result.content:
            content.append(result.content)
        else:
            content.append("No content extracted")
            
        return "\n".join(content)
    
    def _create_single_file(self, crawled_pages: List) -> str:
        """Create a single consolidated file from all pages."""
        content = []
        
        # Add document header
        content.append(self._create_document_header(crawled_pages))
        content.append("")
        
        # Add table of contents if more than one page
        if len(crawled_pages) > 1:
            toc = create_table_of_contents(crawled_pages)
            content.append("## Table of Contents")
            content.append("")
            content.append(toc)
            content.append("")
            content.append("---")
            content.append("")
        
        # Add all pages
        for i, page in enumerate(crawled_pages):
            if i > 0:
                content.append("\n---\n")
            
            page_content = self.format_single_page(page)
            content.append(page_content)
        
        # Add footer
        content.append("")
        content.append("---")
        content.append(f"*Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*")
        content.append(f"*Total pages: {len(crawled_pages)}*")
        
        return "\n".join(content)
    
    def _create_chapters(self, crawled_pages: List) -> str:
        """Create organized chapters from crawled pages."""
        # Group pages by URL structure
        chapters = self._group_pages_by_structure(crawled_pages)
        
        # Create main index file content
        content = []
        content.append(self._create_document_header(crawled_pages))
        content.append("")
        content.append("## Chapters")
        content.append("")
        
        for chapter_name, pages in chapters.items():
            content.append(f"- [{chapter_name}](chapter-{sanitize_filename(chapter_name)}.{self._get_file_extension()})")
        
        content.append("")
        content.append(f"*Total chapters: {len(chapters)}*")
        content.append(f"*Total pages: {len(crawled_pages)}*")
        
        return "\n".join(content)
    
    def _create_pages(self, crawled_pages: List) -> str:
        """Create individual page files organized in directories."""
        # Group pages by directory structure
        page_structure = self._organize_pages_by_path(crawled_pages)
        
        # Create main index
        content = []
        content.append(self._create_document_header(crawled_pages))
        content.append("")
        content.append("## Documentation Structure")
        content.append("")
        
        content.append(self._create_directory_listing(page_structure))
        
        content.append("")
        content.append(f"*Total pages: {len(crawled_pages)}*")
        
        return "\n".join(content)
    
    def _create_document_header(self, crawled_pages: List) -> str:
        """Create document header with metadata."""
        if not crawled_pages:
            return "# Documentation"
        
        # Extract base domain
        first_url = crawled_pages[0].url
        domain = urlparse(first_url).netloc
        
        header = []
        header.append(f"# Documentation: {domain}")
        header.append("")
        header.append(f"**Scraped from:** {first_url}")
        header.append(f"**Generated on:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        header.append(f"**Total pages:** {len(crawled_pages)}")
        header.append(f"**Format:** {self.config.output_format}")
        
        return "\n".join(header)
    
    def _group_pages_by_structure(self, crawled_pages: List) -> Dict[str, List]:
        """Group pages into logical chapters based on URL structure."""
        chapters = {}
        
        for page in crawled_pages:
            # Extract chapter name from URL path
            parsed_url = urlparse(page.url)
            path_parts = [part for part in parsed_url.path.split('/') if part]
            
            if len(path_parts) >= 2:
                chapter_name = path_parts[1].replace('-', ' ').replace('_', ' ').title()
            elif len(path_parts) == 1:
                chapter_name = path_parts[0].replace('-', ' ').replace('_', ' ').title()
            else:
                chapter_name = "Introduction"
            
            if chapter_name not in chapters:
                chapters[chapter_name] = []
            chapters[chapter_name].append(page)
        
        return chapters
    
    def _organize_pages_by_path(self, crawled_pages: List) -> Dict:
        """Organize pages into a hierarchical directory structure."""
        structure = {}
        
        for page in crawled_pages:
            parsed_url = urlparse(page.url)
            path_parts = [part for part in parsed_url.path.split('/') if part]
            
            current_level = structure
            for i, part in enumerate(path_parts):
                if part not in current_level:
                    if i == len(path_parts) - 1:
                        # This is a file
                        current_level[part] = {
                            'type': 'file',
                            'page': page,
                            'title': page.title or part.replace('-', ' ').title()
                        }
                    else:
                        # This is a directory
                        current_level[part] = {'type': 'directory', 'children': {}}
                
                if current_level[part]['type'] == 'directory':
                    current_level = current_level[part]['children']
        
        return structure
    
    def _create_directory_listing(self, structure: Dict, level: int = 0) -> str:
        """Create a markdown directory listing from the page structure."""
        listing = []
        indent = "  " * level
        
        for name, item in structure.items():
            if item['type'] == 'file':
                title = item['title']
                filename = f"{sanitize_filename(name)}.{self._get_file_extension()}"
                listing.append(f"{indent}- [{title}]({'/'.join([''] * level + [filename])})")
            elif item['type'] == 'directory':
                listing.append(f"{indent}- **{name.replace('-', ' ').title()}/**")
                if item.get('children'):
                    listing.append(self._create_directory_listing(item['children'], level + 1))
        
        return "\n".join(listing)
    
    def _get_file_extension(self) -> str:
        """Get file extension based on output format."""
        if self.config.output_format == 'markdown':
            return 'md'
        elif self.config.output_format == 'html':
            return 'html'
        else:
            return 'txt'
    
    def save_to_file(self, content: str, file_path: str):
        """Save content to file with proper encoding."""
        try:
            path = Path(file_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(path, 'w', encoding='utf-8') as f:
                f.write(content)
                
            self.logger.info(f"Content saved to {path}")
            
        except Exception as e:
            self.logger.error(f"Failed to save file {file_path}: {e}")
            raise
    
    def save_structured_output(self, crawled_pages: List, output_path: str):
        """Save structured output based on organization method."""
        base_path = Path(output_path)
        
        if self.config.organization == 'single':
            content = self._create_single_file(crawled_pages)
            self.save_to_file(content, output_path)
            
        elif self.config.organization == 'chapters':
            # Create main index
            main_content = self._create_chapters(crawled_pages)
            index_path = base_path.parent / f"index.{self._get_file_extension()}"
            self.save_to_file(main_content, str(index_path))
            
            # Create chapter files
            chapters = self._group_pages_by_structure(crawled_pages)
            for chapter_name, pages in chapters.items():
                chapter_content = self._create_single_file(pages)
                filename = f"chapter-{sanitize_filename(chapter_name)}.{self._get_file_extension()}"
                chapter_path = base_path.parent / filename
                self.save_to_file(chapter_content, str(chapter_path))
                
        elif self.config.organization == 'pages':
            # Create main index
            main_content = self._create_pages(crawled_pages)
            index_path = base_path.parent / f"index.{self._get_file_extension()}"
            self.save_to_file(main_content, str(index_path))
            
            # Create individual page files
            for page in crawled_pages:
                page_content = self.format_single_page(page)
                parsed_url = urlparse(page.url)
                path_parts = [part for part in parsed_url.path.split('/') if part]
                
                if path_parts:
                    filename = f"{sanitize_filename(path_parts[-1])}.{self._get_file_extension()}"
                    # Create directory structure
                    if len(path_parts) > 1:
                        dir_path = base_path.parent / "/".join(path_parts[:-1])
                        dir_path.mkdir(parents=True, exist_ok=True)
                        page_path = dir_path / filename
                    else:
                        page_path = base_path.parent / filename
                else:
                    page_path = base_path.parent / f"page-{len(crawled_pages)}.{self._get_file_extension()}"
                    
                self.save_to_file(page_content, str(page_path))
    
    def export_metadata(self, crawled_pages: List, output_path: str):
        """Export metadata about the crawling session."""
        metadata = {
            'scraping_session': {
                'timestamp': datetime.now().isoformat(),
                'total_pages': len(crawled_pages),
                'output_format': self.config.output_format,
                'organization': self.config.organization,
                'config': {
                    'max_depth': self.config.max_depth,
                    'delay': self.config.delay,
                    'max_delay': self.config.max_delay,
                    'max_pages': self.config.max_pages
                }
            },
            'pages': []
        }
        
        for page in crawled_pages:
            page_metadata = {
                'url': page.url,
                'title': page.title,
                'status_code': page.status_code,
                'content_length': len(page.content) if page.content else 0,
                'error': page.error
            }
            metadata['pages'].append(page_metadata)
        
        # Save metadata
        metadata_path = Path(output_path).parent / 'scraping_metadata.json'
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
            
        self.logger.info(f"Metadata saved to {metadata_path}")
