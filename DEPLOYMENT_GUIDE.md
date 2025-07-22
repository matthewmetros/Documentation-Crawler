# Benjamin Western Documentation Crawler - Web Interface Deployment Guide

## Overview

This is a comprehensive web-based interface for Benjamin Western's documentation-crawler tool, providing intelligent documentation scraping with real-time progress tracking, advanced configuration options, and downloadable results.

## Features

### Core Functionality
- **Intelligent Documentation Crawling**: Automatically discovers and scrapes documentation pages from sitemaps
- **Multi-language Support**: Supports 11+ languages including English, French, German, Spanish, Portuguese, Japanese, Korean, Chinese, Italian, and Indonesian
- **Real-time Progress Tracking**: Live updates via WebSocket connections showing current status, pages processed, and errors
- **Advanced Configuration**: Customizable worker count, timeouts, retry logic, and chunk sizes for optimal performance
- **Multiple Output Formats**: Supports Markdown, raw HTML, and plain text extraction
- **Smart URL Processing**: Intelligent sitemap parsing and URL filtering based on relevance and language

### Web Interface Features
- **Modern Responsive UI**: Bootstrap-based interface that works on desktop and mobile
- **Real-time Logs**: Live terminal-style log display with color-coded messages
- **Session Management**: Track multiple crawling sessions with unique identifiers
- **Progress Visualization**: Progress bars, status indicators, and real-time statistics
- **Download Results**: One-click ZIP download of all crawled content with metadata
- **Form Validation**: Client-side validation and user-friendly error messages

### Technical Features
- **WebSocket Integration**: Real-time bidirectional communication using Flask-SocketIO
- **Asynchronous Processing**: Non-blocking crawling operations in background threads
- **Error Handling**: Comprehensive error tracking and user notification
- **State Management**: Persistent session tracking and cleanup of old sessions
- **Security**: Environment variable support for sensitive configuration

## Installation and Setup

### Prerequisites
- Python 3.8+
- Replit environment (recommended) or local development environment
- Internet connection for crawling external documentation sites

### Dependencies
The following Python packages are automatically installed:
```
flask>=2.3.0
flask-socketio>=5.3.0
requests>=2.31.0
beautifulsoup4>=4.12.0
markdownify>=0.11.0
tqdm>=4.66.0
```

### Environment Setup
1. **Clone/Download the Project**: Ensure all files are in your Replit or local environment
2. **Install Dependencies**: Dependencies are automatically installed when running the application
3. **Configure Environment Variables** (optional):
   ```bash
   export SECRET_KEY="your-secure-secret-key-here"
   export DEBUG_MODE="False"  # Set to "True" for development
   ```

## Running the Application

### On Replit (Recommended)
1. Open the Replit environment
2. Click the "Run" button or execute `python crawler_app.py`
3. The application will start on port 5000
4. Access via the provided Replit URL (usually `https://your-repl-name.your-username.repl.co`)

### Local Development
1. Install Python dependencies: `pip install -r requirements.txt`
2. Run the application: `python crawler_app.py`
3. Open your browser to `http://localhost:5000`

### Using Docker (Alternative)
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY . .
RUN pip install -r requirements.txt
EXPOSE 5000
CMD ["python", "crawler_app.py"]
```

## Usage Guide

### Basic Crawling Process
1. **Enter Documentation URL**: Input the base URL of the documentation site (e.g., `https://docs.example.com`)
2. **Select Language**: Choose the appropriate language for multi-language documentation sites
3. **Configure Advanced Options** (optional):
   - **Max Workers**: Number of parallel processing threads (1-20, default: 5)
   - **Timeout**: Request timeout in seconds (5-60, default: 10)
   - **Max Retries**: Number of retry attempts for failed requests (0-10, default: 3)
   - **Chunk Size**: URLs processed per batch (1-10, default: 3)
4. **Choose Output Formats**: Select desired output formats (Markdown, HTML, Text)
5. **Start Crawling**: Click "Start Crawling" to begin the process

### Advanced Configuration

#### Worker Configuration
- **Max Workers**: Controls parallel processing. Higher values increase speed but may overwhelm target servers
- **Recommended**: 3-5 workers for small sites, 5-10 for larger sites with good infrastructure

#### Rate Limiting
- **Timeout**: Prevents hanging requests. Increase for slow documentation sites
- **Retry Logic**: Automatically retries failed requests with exponential backoff

#### Output Options
- **Markdown**: Clean, readable format ideal for documentation analysis
- **Raw HTML**: Preserves original formatting and structure
- **Plain Text**: Stripped content for text analysis
- **Debug Mode**: Enables detailed logging for troubleshooting

### Monitoring Progress
- **Real-time Status**: Watch the crawler's current activity in the status panel
- **Progress Bar**: Visual indication of completion percentage
- **Live Logs**: Terminal-style output showing detailed operations
- **Error Tracking**: Automatic capture and display of any issues

### Downloading Results
1. Wait for crawling to complete (status shows "Completed")
2. Click "Download ZIP" button
3. Results include:
   - Individual markdown/HTML files for each page
   - `metadata.json` with crawling statistics and URLs
   - Organized file structure maintaining documentation hierarchy

## API Documentation

### REST Endpoints

#### Start Crawling Session
```http
POST /api/start-crawling
Content-Type: application/json

{
  "url": "https://docs.example.com",
  "language": "en",
  "max_workers": 5,
  "timeout": 10,
  "max_retries": 3,
  "chunk_size": 3,
  "store_markdown": true,
  "store_raw_html": false,
  "store_text": false,
  "debug": false
}
```

