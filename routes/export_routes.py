
from flask import Blueprint, request, send_file, jsonify
from utils.export_utils import export_to_json, export_to_csv
import os
import tempfile

export_bp = Blueprint("export", __name__)

@export_bp.route("/api/export", methods=["POST"])
def export_results():
    data = request.json
    results = data.get("results")
    filetype = data.get("filetype", "json")
    filename = data.get("filename", "osint_export")

    if not results:
        return jsonify({ "error": "No results to export" }), 400

    try:
        if filetype == "csv":
            path = export_to_csv(results, filename)
        else:
            path = export_to_json(results, filename)
        return send_file(path, as_attachment=True)
    except Exception as e:
        return jsonify({ "error": str(e) }), 500
