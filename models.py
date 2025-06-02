from app import db
from datetime import datetime
import json

class SearchResult(db.Model):
    """Model to store search results for caching and export functionality"""
    id = db.Column(db.Integer, primary_key=True)
    search_type = db.Column(db.String(20), nullable=False)  # 'username' or 'keyword'
    search_query = db.Column(db.String(255), nullable=False)
    platform = db.Column(db.String(50), nullable=False)
    result_data = db.Column(db.Text)  # JSON string of scraped data
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), default='success')  # success, error, not_found
    
    def set_result_data(self, data):
        """Store result data as JSON string"""
        self.result_data = json.dumps(data)
    
    def get_result_data(self):
        """Retrieve result data as Python object"""
        if self.result_data:
            return json.loads(self.result_data)
        return {}
    
    def __repr__(self):
        return f'<SearchResult {self.search_type}:{self.search_query}:{self.platform}>'

class ScrapingSession(db.Model):
    """Model to track scraping sessions and rate limiting"""
    id = db.Column(db.Integer, primary_key=True)
    platform = db.Column(db.String(50), nullable=False)
    last_request = db.Column(db.DateTime, default=datetime.utcnow)
    request_count = db.Column(db.Integer, default=0)
    session_start = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<ScrapingSession {self.platform}:{self.request_count}>'
