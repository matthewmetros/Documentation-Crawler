#!/usr/bin/env python3
"""
Documentation Scraper with Google Docs Integration
A comprehensive tool for scraping documentation websites and integrating with NotebookLM workflows
"""

import os
import sys
import logging
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from flask import Flask, render_template, request, jsonify, send_from_directory
from src.cli import main as cli_main
from src.crawler import DocumentationCrawler
from src.google_docs_integration import GoogleDocsIntegrator
from src.config import Config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

app = Flask(__name__, template_folder='templates', static_folder='static')

@app.route('/')
def index():
    """Main web interface for the documentation scraper."""
    return render_template('index.html')

@app.route('/api/scrape', methods=['POST'])
def api_scrape():
    """API endpoint for scraping documentation."""
    try:
        data = request.get_json()
        
        if not data or 'url' not in data:
            return jsonify({'error': 'URL is required'}), 400
            
        url = data['url']
        output_format = data.get('format', 'markdown')
        max_depth = data.get('max_depth', 3)
        delay = data.get('delay', 1.0)
        single_page = data.get('single_page', False)
        
        # Initialize crawler
        config = Config(
            max_depth=max_depth,
            delay=delay,
            output_format=output_format
        )
        
        crawler = DocumentationCrawler(config)
        
        if single_page:
            # Scrape single page
            content = crawler.scrape_single_page(url)
            return jsonify({
                'success': True,
                'content': content,
                'pages_scraped': 1
            })
        else:
            # Full crawl
            result = crawler.crawl_documentation(url)
            return jsonify({
                'success': True,
                'content': result['content'],
                'pages_scraped': result['pages_scraped'],
                'urls_processed': result['urls_processed']
            })
            
    except Exception as e:
        logging.error(f"Error in API scrape: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/create-google-doc', methods=['POST'])
def api_create_google_doc():
    """API endpoint for creating Google Docs."""
    try:
        data = request.get_json()
        
        if not data or 'title' not in data or 'content' not in data:
            return jsonify({'error': 'Title and content are required'}), 400
            
        title = data['title']
        content = data['content']
        
        # Initialize Google Docs integrator
        integrator = GoogleDocsIntegrator()
        
        # Create document
        doc_id = integrator.create_document(title, content)
        doc_url = f"https://docs.google.com/document/d/{doc_id}"
        
        return jsonify({
            'success': True,
            'document_id': doc_id,
            'document_url': doc_url
        })
        
    except Exception as e:
        logging.error(f"Error creating Google Doc: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/update-google-doc', methods=['POST'])
def api_update_google_doc():
    """API endpoint for updating existing Google Docs."""
    try:
        data = request.get_json()
        
        if not data or 'document_id' not in data or 'content' not in data:
            return jsonify({'error': 'Document ID and content are required'}), 400
            
        document_id = data['document_id']
        content = data['content']
        
        # Initialize Google Docs integrator
        integrator = GoogleDocsIntegrator()
        
        # Update document
        integrator.update_document(document_id, content)
        
        return jsonify({'success': True})
        
    except Exception as e:
        logging.error(f"Error updating Google Doc: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/static/<path:filename>')
def static_files(filename):
    """Serve static files."""
    return send_from_directory('static', filename)

def run_web_interface():
    """Run the web interface."""
    print("🚀 Starting Documentation Scraper Web Interface")
    print(f"📱 Access the interface at: http://localhost:5000")
    print("🔗 Use this interface to scrape documentation and create Google Docs")
    print("📖 For CLI usage, run: python main.py --help")
    
    app.run(host='0.0.0.0', port=5000, debug=True)

if __name__ == '__main__':
    if len(sys.argv) > 1:
        # CLI mode
        cli_main()
    else:
        # Web interface mode
        run_web_interface()
