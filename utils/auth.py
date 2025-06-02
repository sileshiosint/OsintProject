import streamlit as st

def login():
    st.sidebar.title("🔐 Analyst Login")
    username = st.sidebar.text_input("Username")
    password = st.sidebar.text_input("Password", type="password")
    if st.sidebar.button("Login"):
        if username == "admin" and password == "hornwatch123":
            st.session_state["logged_in"] = True
            st.success("✅ Login successful!")
            st.rerun()
        else:
            st.error("❌ Invalid credentials")

def require_login():
    if "logged_in" not in st.session_state or not st.session_state["logged_in"]:
        login()
        st.stop()
