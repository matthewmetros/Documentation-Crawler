"""
Configuration Module
Central configuration management for the documentation scraper
"""

import os
from dataclasses import dataclass
from typing import List, Optional

@dataclass
class Config:
    """Configuration settings for the documentation scraper."""
    
    # Output settings
    output_format: str = 'markdown'  # markdown, html, text
    organization: str = 'single'     # single, chapters, pages
    output_path: Optional[str] = None
    
    # Crawling behavior
    max_depth: int = 3
    max_pages: int = 100
    delay: float = 1.0
    max_delay: float = 5.0
    no_delay: bool = False
    single_page: bool = False
    
    # Request settings
    timeout: int = 30
    retries: int = 3
    user_agent: str = (
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
        '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 DocumentationScraper/1.0'
    )
    
    # Content filtering
    include_patterns: List[str] = None
    exclude_patterns: List[str] = None
    content_selectors: List[str] = None
    
    # Google Docs integration
    google_credentials_file: str = 'credentials.json'
    
    def __post_init__(self):
        """Initialize default values for mutable fields."""
        if self.include_patterns is None:
            self.include_patterns = []
        if self.exclude_patterns is None:
            self.exclude_patterns = []
        if self.content_selectors is None:
            self.content_selectors = []
    
    @classmethod
    def from_dict(cls, config_dict: dict) -> 'Config':
        """Create Config instance from dictionary."""
        return cls(**config_dict)
    
    @classmethod
    def from_env(cls) -> 'Config':
        """Create Config instance from environment variables."""
        return cls(
            output_format=os.getenv('SCRAPER_OUTPUT_FORMAT', 'markdown'),
            organization=os.getenv('SCRAPER_ORGANIZATION', 'single'),
            max_depth=int(os.getenv('SCRAPER_MAX_DEPTH', '3')),
            max_pages=int(os.getenv('SCRAPER_MAX_PAGES', '100')),
            delay=float(os.getenv('SCRAPER_DELAY', '1.0')),
            max_delay=float(os.getenv('SCRAPER_MAX_DELAY', '5.0')),
            no_delay=os.getenv('SCRAPER_NO_DELAY', '').lower() in ('true', '1', 'yes'),
            timeout=int(os.getenv('SCRAPER_TIMEOUT', '30')),
            retries=int(os.getenv('SCRAPER_RETRIES', '3')),
            user_agent=os.getenv('SCRAPER_USER_AGENT', cls.user_agent),
            google_credentials_file=os.getenv('GOOGLE_CREDENTIALS_FILE', 'credentials.json')
        )
    
    def validate(self) -> List[str]:
        """Validate configuration and return list of errors."""
        errors = []
        
        # Validate output format
        if self.output_format not in ['markdown', 'html', 'text']:
            errors.append(f"Invalid output format: {self.output_format}")
        
        # Validate organization
        if self.organization not in ['single', 'chapters', 'pages']:
            errors.append(f"Invalid organization: {self.organization}")
        
        # Validate numeric values
        if self.max_depth < 1:
            errors.append("max_depth must be at least 1")
        if self.max_pages < 1:
            errors.append("max_pages must be at least 1")
        if self.delay < 0:
            errors.append("delay cannot be negative")
        if self.max_delay < self.delay:
            errors.append("max_delay must be >= delay")
        if self.timeout < 1:
            errors.append("timeout must be at least 1 second")
        if self.retries < 0:
            errors.append("retries cannot be negative")
        
        return errors
    
    def get_file_extension(self) -> str:
        """Get appropriate file extension for output format."""
        extensions = {
            'markdown': 'md',
            'html': 'html',
            'text': 'txt'
        }
        return extensions.get(self.output_format, 'txt')
