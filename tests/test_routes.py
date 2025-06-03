import pytest

def test_index_route(client):
    """Test the home page (index route)."""
    response = client.get('/')
    assert response.status_code == 200
    # Check for content from index.html and base.html (title)
    assert b"Social Media OSINT Tool" in response.data # From H1 tag in index.html
    assert b"Search - Social Media OSINT Tool" in response.data # From title block in index.html
    assert b"Username" in response.data # From form label
    assert b"Keyword or Phrase" in response.data # From form label

def test_search_route_post_valid(client):
    """Test the /search route with valid POST data."""
    response = client.post('/search', data={
        'search_query': 'testquery',
        'search_type': 'keyword', # Assuming 'keyword' is a valid search_type
        'platforms': ['Twitter', 'Facebook']
    }, follow_redirects=True) # follow_redirects is important if this route redirects

    assert response.status_code == 200
    # This route renders results.html.
    # The results.html page then makes an API call to /api/execute_search.
    # For this test, we are only checking if the initial results.html template is rendered.
    assert b"Results for: testquery (keyword)" in response.data
    # Check if platform names are passed to the template context correctly
    # (The template itself might format this differently)
    assert b"const platforms = [\"Twitter\", \"Facebook\"];" in response.data

def test_search_route_post_invalid_query(client):
    """Test the /search route with missing search_query."""
    response = client.post('/search', data={
        'search_query': '', # Empty query
        'search_type': 'keyword',
        'platforms': ['Twitter']
    }, follow_redirects=True)

    assert response.status_code == 200 # Should redirect to index
    # Check for the flash message that should be displayed on the index page
    assert b"Please enter a search query and select at least one platform." in response.data
    # Verify it's back on the index page
    assert b"Social Media OSINT Tool" in response.data # From H1 tag
    assert b"Search - Social Media OSINT Tool" in response.data # From title

def test_search_route_post_invalid_platform(client):
    """Test the /search route with missing platforms."""
    response = client.post('/search', data={
        'search_query': 'testquery',
        'search_type': 'keyword',
        # 'platforms': [] # No platforms selected - form submission won't include 'platforms' if none checked
    }, follow_redirects=True)

    assert response.status_code == 200 # Should redirect to index
    assert b"Please enter a search query and select at least one platform." in response.data
    assert b"Social Media OSINT Tool" in response.data # Back on index H1
    assert b"Search - Social Media OSINT Tool" in response.data # Back on index title
