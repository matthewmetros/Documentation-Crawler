/**
 * Documentation Scraper - Main JavaScript Functionality
 */

class DocumentationScraper {
    constructor() {
        this.currentScrapingSession = null;
        this.scrapedContent = null;
        this.settings = this.loadSettings();
        
        this.init();
    }
    
    init() {
        this.initializeEventListeners();
        this.initializeTabs();
        this.loadHistory();
        this.loadSettings();
        this.checkGoogleDocsAuth();
    }
    
    initializeEventListeners() {
        // Scraper form
        document.getElementById('scraper-form').addEventListener('submit', (e) => {
            e.preventDefault();
            this.startScraping();
        });
        
        // URL validation
        document.getElementById('validate-url-btn').addEventListener('click', () => {
            this.validateUrl();
        });
        
        // URL examples
        document.querySelectorAll('.url-example').forEach(link => {
            link.addEventListener('click', (e) => {
                e.preventDefault();
                document.getElementById('url-input').value = e.target.dataset.url;
                this.validateUrl();
            });
        });
        
        // Google Docs form
        document.getElementById('google-docs-form').addEventListener('submit', (e) => {
            e.preventDefault();
            this.createGoogleDoc();
        });
        
        // Load from scraper button
        document.getElementById('load-from-scraper-btn').addEventListener('click', () => {
            this.loadContentFromScraper();
        });
        
        // Create Google Doc from results
        document.getElementById('create-google-doc-btn').addEventListener('click', () => {
            this.createGoogleDocFromResults();
        });
        
        // Download button
        document.getElementById('download-btn').addEventListener('click', () => {
            this.downloadContent();
        });
        
        // Copy document ID
        document.getElementById('copy-doc-id-btn').addEventListener('click', () => {
            this.copyDocumentId();
        });
        
        // Settings form
        document.getElementById('settings-form').addEventListener('submit', (e) => {
            e.preventDefault();
            this.saveSettings();
        });
        
        // Reset settings
        document.getElementById('reset-settings-btn').addEventListener('click', () => {
            this.resetSettings();
        });
        
        // Clear buttons
        document.getElementById('clear-all-btn').addEventListener('click', () => {
            this.clearAll();
        });
        
        document.getElementById('clear-history-btn').addEventListener('click', () => {
            this.clearHistory();
        });
        
        // Real-time URL validation
        document.getElementById('url-input').addEventListener('input', () => {
            this.debounce(this.validateUrl.bind(this), 500)();
        });
    }
    
    initializeTabs() {
        // Handle tab switching
        document.querySelectorAll('.nav-link[data-toggle="tab"]').forEach(tab => {
            tab.addEventListener('click', (e) => {
                e.preventDefault();
                this.switchTab(e.target.getAttribute('href').substring(1));
            });
        });
    }
    
    switchTab(tabId) {
        // Remove active classes
        document.querySelectorAll('.nav-link').forEach(link => {
            link.classList.remove('active');
        });
        document.querySelectorAll('.tab-pane').forEach(pane => {
            pane.classList.remove('show', 'active');
        });
        
        // Add active classes
        document.querySelector(`[href="#${tabId}"]`).classList.add('active');
        document.getElementById(tabId).classList.add('show', 'active');
    }
    
