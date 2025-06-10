import pytest
import json
from unittest.mock import patch
from models import SearchResult # Assuming SearchResult is used in mocks

def test_index_route(client):
    """Test the home page (index route)."""
    response = client.get('/')
    assert response.status_code == 200
    # Check for content from index.html and base.html (title)
    assert b"Facebook OSINT Search Tool" in response.data # From H1 tag in index.html
    assert b"Search - Facebook OSINT Search Tool" in response.data # From title block in index.html
    assert b"Username" in response.data # From form label
    assert b"Keyword or Phrase" in response.data # From form label

def test_search_route_post_valid(client):
    """Test the /search route with valid POST data."""
    response = client.post('/search', data={
        'search_query': 'testquery',
        'search_type': 'keyword' # Platforms field removed
    }, follow_redirects=True)

    assert response.status_code == 200
    # This route renders results.html.
    # The results.html page then makes an API call to /api/execute_search.
    # For this test, we are only checking if the initial results.html template is rendered.
    assert b"Results for: testquery (keyword)" in response.data
    # Check if platform names are passed to the template context correctly
    assert b"const platforms = [\"Facebook\"];" in response.data

def test_search_route_post_invalid_query(client):
    """Test the /search route with missing search_query."""
    response = client.post('/search', data={
        'search_query': '', # Empty query
        'search_type': 'keyword' # Platforms field removed
    }, follow_redirects=True)

    assert response.status_code == 200 # Should redirect to index
    # Check for the flash message that should be displayed on the index page
    assert b"Please enter a search query." in response.data
    # Verify it's back on the index page
    assert b"Facebook OSINT Search Tool" in response.data # From H1 tag
    assert b"Search - Facebook OSINT Search Tool" in response.data # From title

def test_search_route_post_valid_query_no_platforms_field(client): # Renamed and updated
    """Test the /search route with a valid query but (now redundantly) no platforms field in POST."""
    response = client.post('/search', data={
        'search_query': 'testquery',
        'search_type': 'keyword'
        # No 'platforms' key in data, which is fine now
    }, follow_redirects=True)

    assert response.status_code == 200 # Should proceed to results page
    assert b"Results for: testquery (keyword)" in response.data # On results page
    assert b"const platforms = [\"Facebook\"];" in response.data # Hardcoded to Facebook

@patch('routes.run_scraper') # Mock run_scraper in routes.py
def test_api_execute_search_valid(mock_run_scraper, client, db): # Added db fixture
    mock_run_scraper.return_value = [{
        "platform": "Facebook",
        "query": "testapi",
        "search_type": "keyword",
        "status": "success",
        "results": [{"text": "Facebook result 1"}],
        "html": "<html></html>",
        "screenshot": "fb_test.png",
        "status_detail": "Mock success"
    }]

    # Simulate that run_scraper has populated the database
    # by manually adding a SearchResult object that the route would find.
    # This is important because execute_search tries to read from DB after run_scraper.
    with client.application.app_context():
        db.session.add(SearchResult(
            search_query='testapi',
            search_type='keyword',
            platform='Facebook', # Default is Facebook, but explicit for clarity
            status='success',
            result_data=json.dumps([{"text": "Facebook result 1"}]) # Stored as JSON string
        ))
        db.session.commit()

    response = client.post('/api/execute_search', json={
        'search_query': 'testapi',
        'search_type': 'keyword',
        'platforms': ['Facebook'] # results.html will send this
    })

    assert response.status_code == 200
    mock_run_scraper.assert_called_once_with('testapi', 'keyword', ['Facebook'])

    data = json.loads(response.data)
    # API now returns a single object, not a list under "results"
    assert data['platform'] == "Facebook"
    assert data['query'] == "testapi"
    assert data['status'] == "success"
    assert isinstance(data['data'], list) # 'data' contains the 'results' from SearchResult.get_result_data()
    assert data['data'][0]['text'] == "Facebook result 1"
    # The screenshot path is taken from the direct output of run_scraper in the route
    assert data['screenshot_path'] == "fb_test.png"
