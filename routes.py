
from flask import request, jsonify, render_template, redirect, url_for, flash
from app import app
import asyncio
from scraper import run_scraper

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/search', methods=['POST'])
def search():
    search_query = request.form.get('search_query')
    search_type = request.form.get('search_type')
    selected_platforms = request.form.getlist('platforms')

    if not search_query or not selected_platforms:
        flash('Please enter a search query and select at least one platform.')
        return redirect(url_for('index'))

    return render_template('results.html', search_query=search_query,
                           search_type=search_type, platforms=selected_platforms)

@app.route('/api/execute_search', methods=['POST'])
def execute_search():
    data = request.get_json()
    search_query = data.get('search_query')
    search_type = data.get('search_type')
    selected_platforms = data.get('platforms')

    if not search_query or not selected_platforms:
        return jsonify({"error": "Invalid input"}), 400

    results = asyncio.run(run_scraper(search_query, search_type, selected_platforms))
    return jsonify({"results": results})