    async startScraping() {
        const form = document.getElementById('scraper-form');
        const formData = new FormData(form);
        
        const scrapingData = {
            url: document.getElementById('url-input').value,
            format: document.getElementById('format-select').value,
            max_depth: parseInt(document.getElementById('depth-input').value),
            delay: parseFloat(document.getElementById('delay-input').value),
            single_page: document.getElementById('single-page-check').checked
        };
        
        // Validate input
        if (!scrapingData.url) {
            this.showAlert('Please enter a valid URL', 'danger');
            return;
        }
        
        try {
            this.showProgress('Initializing scraper...');
            this.setFormLoading(true);
            
            // Start scraping
            const response = await fetch('/api/scrape', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(scrapingData)
            });
            
            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.error || 'Scraping failed');
            }
            
            const result = await response.json();
            
            if (result.success) {
                this.scrapedContent = result.content;
                this.displayResults(result);
                this.saveToHistory(scrapingData, result);
                this.showAlert(`Successfully scraped ${result.pages_scraped} pages!`, 'success');
            } else {
                throw new Error('Scraping failed');
            }
            
        } catch (error) {
            console.error('Scraping error:', error);
            this.showAlert(`Scraping failed: ${error.message}`, 'danger');
        } finally {
            this.hideProgress();
            this.setFormLoading(false);
        }
    }
    
    async validateUrl() {
        const urlInput = document.getElementById('url-input');
        const url = urlInput.value.trim();
        const validateBtn = document.getElementById('validate-url-btn');
        
        if (!url) {
            this.clearUrlValidation();
            return;
        }
        
        // Basic URL validation
        try {
            new URL(url);
            validateBtn.innerHTML = '<i data-feather="check-circle"></i> Valid';
            validateBtn.className = 'btn btn-outline-success';
            feather.replace();
        } catch {
            validateBtn.innerHTML = '<i data-feather="x-circle"></i> Invalid';
            validateBtn.className = 'btn btn-outline-danger';
            feather.replace();
        }
    }
    
    clearUrlValidation() {
        const validateBtn = document.getElementById('validate-url-btn');
        validateBtn.innerHTML = '<i data-feather="check-circle"></i> Validate';
        validateBtn.className = 'btn btn-outline-secondary';
        feather.replace();
    }
    
    displayResults(result) {
        const resultsContainer = document.getElementById('results-container');
        const resultsStats = document.getElementById('results-stats');
        const resultsContent = document.getElementById('results-content');
        
        // Show results container
        resultsContainer.style.display = 'block';
        resultsContainer.scrollIntoView({ behavior: 'smooth' });
        
        // Update stats
        resultsStats.innerHTML = `
            <div class="row">
                <div class="col-md-4">
                    <strong>Pages Scraped:</strong> ${result.pages_scraped}
                </div>
                <div class="col-md-4">
                    <strong>Content Length:</strong> ${this.formatBytes(result.content.length)}
                </div>
                <div class="col-md-4">
                    <strong>Format:</strong> ${document.getElementById('format-select').value.toUpperCase()}
                </div>
            </div>
        `;
        
        // Update content
        resultsContent.value = result.content;
        
        // Enable action buttons
        document.getElementById('download-btn').disabled = false;
        document.getElementById('create-google-doc-btn').disabled = false;
    }
    
    async createGoogleDoc() {
        const title = document.getElementById('doc-title-input').value.trim();
        const content = document.getElementById('doc-content-input').value.trim();
        
        if (!title || !content) {
            this.showAlert('Please provide both title and content', 'warning');
            return;
        }
        
        try {
            this.setButtonLoading('create-doc-btn', true);
            
            const response = await fetch('/api/create-google-doc', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ title, content })
            });
            
            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.error || 'Failed to create Google Doc');
            }
            
            const result = await response.json();
            
            if (result.success) {
                this.displayGoogleDocResult(result);
                this.showAlert('Google Doc created successfully!', 'success');
            } else {
                throw new Error('Failed to create document');
            }
            
        } catch (error) {
            console.error('Google Docs error:', error);
            this.showAlert(`Google Docs integration failed: ${error.message}`, 'danger');
        } finally {
            this.setButtonLoading('create-doc-btn', false);
        }
    }
    
    createGoogleDocFromResults() {
        if (!this.scrapedContent) {
            this.showAlert('No content available. Please scrape documentation first.', 'warning');
            return;
        }
        
        // Switch to Google Docs tab
        this.switchTab('google-docs');
        
        // Fill in the form
        const url = document.getElementById('url-input').value;
        const domain = new URL(url).hostname;
        document.getElementById('doc-title-input').value = `Documentation: ${domain}`;
        document.getElementById('doc-content-input').value = this.scrapedContent;
        
        // Auto-create if user confirms
        if (confirm('Create Google Doc with scraped content?')) {
            this.createGoogleDoc();
        }
    }
    
    loadContentFromScraper() {
        if (!this.scrapedContent) {
            this.showAlert('No content available. Please scrape documentation first.', 'warning');
            return;
        }
        
        document.getElementById('doc-content-input').value = this.scrapedContent;
        this.showAlert('Content loaded from scraper', 'info');
    }
    
    displayGoogleDocResult(result) {
        const resultDiv = document.getElementById('google-docs-result');
        const docLink = document.getElementById('doc-link');
        
        docLink.href = result.document_url;
        docLink.dataset.documentId = result.document_id;
        
        resultDiv.style.display = 'block';
        resultDiv.scrollIntoView({ behavior: 'smooth' });
    }
    
    downloadContent() {
        if (!this.scrapedContent) {
            this.showAlert('No content to download', 'warning');
            return;
        }
        
        const format = document.getElementById('format-select').value;
        const url = document.getElementById('url-input').value;
        const domain = new URL(url).hostname;
        
        const filename = `documentation-${domain}-${Date.now()}.${this.getFileExtension(format)}`;
        const blob = new Blob([this.scrapedContent], { type: this.getMimeType(format) });
        
        const link = document.createElement('a');
        link.href = URL.createObjectURL(blob);
        link.download = filename;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        
        this.showAlert('Content downloaded successfully', 'success');
    }
    
    copyDocumentId() {
        const docLink = document.getElementById('doc-link');
        const documentId = docLink.dataset.documentId;
        
        if (!documentId) {
            this.showAlert('No document ID available', 'warning');
            return;
        }
        
        navigator.clipboard.writeText(documentId).then(() => {
            this.showAlert('Document ID copied to clipboard', 'success');
        }).catch(() => {
            this.showAlert('Failed to copy document ID', 'danger');
        });
    }
    
    saveToHistory(scrapingData, result) {
        const history = this.getHistory();
        const historyItem = {
            id: Date.now(),
            timestamp: new Date().toISOString(),
            url: scrapingData.url,
            format: scrapingData.format,
            pages_scraped: result.pages_scraped,
            content_length: result.content.length,
            settings: { ...scrapingData }
        };
        
        history.unshift(historyItem);
        
        // Keep only last 50 items
        if (history.length > 50) {
            history.splice(50);
        }
        
        localStorage.setItem('scraper_history', JSON.stringify(history));
        this.loadHistory();
    }
    
    loadHistory() {
        const history = this.getHistory();
        const historyList = document.getElementById('history-list');
        
        if (history.length === 0) {
            historyList.innerHTML = '<p class="text-muted">No scraping history available</p>';
            return;
        }
        
        historyList.innerHTML = history.map(item => `
            <div class="history-item fade-in">
                <div class="history-item-header">
                    <div class="history-item-title">${new URL(item.url).hostname}</div>
                    <div class="history-item-date">${this.formatDate(item.timestamp)}</div>
                </div>
                <div class="history-item-url">
                    <a href="${item.url}" target="_blank">${item.url}</a>
                </div>
                <div class="history-item-stats">
                    <span class="status-indicator status-success"></span>
                    ${item.pages_scraped} pages • ${this.formatBytes(item.content_length)} • ${item.format.toUpperCase()}
                </div>
                <div class="mt-2">
                    <button class="btn btn-outline-primary btn-sm" onclick="app.restoreSession(${item.id})">
                        <i data-feather="rotate-ccw"></i> Restore Settings
                    </button>
                </div>
            </div>
        `).join('');
        
        feather.replace();
    }
    
    getHistory() {
        try {
            return JSON.parse(localStorage.getItem('scraper_history') || '[]');
        } catch {
            return [];
        }
    }
    
    clearHistory() {
        if (confirm('Are you sure you want to clear all history?')) {
            localStorage.removeItem('scraper_history');
            this.loadHistory();
            this.showAlert('History cleared', 'info');
        }
    }
    
    restoreSession(itemId) {
        const history = this.getHistory();
        const item = history.find(h => h.id === itemId);
        
        if (!item) {
            this.showAlert('History item not found', 'danger');
            return;
        }
        
        // Restore form values
        document.getElementById('url-input').value = item.url;
        document.getElementById('format-select').value = item.format;
        document.getElementById('depth-input').value = item.settings.max_depth || 3;
        document.getElementById('delay-input').value = item.settings.delay || 1.0;
        document.getElementById('single-page-check').checked = item.settings.single_page || false;
        
        // Switch to scraper tab
        this.switchTab('scraper');
        
        this.showAlert('Settings restored from history', 'success');
    }
    
    loadSettings() {
        // Load and apply saved settings
        document.getElementById('default-format').value = this.settings.defaultFormat || 'markdown';
        document.getElementById('default-depth').value = this.settings.defaultDepth || 3;
        document.getElementById('default-delay').value = this.settings.defaultDelay || 1.0;
        document.getElementById('max-pages').value = this.settings.maxPages || 100;
        document.getElementById('user-agent').value = this.settings.userAgent || this.getDefaultUserAgent();
        document.getElementById('include-patterns').value = (this.settings.includePatterns || []).join('\n');
        document.getElementById('exclude-patterns').value = (this.settings.excludePatterns || []).join('\n');
        
        // Apply to main form
        document.getElementById('format-select').value = this.settings.defaultFormat || 'markdown';
        document.getElementById('depth-input').value = this.settings.defaultDepth || 3;
        document.getElementById('delay-input').value = this.settings.defaultDelay || 1.0;
    }
    
    saveSettings() {
        this.settings = {
            defaultFormat: document.getElementById('default-format').value,
            defaultDepth: parseInt(document.getElementById('default-depth').value),
            defaultDelay: parseFloat(document.getElementById('default-delay').value),
            maxPages: parseInt(document.getElementById('max-pages').value),
            userAgent: document.getElementById('user-agent').value,
            includePatterns: document.getElementById('include-patterns').value.split('\n').filter(p => p.trim()),
            excludePatterns: document.getElementById('exclude-patterns').value.split('\n').filter(p => p.trim())
        };
        
        localStorage.setItem('scraper_settings', JSON.stringify(this.settings));
        this.loadSettings();
        this.showAlert('Settings saved successfully', 'success');
    }
    
    loadSettings() {
        try {
            const saved = localStorage.getItem('scraper_settings');
            return saved ? JSON.parse(saved) : {};
        } catch {
            return {};
        }
    }
    
    resetSettings() {
        if (confirm('Reset all settings to defaults?')) {
            localStorage.removeItem('scraper_settings');
            this.settings = {};
            this.loadSettings();
            this.showAlert('Settings reset to defaults', 'info');
        }
    }
    
    clearAll() {
        if (confirm('Clear all data including history and settings?')) {
            localStorage.clear();
            this.settings = {};
            this.scrapedContent = null;
            
            // Reset forms
            document.getElementById('scraper-form').reset();
            document.getElementById('google-docs-form').reset();
            document.getElementById('settings-form').reset();
            
            // Hide results
            document.getElementById('results-container').style.display = 'none';
            document.getElementById('google-docs-result').style.display = 'none';
            
            // Reload components
            this.loadHistory();
            this.loadSettings();
            
            this.showAlert('All data cleared', 'info');
        }
    }
    
    async checkGoogleDocsAuth() {
        // This would check if Google Docs authentication is available
        // For now, we'll just show a placeholder message
        try {
            const response = await fetch('/api/google-docs/status');
            if (response.ok) {
                const status = await response.json();
                if (!status.authenticated) {
                    this.showAuthenticationNotice();
                }
            }
        } catch {
            // Authentication check failed - show setup instructions
            this.showAuthenticationNotice();
        }
    }
    
    showAuthenticationNotice() {
        const notice = document.createElement('div');
        notice.className = 'alert alert-info';
        notice.innerHTML = `
            <h6><i data-feather="info"></i> Google Docs Setup Required</h6>
            <p class="mb-2">To use Google Docs integration, you need to set up API credentials.</p>
            <p class="mb-0">See the README for detailed setup instructions.</p>
        `;
        
        const container = document.getElementById('alerts-container');
        container.appendChild(notice);
        feather.replace();
    }
    
    // Utility methods
    showProgress(message = 'Processing...') {
        const progressContainer = document.getElementById('progress-container');
        const progressText = document.getElementById('progress-text');
        
        progressText.textContent = message;
        progressContainer.style.display = 'block';
    }
    
    hideProgress() {
        const progressContainer = document.getElementById('progress-container');
        progressContainer.style.display = 'none';
    }
    
    setFormLoading(loading) {
        const form = document.getElementById('scraper-form');
        const submitBtn = document.getElementById('scrape-btn');
        
        if (loading) {
            form.classList.add('loading');
            submitBtn.disabled = true;
            submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm"></span> Scraping...';
        } else {
            form.classList.remove('loading');
            submitBtn.disabled = false;
            submitBtn.innerHTML = '<i data-feather="download"></i> Start Scraping';
            feather.replace();
        }
    }
    
    setButtonLoading(buttonId, loading) {
        const button = document.getElementById(buttonId);
        const originalText = button.dataset.originalText || button.innerHTML;
        
        if (loading) {
            button.dataset.originalText = originalText;
            button.disabled = true;
            button.innerHTML = '<span class="spinner-border spinner-border-sm"></span> Processing...';
        } else {
            button.disabled = false;
            button.innerHTML = originalText;
            feather.replace();
        }
    }
    
    showAlert(message, type = 'info') {
        const alertsContainer = document.getElementById('alerts-container');
        const alert = document.createElement('div');
        alert.className = `alert alert-${type} alert-dismissible fade show`;
        alert.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        
        alertsContainer.appendChild(alert);
        
        // Auto-dismiss after 5 seconds
        setTimeout(() => {
            if (alert.parentNode) {
                alert.remove();
            }
        }, 5000);
    }
    
    debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }
    
    formatBytes(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }
    
    formatDate(dateString) {
        const date = new Date(dateString);
        return date.toLocaleDateString() + ' ' + date.toLocaleTimeString();
    }
    
    getFileExtension(format) {
        const extensions = {
            'markdown': 'md',
            'html': 'html',
            'text': 'txt'
        };
        return extensions[format] || 'txt';
    }
    
    getMimeType(format) {
        const mimeTypes = {
            'markdown': 'text/markdown',
            'html': 'text/html',
            'text': 'text/plain'
        };
        return mimeTypes[format] || 'text/plain';
    }
    
    getDefaultUserAgent() {
        return 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 DocumentationScraper/1.0';
    }
}

// Initialize the application
let app;
document.addEventListener('DOMContentLoaded', () => {
    app = new DocumentationScraper();
});

// Export for global access
window.DocumentationScraper = DocumentationScraper;
