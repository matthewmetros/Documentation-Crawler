#!/usr/bin/env python3
"""
Command Line Interface for Documentation Scraper
"""

import argparse
import sys
import logging
import json
from pathlib import Path
from typing import Optional

import colorama
from colorama import Fore, Style
from tqdm import tqdm

from .crawler import DocumentationCrawler
from .google_docs_integration import GoogleDocsIntegrator
from .config import Config
from .utils import setup_logging, validate_url

# Initialize colorama for cross-platform colored output
colorama.init()

def print_banner():
    """Print application banner."""
    banner = f"""
{Fore.CYAN}
╔══════════════════════════════════════════════════════════════════╗
║                    Documentation Scraper                        ║
║          Comprehensive web scraping for NotebookLM workflows     ║
╚══════════════════════════════════════════════════════════════════╝
{Style.RESET_ALL}
    """
    print(banner)

def create_parser() -> argparse.ArgumentParser:
    """Create and configure argument parser."""
    parser = argparse.ArgumentParser(
        description="Scrape documentation websites and export to various formats with Google Docs integration",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic scraping to Markdown
  python main.py -u https://docs.python.org/3/ -o python_docs.md

  # Scrape with custom settings
  python main.py -u https://react.dev/docs -o react_docs/ --format html --depth 5 --delay 2.0

  # Single page mode
  python main.py -u https://docs.python.org/3/tutorial/ -o tutorial.md --single-page

  # Create Google Doc
  python main.py -u https://nextjs.org/docs -o nextjs_docs.md --create-google-doc

  # Update existing Google Doc
  python main.py -u https://vue.js.org/guide/ --update-google-doc 1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms

  # Web interface mode
  python main.py --web
        """
    )
    
    # Required arguments group
    required = parser.add_argument_group('required arguments')
    required.add_argument(
        '-u', '--url',
        type=str,
        help='Documentation website URL to scrape'
    )
    
    # Output arguments
    parser.add_argument(
        '-o', '--output',
        type=str,
        help='Output file or directory path'
    )
    
    parser.add_argument(
        '--format',
        choices=['markdown', 'html', 'text'],
        default='markdown',
        help='Output format (default: markdown)'
    )
    
    parser.add_argument(
        '--organization',
        choices=['single', 'chapters', 'pages'],
        default='single',
        help='Output organization method (default: single)'
    )
    
    # Scraping behavior
    parser.add_argument(
        '--depth',
        type=int,
        default=3,
        help='Maximum crawling depth (default: 3)'
    )
    
    parser.add_argument(
        '--delay',
        type=float,
        default=1.0,
        help='Delay between requests in seconds (default: 1.0)'
    )
    
    parser.add_argument(
        '--max-delay',
        type=float,
        default=5.0,
        help='Maximum random delay between requests (default: 5.0)'
    )
    
    parser.add_argument(
        '--no-delay',
        action='store_true',
        help='Disable delays between requests (use with caution)'
    )
    
    parser.add_argument(
        '--single-page',
        action='store_true',
        help='Scrape only the provided URL (no crawling)'
    )
    
    parser.add_argument(
        '--max-pages',
        type=int,
        default=100,
        help='Maximum number of pages to scrape (default: 100)'
    )
    
    # Google Docs integration
    parser.add_argument(
        '--create-google-doc',
        action='store_true',
        help='Create a new Google Doc with scraped content'
    )
    
    parser.add_argument(
        '--update-google-doc',
        type=str,
        help='Update existing Google Doc with specified ID'
    )
    
    parser.add_argument(
        '--google-doc-title',
        type=str,
        help='Title for the Google Doc (default: derived from URL)'
    )
    
    # Filtering and content options
    parser.add_argument(
        '--include-patterns',
        type=str,
        nargs='+',
        help='URL patterns to include (regex supported)'
    )
    
    parser.add_argument(
        '--exclude-patterns',
        type=str,
        nargs='+',
        help='URL patterns to exclude (regex supported)'
    )
    
    parser.add_argument(
        '--content-selectors',
        type=str,
        nargs='+',
        help='CSS selectors for content extraction'
    )
    
    # Technical options
    parser.add_argument(
        '--user-agent',
        type=str,
        help='Custom user agent string'
    )
    
    parser.add_argument(
        '--timeout',
        type=int,
        default=30,
        help='Request timeout in seconds (default: 30)'
    )
    
    parser.add_argument(
        '--retries',
        type=int,
        default=3,
        help='Number of retry attempts (default: 3)'
    )
    
    # Logging and output
    parser.add_argument(
        '--verbose', '-v',
        action='count',
        default=0,
        help='Increase verbosity (-v for INFO, -vv for DEBUG)'
    )
    
    parser.add_argument(
        '--quiet', '-q',
        action='store_true',
        help='Suppress all output except errors'
    )
    
    parser.add_argument(
        '--log-file',
        type=str,
        help='Log to file instead of console'
    )
    
    # Web interface
    parser.add_argument(
        '--web',
        action='store_true',
        help='Launch web interface instead of CLI mode'
    )
    
    # Configuration
    parser.add_argument(
        '--config',
        type=str,
        help='Path to JSON configuration file'
    )
    
    parser.add_argument(
        '--save-config',
        type=str,
        help='Save current configuration to file'
    )
    
    return parser

def load_config_file(config_path: str) -> dict:
    """Load configuration from JSON file."""
    try:
        with open(config_path, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"{Fore.RED}Error loading config file: {e}{Style.RESET_ALL}")
        sys.exit(1)

def save_config_file(config_path: str, config: Config):
    """Save configuration to JSON file."""
    try:
        config_dict = {
            'url': getattr(config, 'url', ''),
            'output_path': getattr(config, 'output_path', ''),
            'format': config.output_format,
            'organization': config.organization,
            'max_depth': config.max_depth,
            'delay': config.delay,
            'max_delay': config.max_delay,
            'no_delay': config.no_delay,
            'single_page': getattr(config, 'single_page', False),
            'max_pages': config.max_pages,
            'timeout': config.timeout,
            'retries': config.retries,
            'user_agent': config.user_agent,
            'include_patterns': getattr(config, 'include_patterns', []),
            'exclude_patterns': getattr(config, 'exclude_patterns', []),
            'content_selectors': getattr(config, 'content_selectors', [])
        }
        
        with open(config_path, 'w') as f:
            json.dump(config_dict, f, indent=2)
            
        print(f"{Fore.GREEN}Configuration saved to {config_path}{Style.RESET_ALL}")
        
    except Exception as e:
        print(f"{Fore.RED}Error saving config file: {e}{Style.RESET_ALL}")

def main():
    """Main CLI entry point."""
    parser = create_parser()
    args = parser.parse_args()
    
    # Handle web interface mode
    if args.web:
        from main import run_web_interface
        run_web_interface()
        return
    
    # Validate required arguments
    if not args.url and not args.config:
        print(f"{Fore.RED}Error: URL is required (use -u/--url or --config){Style.RESET_ALL}")
        parser.print_help()
        sys.exit(1)
    
    # Setup logging
    log_level = logging.WARNING
    if args.quiet:
        log_level = logging.ERROR
    elif args.verbose == 1:
        log_level = logging.INFO
    elif args.verbose >= 2:
        log_level = logging.DEBUG
        
    setup_logging(level=log_level, log_file=args.log_file)
    
    # Print banner unless quiet mode
    if not args.quiet:
        print_banner()
    
    try:
        # Load configuration
        config_dict = {}
        if args.config:
            config_dict = load_config_file(args.config)
        
        # Override with command line arguments
        config_dict.update({k: v for k, v in vars(args).items() if v is not None})
        
        # Validate URL
        url = config_dict.get('url') or args.url
        if not validate_url(url):
            print(f"{Fore.RED}Error: Invalid URL format{Style.RESET_ALL}")
            sys.exit(1)
        
        # Create configuration
        config = Config(**config_dict)
        
        # Save configuration if requested
        if args.save_config:
            save_config_file(args.save_config, config)
            return
        
        # Initialize crawler
        crawler = DocumentationCrawler(config)
        
        print(f"{Fore.CYAN}🔍 Starting documentation scraping...{Style.RESET_ALL}")
        print(f"URL: {url}")
        print(f"Format: {config.output_format}")
        print(f"Organization: {config.organization}")
        
        if args.single_page:
            # Single page mode
            print(f"{Fore.YELLOW}📄 Single page mode enabled{Style.RESET_ALL}")
            content = crawler.scrape_single_page(url)
            
            if args.output:
                # Save to file
                output_path = Path(args.output)
                output_path.parent.mkdir(parents=True, exist_ok=True)
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                print(f"{Fore.GREEN}✅ Content saved to {output_path}{Style.RESET_ALL}")
            else:
                print(content)
        else:
            # Full crawling mode
            result = crawler.crawl_documentation(url)
            
            print(f"{Fore.GREEN}✅ Scraping completed!{Style.RESET_ALL}")
            print(f"Pages scraped: {result['pages_scraped']}")
            print(f"URLs processed: {len(result['urls_processed'])}")
            
            if args.output:
                # Save to file
                output_path = Path(args.output)
                if config.organization == 'single':
                    output_path.parent.mkdir(parents=True, exist_ok=True)
                    with open(output_path, 'w', encoding='utf-8') as f:
                        f.write(result['content'])
                    print(f"{Fore.GREEN}✅ Content saved to {output_path}{Style.RESET_ALL}")
                else:
                    # Multiple files - handled by crawler
                    print(f"{Fore.GREEN}✅ Content saved to {output_path}{Style.RESET_ALL}")
        
        # Google Docs integration
        if args.create_google_doc or args.update_google_doc:
            print(f"{Fore.CYAN}📝 Google Docs integration...{Style.RESET_ALL}")
            
            try:
                integrator = GoogleDocsIntegrator()
                
                if args.create_google_doc:
                    # Create new document
                    title = args.google_doc_title or f"Documentation: {url}"
                    content_to_upload = result.get('content', content) if not args.single_page else content
                    
                    doc_id = integrator.create_document(title, content_to_upload)
                    doc_url = f"https://docs.google.com/document/d/{doc_id}"
                    
                    print(f"{Fore.GREEN}✅ Google Doc created!{Style.RESET_ALL}")
                    print(f"Document ID: {doc_id}")
                    print(f"Document URL: {doc_url}")
                    
                elif args.update_google_doc:
                    # Update existing document
                    content_to_upload = result.get('content', content) if not args.single_page else content
                    integrator.update_document(args.update_google_doc, content_to_upload)
                    
                    print(f"{Fore.GREEN}✅ Google Doc updated!{Style.RESET_ALL}")
                    print(f"Document ID: {args.update_google_doc}")
                    
            except Exception as e:
                print(f"{Fore.RED}❌ Google Docs integration failed: {e}{Style.RESET_ALL}")
                logging.error(f"Google Docs error: {e}")
        
        # Success message
        if not args.quiet:
            print(f"\n{Fore.GREEN}🎉 Documentation scraping completed successfully!{Style.RESET_ALL}")
            print(f"{Fore.CYAN}💡 Tip: You can now upload the scraped content to NotebookLM for AI-powered analysis{Style.RESET_ALL}")
        
    except KeyboardInterrupt:
        print(f"\n{Fore.YELLOW}⚠️  Scraping interrupted by user{Style.RESET_ALL}")
        sys.exit(1)
    except Exception as e:
        print(f"{Fore.RED}❌ Error: {e}{Style.RESET_ALL}")
        logging.error(f"CLI error: {e}", exc_info=True)
        sys.exit(1)

if __name__ == '__main__':
    main()
