# 📚 Documentation Scraper with Google Docs Integration

A comprehensive Python tool for scraping documentation websites and integrating with Google Docs for seamless NotebookLM workflows. Extract clean, structured content from any documentation site and automatically create Google Documents ready for AI analysis.

![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)
![License](https://img.shields.io/badge/License-MIT-green.svg)
![Web Interface](https://img.shields.io/badge/Interface-Web%20%2B%20CLI-orange.svg)

## 🌟 Features

### Smart Web Scraping
- **Intelligent Content Extraction**: Uses trafilatura and BeautifulSoup for clean content extraction
- **Multiple Documentation Frameworks**: Works with GitBook, Docusaurus, MkDocs, Sphinx, and more
- **Respectful Crawling**: Configurable delays, robots.txt compliance, and rate limiting
- **Duplicate Detection**: URL normalization and smart duplicate prevention
- **Progress Tracking**: Real-time progress bars and detailed logging

### Multiple Output Formats
- **Markdown**: Clean, structured markdown perfect for NotebookLM
- **HTML**: Formatted HTML with preserved styling
- **Plain Text**: Simple text extraction for basic needs
- **Organized Output**: Single file, chapters, or individual pages

### Google Docs Integration
- **Seamless Creation**: Automatically create Google Docs from scraped content
- **Update Existing**: Update existing documents with new content
- **NotebookLM Ready**: Optimized formatting for AI analysis
- **Batch Processing**: Handle multiple sources in single documents

### Dual Interface
- **Web Interface**: Modern, responsive web UI for easy use
- **Command Line**: Powerful CLI with comprehensive options
- **Cross-Platform**: Windows, macOS, and Linux support

## 🚀 Quick Start

### Installation

1. **Clone the repository**
```bash
git clone https://github.com/your-username/documentation-scraper.git
cd documentation-scraper
