# Documentation Scraper with Google Docs Integration

## Overview

This is a comprehensive Python web application for scraping documentation websites and integrating with Google Docs for NotebookLM workflows. The application provides both a web interface and CLI for extracting clean, structured content from documentation sites and automatically creating Google Docs from the scraped content.

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Frontend Architecture
- **Web Interface**: Flask-based web application with Bootstrap UI
- **Static Assets**: CSS and JavaScript for responsive user interface
- **Template Engine**: Jinja2 templates for server-side rendering
- **Client-Side**: Vanilla JavaScript for dynamic interactions and API calls

### Backend Architecture
- **Framework**: Flask web framework for HTTP handling and routing
- **Modular Design**: Separate modules for different functionality (crawler, content extraction, output management)
- **Configuration Management**: Centralized configuration through dataclasses
- **Dual Interface**: Both web API endpoints and CLI command support

### Content Processing Pipeline
- **Web Scraping**: Uses trafilatura and BeautifulSoup for intelligent content extraction
- **Content Filtering**: Smart removal of navigation, ads, and non-content elements
- **Output Formats**: Support for Markdown, HTML, and plain text output
- **Organization Options**: Single file, chapters, or individual pages

## Key Components

### Web Crawler (`src/crawler.py`)
- **Respectful Crawling**: Implements robots.txt compliance and configurable delays
- **Duplicate Detection**: URL normalization and intelligent duplicate prevention
- **Progress Tracking**: Real-time progress monitoring with tqdm
- **Error Handling**: Robust retry mechanisms and failure tracking

### Content Extractor (`src/content_extractor.py`)
- **Framework Support**: Works with GitBook, Docusaurus, MkDocs, Sphinx, and more
- **Smart Selectors**: Uses CSS selectors to identify main content areas
- **Content Cleaning**: Removes navigation, ads, and non-essential elements
- **Format Conversion**: Converts HTML to Markdown using markdownify

### Google Docs Integration (`src/google_docs_integration.py`)
- **OAuth Authentication**: Secure Google API authentication flow
- **Document Creation**: Automatically creates Google Docs from scraped content
- **Content Updates**: Updates existing documents with new content
- **NotebookLM Optimization**: Formats content specifically for AI analysis

### Output Manager (`src/output_manager.py`)
- **Multiple Formats**: Generates Markdown, HTML, or plain text output
- **Organization Strategies**: Single file, chapter-based, or page-by-page organization
- **File Management**: Handles file naming, directory creation, and content organization
- **Metadata Inclusion**: Adds timestamps, source URLs, and table of contents

## Data Flow

1. **Input Processing**: User provides URL through web interface or CLI
2. **URL Validation**: System validates and normalizes the target URL
3. **Crawling**: DocumentationCrawler discovers and fetches pages
4. **Content Extraction**: ContentExtractor processes HTML and extracts clean content
5. **Output Generation**: OutputManager formats content according to user preferences
6. **Google Docs Integration**: Optional creation/update of Google Docs
7. **Result Delivery**: Content returned to user via web interface or saved to files

## External Dependencies

### Core Python Libraries
- **Flask**: Web framework for HTTP handling
- **requests**: HTTP client for web scraping
- **BeautifulSoup4**: HTML parsing and manipulation
- **trafilatura**: Intelligent content extraction
- **markdownify**: HTML to Markdown conversion
- **tqdm**: Progress bar functionality
- **colorama**: Cross-platform colored terminal output

### Google API Integration
- **google-auth**: Google API authentication
- **google-auth-oauthlib**: OAuth flow handling
- **google-auth-httplib2**: HTTP transport for Google APIs
- **google-api-python-client**: Google Docs and Drive API client

### Frontend Dependencies
- **Bootstrap 5.3.0**: CSS framework for responsive design
- **Feather Icons**: Icon library for UI elements

## Deployment Strategy

### Development Setup
- **Local Development**: Flask development server with debug mode
- **Configuration**: Environment-based configuration management
- **Credentials**: Local JSON files for Google API credentials
- **Static Assets**: Served directly by Flask in development

### Production Considerations
- **WSGI Server**: Designed to run with production WSGI servers (Gunicorn, uWSGI)
- **Static File Serving**: Can be configured with reverse proxy for static assets
- **Environment Variables**: Supports environment-based configuration
- **Logging**: Configurable logging levels and file output
- **Error Handling**: Comprehensive error handling and user feedback

### File Structure
- **Modular Architecture**: Clear separation between web interface, CLI, and core functionality
- **Template Organization**: HTML templates in dedicated directory
- **Static Assets**: CSS and JavaScript in static directory
- **Configuration**: Centralized configuration management
- **Output Management**: Flexible output directory structure

The application is designed to be easily deployable on various platforms while maintaining clean separation between the web interface, command-line interface, and core scraping functionality.