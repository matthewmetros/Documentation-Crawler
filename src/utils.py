"""
Utility functions for the documentation scraper
"""

import re
import os
import logging
from typing import List, Dict, Any
from urllib.parse import urlparse, urljoin
from pathlib import Path

def setup_logging(level=logging.INFO, log_file=None):
    """Setup logging configuration."""
    format_string = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
    if log_file:
        logging.basicConfig(
            level=level,
            format=format_string,
            filename=log_file,
            filemode='a'
        )
    else:
        logging.basicConfig(
            level=level,
            format=format_string
        )

def normalize_url(url: str) -> str:
    """Normalize URL by removing fragments and trailing slashes."""
    parsed = urlparse(url)
    normalized = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
    return normalized.rstrip('/')

def validate_url(url: str) -> bool:
    """Validate if URL is properly formatted."""
    try:
        parsed = urlparse(url)
        return bool(parsed.scheme and parsed.netloc)
    except:
        return False

def is_same_domain(url1: str, url2: str) -> bool:
    """Check if two URLs belong to the same domain."""
    try:
        domain1 = urlparse(url1).netloc.lower()
        domain2 = urlparse(url2).netloc.lower()
        return domain1 == domain2
    except:
        return False

def get_domain(url: str) -> str:
    """Extract domain from URL."""
    try:
        return urlparse(url).netloc.lower()
    except:
        return ""

def sanitize_filename(filename: str) -> str:
    """Sanitize filename for cross-platform compatibility."""
    # Replace invalid characters
    filename = re.sub(r'[<>:"/\\|?*]', '-', filename)
    # Replace multiple consecutive dashes with single dash
    filename = re.sub(r'-+', '-', filename)
    # Remove leading/trailing dashes and dots
    filename = filename.strip('.-')
    # Limit length
    if len(filename) > 100:
        filename = filename[:100]
    return filename or "untitled"

def create_table_of_contents(pages: List[Any]) -> str:
    """Create a table of contents from page list."""
    toc_lines = []
    
    for i, page in enumerate(pages, 1):
        title = page.title or f"Page {i}"
        # Create anchor link
        anchor = create_anchor_link(title)
        toc_lines.append(f"{i}. [{title}](#{anchor})")
    
    return "\n".join(toc_lines)

def create_anchor_link(text: str) -> str:
    """Create URL-safe anchor link from text."""
    # Convert to lowercase and replace spaces/special chars with dashes
    anchor = re.sub(r'[^\w\s-]', '', text.lower())
    anchor = re.sub(r'[-\s]+', '-', anchor)
    return anchor.strip('-')

def chunk_text(text: str, max_length: int = 1000000) -> List[str]:
    """Split text into chunks of specified maximum length."""
    if len(text) <= max_length:
        return [text]
    
    chunks = []
    start = 0
    
    while start < len(text):
        end = start + max_length
        
        # Try to break at a reasonable point (paragraph, sentence, etc.)
        if end < len(text):
            # Look for paragraph break
            paragraph_break = text.rfind('\n\n', start, end)
            if paragraph_break != -1 and paragraph_break > start:
                end = paragraph_break + 2
            else:
                # Look for sentence end
                sentence_end = text.rfind('. ', start, end)
                if sentence_end != -1 and sentence_end > start:
                    end = sentence_end + 2
                else:
                    # Look for word boundary
                    word_boundary = text.rfind(' ', start, end)
                    if word_boundary != -1 and word_boundary > start:
                        end = word_boundary + 1
        
        chunks.append(text[start:end])
        start = end
    
    return chunks

def convert_markdown_to_docs_format(markdown_content: str) -> List[Dict]:
    """Convert markdown content to Google Docs API format."""
    # This is a simplified conversion - in a full implementation,
    # you'd want a more sophisticated markdown parser
    
    requests = []
    lines = markdown_content.split('\n')
    current_index = 1
    
    for line in lines:
        if not line.strip():
            # Empty line
            requests.append({
                'insertText': {
                    'location': {'index': current_index},
                    'text': '\n'
                }
            })
            current_index += 1
            continue
        
        # Handle headers
        header_match = re.match(r'^(#{1,6})\s+(.+)', line)
        if header_match:
            level = len(header_match.group(1))
            text = header_match.group(2) + '\n'
            
            requests.append({
                'insertText': {
                    'location': {'index': current_index},
                    'text': text
                }
            })
            
            # Apply heading style
            requests.append({
                'updateParagraphStyle': {
                    'range': {
                        'startIndex': current_index,
                        'endIndex': current_index + len(text) - 1
                    },
                    'paragraphStyle': {
                        'namedStyleType': f'HEADING_{level}'
                    },
                    'fields': 'namedStyleType'
                }
            })
            
            current_index += len(text)
            continue
        
        # Handle bold text
        bold_pattern = r'\*\*(.*?)\*\*'
        line_with_formatting = line
        
        # Regular text
        requests.append({
            'insertText': {
                'location': {'index': current_index},
                'text': line + '\n'
            }
        })
        
        current_index += len(line) + 1
    
    return requests

def extract_urls_from_text(text: str) -> List[str]:
    """Extract URLs from text content."""
    url_pattern = r'https?://[^\s<>"\']+|www\.[^\s<>"\']+'
    urls = re.findall(url_pattern, text, re.IGNORECASE)
    
    # Clean up URLs
    cleaned_urls = []
    for url in urls:
        url = url.rstrip('.,!?;:')  # Remove trailing punctuation
        if not url.startswith('http'):
            url = 'https://' + url
        cleaned_urls.append(url)
    
    return cleaned_urls

def estimate_reading_time(text: str) -> int:
    """Estimate reading time in minutes based on word count."""
    words = len(text.split())
    # Average reading speed: 200-300 words per minute
    reading_speed = 250
    return max(1, round(words / reading_speed))

def clean_html_text(text: str) -> str:
    """Clean text extracted from HTML."""
    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text)
    # Remove leading/trailing whitespace
    text = text.strip()
    # Fix common encoding issues
    replacements = {
        '&amp;': '&',
        '&lt;': '<',
        '&gt;': '>',
        '&quot;': '"',
        '&#39;': "'",
        '&nbsp;': ' ',
    }
    
    for old, new in replacements.items():
        text = text.replace(old, new)
    
    return text

def create_progress_callback(description: str = "Processing"):
    """Create a progress callback for long-running operations."""
    from tqdm import tqdm
    
    def progress_callback(current: int, total: int, message: str = ""):
        if not hasattr(progress_callback, 'pbar'):
            progress_callback.pbar = tqdm(total=total, desc=description)
        
        progress_callback.pbar.update(current - progress_callback.pbar.n)
        if message:
            progress_callback.pbar.set_description(f"{description}: {message}")
        
        if current >= total:
            progress_callback.pbar.close()
            delattr(progress_callback, 'pbar')
    
    return progress_callback

def ensure_directory_exists(path: str):
    """Ensure directory exists, create if it doesn't."""
    Path(path).mkdir(parents=True, exist_ok=True)

def get_file_size_human_readable(size_bytes: int) -> str:
    """Convert bytes to human readable format."""
    if size_bytes == 0:
        return "0B"
    
    size_names = ["B", "KB", "MB", "GB", "TB"]
    import math
    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)
    return f"{s} {size_names[i]}"
