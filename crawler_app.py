#!/usr/bin/env python3
"""
Benjamin Western Documentation Crawler - Web Interface
A comprehensive web-based interface for documentation crawling with real-time progress tracking
"""

import os
import sys
import json
import asyncio
import logging
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime
import threading
import queue
import zipfile
import io

from flask import Flask, render_template, request, jsonify, send_file, session
from flask_socketio import SocketIO, emit, join_room, leave_room
import uuid

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(__file__))

from crawler.new_crawler import DocCrawler
from utils.config import CrawlerConfig
from utils.logging import setup_logging

# Configure logging
setup_logging(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__, template_folder='templates', static_folder='static')
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-key-change-in-production')
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# Global storage for active crawling sessions
active_sessions: Dict[str, Dict] = {}
session_lock = threading.Lock()

class CrawlerWebInterface:
    """Web interface wrapper for Benjamin Western's documentation crawler."""
    
    def __init__(self, session_id: str, socketio_instance):
        self.session_id = session_id
        self.socketio = socketio_instance
        self.crawler = None
        self.config = None
        self.status = "idle"
        self.progress = 0
        self.total_pages = 0
        self.scraped_content = {}
        self.error_log = []
        self.stop_requested = False
        
    def emit_status(self, message: str, level: str = "info"):
        """Emit status update to the connected client."""
        self.socketio.emit('crawler_status', {
            'session_id': self.session_id,
            'message': message,
            'level': level,
            'timestamp': datetime.now().isoformat(),
            'status': self.status,
            'progress': self.progress,
            'total_pages': self.total_pages
        }, room=self.session_id)
        
    def emit_progress(self, current: int, total: int):
        """Emit progress update to the connected client."""
        self.progress = current
        self.total_pages = total
        progress_percent = (current / total * 100) if total > 0 else 0
        
        self.socketio.emit('crawler_progress', {
            'session_id': self.session_id,
            'current': current,
            'total': total,
            'percent': progress_percent,
            'timestamp': datetime.now().isoformat()
        }, room=self.session_id)
        
    def start_crawling(self, config_data: Dict):
        """Start the crawling process in a separate thread."""
        try:
            self.status = "initializing"
            self.stop_requested = False
            self.emit_status("Initializing crawler configuration...")
            
            # Create crawler configuration
            self.config = CrawlerConfig(
                base_url=config_data.get('url', ''),
                language=config_data.get('language', 'en'),
                max_workers=config_data.get('max_workers', 5),
                debug=config_data.get('debug', False),
                timeout=config_data.get('timeout', 10),
                max_retries=config_data.get('max_retries', 3),
                retry_delay=config_data.get('retry_delay', 1),
                chunk_size=config_data.get('chunk_size', 3)
            )
            
            self.emit_status(f"Creating crawler for URL: {self.config.base_url}")
            
            # Initialize crawler
            base_urls = [self.config.base_url]
            self.crawler = DocCrawler(self.config, base_urls)
            
            self.emit_status("Parsing sitemap and discovering pages...")
            self.status = "discovering"
            
            # Parse sitemap to find pages
            logger.info(f"🔍 Starting sitemap discovery for URLs: {base_urls}")
            self.crawler.parse_sitemap(base_urls)
            
            logger.info(f"📊 Sitemap discovery complete. Found {len(self.crawler.sitemap)} pages")
            
            if not self.crawler.sitemap:
                error_msg = f"No pages found for {self.config.base_url}"
                logger.error(f"❌ {error_msg}")
                logger.error(f"🔧 Troubleshooting steps:")
                logger.error(f"  1. Verify the URL is a documentation site")
                logger.error(f"  2. Check if the site requires authentication")
                logger.error(f"  3. Try a more specific documentation URL")
                logger.error(f"  4. Ensure language setting matches site content")
                self.emit_status(f"{error_msg} - Try a more specific documentation URL", "error")
                self.status = "error"
                return
                
            self.emit_status(f"Found {len(self.crawler.sitemap)} documentation pages")
            
            # Auto-select all pages for web interface
            selected_urls = list(self.crawler.sitemap.keys())
            
            self.emit_status("Starting content extraction...")
            self.status = "crawling"
            
            # Start crawling with progress tracking
            self.crawl_with_progress(selected_urls, config_data)
            
        except Exception as e:
            logger.error(f"Crawling error: {e}")
            self.emit_status(f"Crawling failed: {str(e)}", "error")
            self.status = "error"
            
    def crawl_with_progress(self, selected_urls: List[str], config_data: Dict):
        """Crawl pages with real-time progress updates."""
        logger.info("🔧 TRACE: crawl_with_progress() - Entry point")
        logger.info(f"🔧 TRACE: Received config_data: {config_data}")
        
        store_markdown = config_data.get('store_markdown', True)
        store_raw_html = config_data.get('store_raw_html', False)
        store_text = config_data.get('store_text', False)
        store_flatten = config_data.get('store_flatten', False)
        
        logger.info("🔧 TRACE: Format options extracted from config:")
        logger.info(f"  - store_markdown: {store_markdown}")
        logger.info(f"  - store_raw_html: {store_raw_html}")
        logger.info(f"  - store_text: {store_text}")
        logger.info(f"  - store_flatten: {store_flatten}")
        
        logger.warning("⚠️ TRACE: CRITICAL ISSUE - Format options are extracted but NOT USED!")
        logger.warning("⚠️ TRACE: Only Markdown content will be generated regardless of user selection")
        
        total_urls = len(selected_urls)
        processed = 0
        
        self.emit_progress(0, total_urls)
        
        # Process pages and track progress
        for url in selected_urls:
            if self.stop_requested:
                self.emit_status("Crawling stopped by user", "warning")
                self.status = "stopped"
                return
                
            try:
                # Get page content
                content = self.crawler._scrape_single_page(url)
                if content:
                    self.scraped_content[url] = {
                        'content': content,
                        'title': self.crawler.sitemap.get(url, url),
                        'timestamp': datetime.now().isoformat()
                    }
                    
                processed += 1
                self.emit_progress(processed, total_urls)
                self.emit_status(f"Processed: {url}")
                
            except Exception as e:
                self.error_log.append(f"Failed to process {url}: {str(e)}")
                self.emit_status(f"Error processing {url}: {str(e)}", "warning")
                processed += 1
                self.emit_progress(processed, total_urls)
                
        self.status = "completed"
        self.emit_status(f"Crawling completed! Successfully processed {len(self.scraped_content)} pages")
        
    def stop_crawling(self):
        """Stop the crawling process."""
        self.stop_requested = True
        self.emit_status("Stop request received...")
        
    def get_results(self):
        """Get crawling results."""
        return {
            'status': self.status,
            'total_pages': len(self.scraped_content),
            'content': self.scraped_content,
            'errors': self.error_log,
            'sitemap': self.crawler.sitemap if self.crawler else {}
        }

