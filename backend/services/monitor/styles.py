import streamlit as st

def apply_dashboard_style() -> None:
    """Apply the dark theme styling to the Streamlit dashboard"""
    st.markdown("""
    <style>
        .main {
            background-color: #1e1e1e;
            color: #f0f0f0;
        }

        .stTabs [data-baseweb="tab"] {
            padding-left: 20px;
            padding-right: 20px;
        }
        .stTabs [aria-selected="true"] {
            background-color: #000000;
        }
        /* Style search input */
        .stTextInput input {
            background-color: rgba(29, 29, 29, 0.7) !important;
            border-radius: 5px;
            border: 1px solid rgba(250, 250, 250, 0.2) !important;
        }
        
        /* Add hand cursor and style for multiselect elements */
        div[data-baseweb="select"] {
            cursor: pointer !important;
            background-color: #2d2d2d !important;
            border: 1px solid rgba(250, 250, 250, 0.2) !important;
            border-radius: 5px !important;
        }
        div[data-baseweb="select"] * {
            cursor: pointer !important;
        }
        div[data-baseweb="select"] input {
            cursor: text !important;
        }
        /* Style multiselect dropdown menu items */
        div[data-baseweb="popover"] li {
            background-color: #101010 !important; /* Use main dark background */
            color: #f0f0f0 !important;
        }
        div[data-baseweb="popover"] li:hover {
            background-color: #2d2d2d !important;  
        }
        /* Style for secondary buttons */
        .stButton button[kind="secondary"] {
            border-color: #3498db !important;
            color: #ffffff !important;
            background-color: #3498db !important;
            transition: all 0.3s ease;
        }
        .stButton button[kind="secondary"]:hover {
            background-color: rgba(52, 152, 219, 0.2) !important;
        }
        .news-card {
            background-color: #2d2d2d;
            border-radius: 8px;
            padding: 15px;
            margin-bottom: 10px;
            overflow: hidden;
            word-wrap: break-word;
        }
        .status-indicator {
            height: 10px;
            border-radius: 5px;
            margin-top: 5px;
        }
        .news-title {
            font-weight: bold;
            font-size: 1.1em;
            margin-bottom: 5px;
        }
        .news-meta {
            font-size: 0.85em;
            color: #aaaaaa;
        }
    </style>
    """, unsafe_allow_html=True)

# Status colors and stages
STATUS_COLORS = {
    "aggregated": "#3498db",   # Blue
    "processing": "#f39c12",   # Orange
    "production": "#e74c3c",   # Red
    "published": "#2ecc71",    # Green
    "failed": "#c0392b"         # Dark red
}

STAGES = ["aggregated", "processing", "production", "published", "failed"]