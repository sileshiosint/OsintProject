
import os
import pdfkit
import pandas as pd
from jinja2 import Environment, FileSystemLoader

def generate_html_report(data, out_path="exports/report.html"):
    env = Environment(loader=FileSystemLoader("utils/templates"))
    template = env.get_template("report_template.html")
    html_out = template.render(results=data)
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html_out)
    return out_path

def generate_pdf_report(html_path, out_path="exports/report.pdf"):
    pdfkit.from_file(html_path, out_path)
    return out_path
