
import os
import streamlit as st
import datetime
from utils.report import generate_html_report, generate_pdf_report

EXPORT_DIR = "exports/"

def save_current_export(results):
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    html_path = f"{EXPORT_DIR}hornwatch_{ts}.html"
    pdf_path = f"{EXPORT_DIR}hornwatch_{ts}.pdf"
    generate_html_report(results, html_path)
    generate_pdf_report(html_path, pdf_path)
    return html_path, pdf_path

def list_archives():
    st.subheader("📦 Archive Manager")
    files = sorted(os.listdir(EXPORT_DIR), reverse=True)
    htmls = [f for f in files if f.endswith(".html")]
    pdfs = [f for f in files if f.endswith(".pdf")]

    for f in htmls:
        st.markdown(f"- 📄 [{f}](./{EXPORT_DIR}{f})")

    for f in pdfs:
        st.markdown(f"- 📕 [{f}](./{EXPORT_DIR}{f})")