#### Stop Crawling Session
```http
POST /api/stop-crawling/{session_id}
```

#### Get Results
```http
GET /api/results/{session_id}
```

#### Download Results
```http
GET /api/download/{session_id}
```

#### List Active Sessions
```http
GET /api/sessions
```

### WebSocket Events

#### Client to Server
- `join_session`: Join a crawling session for real-time updates
- `leave_session`: Leave a crawling session

#### Server to Client
- `crawler_status`: Status updates with messages and progress
- `crawler_progress`: Numerical progress updates
- `connected`/`disconnected`: Connection status

## Troubleshooting

### Common Issues

#### Connection Problems
- **Symptom**: "Disconnected from server" status
- **Solution**: Refresh page, check internet connection, restart application

#### Crawling Failures
- **Symptom**: "No pages found in sitemap" error
- **Solution**: Verify URL is correct and site has a sitemap.xml file
- **Alternative**: Check if the site blocks automated requests

#### Timeout Errors
- **Symptom**: Multiple timeout messages in logs
- **Solution**: Increase timeout value in advanced settings
- **Alternative**: Reduce number of workers to be more respectful

#### Memory Issues
- **Symptom**: Application becomes slow or unresponsive
- **Solution**: Reduce worker count and chunk size
- **Alternative**: Process smaller documentation sites or sections

### Performance Optimization

#### For Large Documentation Sites
- Start with conservative settings (3 workers, 15-second timeout)
- Monitor logs for errors and adjust accordingly
- Consider processing in multiple smaller sessions

#### For Rate-Limited Sites
- Reduce workers to 1-2
- Increase timeout to 20-30 seconds
- Enable debug mode to monitor request patterns

#### For Slow Networks
- Increase timeout values
- Reduce chunk size to 1-2
- Use fewer workers (2-3)

### Debugging Tips
1. **Enable Debug Mode**: Provides detailed logging information
2. **Check Browser Console**: May show WebSocket connection issues
3. **Monitor Server Logs**: Application logs show detailed error information
4. **Test with Simple Sites**: Verify setup with smaller documentation sites first

## Security Considerations

### Environment Variables
- Always set a secure `SECRET_KEY` in production
- Consider setting `DEBUG_MODE=False` for production deployments

### Rate Limiting
- The crawler respects robots.txt when available
- Built-in delays prevent overwhelming target servers
- Configurable retry logic with exponential backoff

### Network Security
- Application binds to all interfaces (0.0.0.0) for Replit compatibility
- Consider firewall rules for production deployments
- WebSocket connections use same-origin policy

## Deployment on Different Platforms

### Replit Deployment
1. Import project into Replit
2. Ensure all files are present
3. Click "Run" - dependencies install automatically
4. Share via Replit's built-in hosting

### Heroku Deployment
```bash
# Create Procfile
echo "web: python crawler_app.py" > Procfile

# Deploy
git init
git add .
git commit -m "Initial commit"
heroku create your-app-name
git push heroku main
```

### DigitalOcean/AWS Deployment
1. Set up virtual machine with Python 3.8+
2. Clone repository
3. Install dependencies: `pip install -r requirements.txt`
4. Configure reverse proxy (nginx) for production
5. Use process manager (supervisor/systemd) for service management

### Docker Deployment
```bash
# Build image
docker build -t doc-crawler .

# Run container
docker run -p 5000:5000 -e SECRET_KEY="your-secret" doc-crawler
```

## Contributing and Development

### File Structure
```
├── crawler_app.py              # Main Flask application
├── templates/
│   └── crawler_interface.html  # Web interface template
├── crawler/
│   └── new_crawler.py          # Benjamin Western's crawler implementation
├── utils/                      # Utility modules
│   ├── config.py              # Configuration management
│   ├── display.py             # Progress display
│   ├── url_processor.py       # URL handling
│   └── logging.py             # Logging setup
├── converters/
│   └── html_to_md.py          # HTML to Markdown conversion
└── static/                    # CSS and JavaScript assets
```

### Adding New Features
1. **Backend Features**: Extend `CrawlerWebInterface` class in `crawler_app.py`
2. **Frontend Features**: Modify `CrawlerInterface` class in the HTML template
3. **Crawler Enhancements**: Update `DocCrawler` class in `crawler/new_crawler.py`

### Testing
- Test with various documentation sites (GitBook, Docusaurus, MkDocs, Sphinx)
- Verify real-time updates work correctly
- Test download functionality with different browsers
- Validate configuration edge cases

## Support and Resources

### Documentation Sites Tested
- ✅ GitBook-based documentation
- ✅ Docusaurus sites
- ✅ MkDocs documentation
- ✅ Sphinx-generated docs
- ✅ Custom documentation frameworks

### Browser Compatibility
- ✅ Chrome/Chromium 90+
- ✅ Firefox 85+
- ✅ Safari 14+
- ✅ Edge 90+

### Known Limitations
- Requires JavaScript for real-time features
- WebSocket support needed for live updates
- Some sites may block automated requests
- Large documentation sites may require patience

## License and Credits

Based on Benjamin Western's documentation-crawler project with web interface enhancements. Designed for educational and legitimate documentation analysis purposes. Please respect target site robots.txt and terms of service when using this tool.