@app.route('/')
def index():
    """Main crawler interface."""
    return render_template('crawler_interface.html')

@app.route('/api/start-crawling', methods=['POST'])
def start_crawling():
    """Start a new crawling session."""
    try:
        data = request.get_json()
        session_id = str(uuid.uuid4())
        
        # Create new crawler session
        crawler_interface = CrawlerWebInterface(session_id, socketio)
        
        with session_lock:
            active_sessions[session_id] = {
                'crawler': crawler_interface,
                'started_at': datetime.now().isoformat(),
                'config': data
            }
        
        # Start crawling in background thread
        crawl_thread = threading.Thread(
            target=crawler_interface.start_crawling,
            args=(data,)
        )
        crawl_thread.daemon = True
        crawl_thread.start()
        
        return jsonify({
            'success': True,
            'session_id': session_id,
            'message': 'Crawling session started'
        })
        
    except Exception as e:
        logger.error(f"Error starting crawling: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/stop-crawling/<session_id>', methods=['POST'])
def stop_crawling(session_id):
    """Stop a crawling session."""
    try:
        with session_lock:
            if session_id in active_sessions:
                crawler_interface = active_sessions[session_id]['crawler']
                crawler_interface.stop_crawling()
                return jsonify({'success': True, 'message': 'Stop request sent'})
            else:
                return jsonify({'success': False, 'error': 'Session not found'}), 404
                
    except Exception as e:
        logger.error(f"Error stopping crawling: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/results/<session_id>')
def get_results(session_id):
    """Get crawling results for a session."""
    try:
        with session_lock:
            if session_id in active_sessions:
                crawler_interface = active_sessions[session_id]['crawler']
                results = crawler_interface.get_results()
                return jsonify(results)
            else:
                return jsonify({'error': 'Session not found'}), 404
                
    except Exception as e:
        logger.error(f"Error getting results: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/download/<session_id>')
def download_results(session_id):
    """Download crawled content as a ZIP file."""
    try:
        logger.info("📦 TRACE: download_results() - Entry point")
        logger.info(f"📦 TRACE: Session ID: {session_id}")
        
        with session_lock:
            if session_id not in active_sessions:
                logger.error(f"📦 TRACE: Session {session_id} not found in active_sessions")
                return jsonify({'error': 'Session not found'}), 404
                
            crawler_interface = active_sessions[session_id]['crawler']
            config_data = active_sessions[session_id].get('config', {})
            
            logger.info("📦 TRACE: Original configuration data:")
            logger.info(f"  - store_markdown: {config_data.get('store_markdown', 'NOT_FOUND')}")
            logger.info(f"  - store_raw_html: {config_data.get('store_raw_html', 'NOT_FOUND')}")
            logger.info(f"  - store_text: {config_data.get('store_text', 'NOT_FOUND')}")
            
            results = crawler_interface.get_results()
            logger.info(f"📦 TRACE: Results retrieved, {len(results.get('content', {}))} pages found")
            
        # Create ZIP file in memory
        zip_buffer = io.BytesIO()
        
        logger.info("📦 TRACE: Creating ZIP file")
        
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            logger.warning("📦 TRACE: CRITICAL ISSUE - Hardcoded to create .md files only!")
            logger.warning("📦 TRACE: User format preferences are completely ignored here!")
            
            # Add each page as a separate markdown file
            for url, page_data in results['content'].items():
                # Create safe filename from URL
                filename = url.replace('https://', '').replace('http://', '')
                filename = filename.replace('/', '_').replace('?', '_').replace('&', '_')
                filename = f"{filename}.md"
                
                logger.info(f"📦 TRACE: Adding file to ZIP: {filename}")
                logger.warning(f"📦 TRACE: File extension hardcoded to .md regardless of user selection!")
                
                # Add file to ZIP
                zip_file.writestr(filename, page_data['content'])
                logger.info(f"📦 TRACE: Content added for {filename} ({len(page_data['content'])} chars)")
                
            # Add metadata file
            metadata = {
                'session_id': session_id,
                'total_pages': results['total_pages'],
                'crawled_at': datetime.now().isoformat(),
                'urls': list(results['content'].keys()),
                'errors': results['errors']
            }
            zip_file.writestr('metadata.json', json.dumps(metadata, indent=2))
            
        zip_buffer.seek(0)
        
        # Create filename with timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"documentation_crawl_{timestamp}.zip"
        
        return send_file(
            zip_buffer,
            as_attachment=True,
            download_name=filename,
            mimetype='application/zip'
        )
        
    except Exception as e:
        logger.error(f"Error downloading results: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/sessions')
def list_sessions():
    """List all active crawling sessions."""
    try:
        with session_lock:
            sessions = {}
            for session_id, session_data in active_sessions.items():
                crawler = session_data['crawler']
                sessions[session_id] = {
                    'started_at': session_data['started_at'],
                    'status': crawler.status,
                    'progress': crawler.progress,
                    'total_pages': crawler.total_pages,
                    'url': session_data['config'].get('url', '')
                }
        
        return jsonify({'sessions': sessions})
        
    except Exception as e:
        logger.error(f"Error listing sessions: {e}")
        return jsonify({'error': str(e)}), 500

# SocketIO event handlers for real-time communication

@socketio.on('connect')
def handle_connect():
    """Handle client connection."""
    logger.info(f"Client connected: {request.sid}")
    emit('connected', {'message': 'Connected to crawler server'})

@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection."""
    logger.info(f"Client disconnected: {request.sid}")

@socketio.on('join_session')
def handle_join_session(data):
    """Join a crawling session room for real-time updates."""
    session_id = data.get('session_id')
    if session_id:
        join_room(session_id)
        emit('joined_session', {'session_id': session_id})
        logger.info(f"Client {request.sid} joined session {session_id}")

@socketio.on('leave_session')
def handle_leave_session(data):
    """Leave a crawling session room."""
    session_id = data.get('session_id')
    if session_id:
        leave_room(session_id)
        emit('left_session', {'session_id': session_id})
        logger.info(f"Client {request.sid} left session {session_id}")

def cleanup_old_sessions():
    """Clean up old completed sessions (run periodically)."""
    current_time = datetime.now()
    to_remove = []
    
    with session_lock:
        for session_id, session_data in active_sessions.items():
            crawler = session_data['crawler']
            if crawler.status in ['completed', 'error', 'stopped']:
                # Remove sessions older than 1 hour
                started_time = datetime.fromisoformat(session_data['started_at'])
                if (current_time - started_time).total_seconds() > 3600:
                    to_remove.append(session_id)
        
        for session_id in to_remove:
            del active_sessions[session_id]
            logger.info(f"Cleaned up old session: {session_id}")

def run_crawler_app():
    """Run the crawler web application."""
    print("🚀 Starting Benjamin Western Documentation Crawler Web Interface")
    print(f"📱 Access the interface at: http://localhost:5000")
    print("🔍 Enter documentation URLs to start intelligent crawling")
    print("📊 Real-time progress tracking and downloadable results")
    
    # Cleanup old sessions periodically
    def periodic_cleanup():
        while True:
            try:
                cleanup_old_sessions()
                threading.Event().wait(300)  # Wait 5 minutes
            except Exception as e:
                logger.error(f"Error in periodic cleanup: {e}")
    
    cleanup_thread = threading.Thread(target=periodic_cleanup)
    cleanup_thread.daemon = True
    cleanup_thread.start()
    
    # Run the application
    socketio.run(app, host='0.0.0.0', port=5000, debug=True, allow_unsafe_werkzeug=True)

if __name__ == '__main__':
    run_crawler_app()