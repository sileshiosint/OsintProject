from utils.auth import require_login
import streamlit as st
import pandas as pd
import os

require_login()

st.set_page_config(page_title="OSINT Dashboard", layout="wide")

st.title("🛰️ Social Media OSINT Dashboard")

# Select CSV file from exports
export_dir = "exports"
if not os.path.exists(export_dir):
    os.makedirs(export_dir)

files = [f for f in os.listdir(export_dir) if f.endswith(".csv")]

if not files:
    st.warning("No exported files found in the 'exports' directory.")
else:
    selected_file = st.selectbox("Select a dataset to view", files)
    df = pd.read_csv(os.path.join(export_dir, selected_file))

    # Ensure numeric columns are correct type
    if "sentiment" in df.columns:
        df["sentiment"] = pd.to_numeric(df["sentiment"], errors="coerce")
    if "toxicity" in df.columns:
        df["toxicity"] = pd.to_numeric(df["toxicity"], errors="coerce")

    # Filters
    col1, col2 = st.columns(2)
    with col1:
        sentiment_range = st.slider("Sentiment Range", -1.0, 1.0, (-1.0, 1.0))
    with col2:
        min_toxicity = st.slider("Minimum Toxicity", 0.0, 1.0, 0.0)

    filtered_df = df[
        (df["sentiment"].fillna(0).between(*sentiment_range)) &
        (df["toxicity"].fillna(0) >= min_toxicity if "toxicity" in df.columns else True)
    ]

    # Show topic distribution
    if "topic" in df.columns:
        st.subheader("📊 Topic Distribution")
        topic_counts = filtered_df["topic"].value_counts()
        st.bar_chart(topic_counts)

        selected_topic = st.selectbox("Filter by topic", ["All"] + list(topic_counts.index))
        if selected_topic != "All":
            filtered_df = filtered_df[filtered_df["topic"] == selected_topic]

    st.markdown(f"### Showing {len(filtered_df)} of {len(df)} results")
    st.dataframe(filtered_df, use_container_width=True)

    # Show top named entities
    if "entities" in df.columns:
        st.subheader("📌 Named Entities")
        all_entities = filtered_df["entities"].dropna().str.cat(sep=", ").split(", ")
        entity_counts = pd.Series(all_entities).value_counts().head(20)
        st.bar_chart(entity_counts)
