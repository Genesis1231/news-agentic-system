import streamlit as st

def apply_dashboard_style() -> None:
    """Apply refined dark theme styling to the Streamlit dashboard"""
    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=DM+Sans:ital,opsz,wght@0,9..40,300;0,9..40,400;0,9..40,500;0,9..40,600;0,9..40,700;1,9..40,400&family=DM+Mono:wght@400;500&display=swap');

        :root {
            --bg-base: #0c0e12;
            --bg-surface: #13161c;
            --bg-elevated: #1a1e27;
            --bg-hover: #222835;
            --border-subtle: rgba(255, 255, 255, 0.06);
            --border-default: rgba(255, 255, 255, 0.1);
            --text-primary: #e8eaed;
            --text-secondary: #8b919a;
            --text-muted: #5a6069;
            --accent: #d4a843;
            --accent-dim: rgba(212, 168, 67, 0.15);
            --radius-sm: 6px;
            --radius-md: 10px;
            --radius-lg: 14px;
        }

        /* ── Base ──────────────────────────────────── */
        .main, .stApp, [data-testid="stAppViewContainer"] {
            background-color: var(--bg-base) !important;
            font-family: 'DM Sans', -apple-system, sans-serif !important;
            color: var(--text-primary);
        }

        header[data-testid="stHeader"] {
            background-color: var(--bg-base) !important;
        }

        /* ── Sidebar ───────────────────────────────── */
        section[data-testid="stSidebar"] {
            background-color: var(--bg-surface) !important;
            border-right: 1px solid var(--border-subtle) !important;
        }

        section[data-testid="stSidebar"] .stMarkdown h1 {
            font-family: 'DM Sans', sans-serif !important;
            font-weight: 700 !important;
            letter-spacing: -0.03em;
            color: var(--accent) !important;
            font-size: 1.4rem !important;
        }

        /* ── Typography ────────────────────────────── */
        h1, h2, h3, .stMarkdown h1, .stMarkdown h2, .stMarkdown h3 {
            font-family: 'DM Sans', sans-serif !important;
            font-weight: 600 !important;
            letter-spacing: -0.02em;
            color: var(--text-primary) !important;
        }

        p, label, .stMarkdown p {
            font-family: 'DM Sans', sans-serif !important;
            color: var(--text-primary);
        }

        /* ── Inputs ────────────────────────────────── */
        .stTextInput input {
            background-color: var(--bg-elevated) !important;
            border: 1px solid var(--border-default) !important;
            border-radius: var(--radius-sm) !important;
            color: var(--text-primary) !important;
            font-family: 'DM Sans', sans-serif !important;
            transition: border-color 0.2s ease;
        }

        .stTextInput input:focus {
            border-color: var(--accent) !important;
            box-shadow: 0 0 0 1px var(--accent-dim) !important;
        }

        /* ── Selects / Multiselect ─────────────────── */
        div[data-baseweb="select"] {
            cursor: pointer !important;
            background-color: var(--bg-elevated) !important;
            border: 1px solid var(--border-default) !important;
            border-radius: var(--radius-sm) !important;
        }
        div[data-baseweb="select"] * {
            cursor: pointer !important;
            font-family: 'DM Sans', sans-serif !important;
        }
        div[data-baseweb="select"] input {
            cursor: text !important;
        }
        div[data-baseweb="popover"] li {
            background-color: var(--bg-surface) !important;
            color: var(--text-primary) !important;
            font-family: 'DM Sans', sans-serif !important;
        }
        div[data-baseweb="popover"] li:hover {
            background-color: var(--bg-hover) !important;
        }

        /* ── Tabs ──────────────────────────────────── */
        .stTabs [data-baseweb="tab-list"] {
            gap: 4px;
            border-bottom: 1px solid var(--border-subtle);
        }
        .stTabs [data-baseweb="tab"] {
            padding: 10px 20px;
            border-radius: var(--radius-sm) var(--radius-sm) 0 0;
            font-family: 'DM Sans', sans-serif !important;
            font-weight: 500;
            color: var(--text-secondary);
            transition: all 0.2s ease;
        }
        .stTabs [aria-selected="true"] {
            background-color: var(--bg-elevated) !important;
            color: var(--accent) !important;
            border-bottom: 2px solid var(--accent);
        }

        /* ── Buttons ───────────────────────────────── */
        .stButton button[kind="primary"] {
            background-color: #c0392b !important;
            color: #ffffff !important;
            border: none !important;
            font-family: 'DM Sans', sans-serif !important;
            font-weight: 600 !important;
            border-radius: var(--radius-sm) !important;
            transition: all 0.2s ease;
        }
        .stButton button[kind="primary"]:hover {
            background-color: #e74c3c !important;
            transform: translateY(-1px);
        }

        .stButton button[kind="secondary"] {
            border: none !important;
            color: #ffffff !important;
            background-color: #2980b9 !important;
            font-family: 'DM Sans', sans-serif !important;
            font-weight: 500 !important;
            border-radius: var(--radius-sm) !important;
            transition: all 0.2s ease;
        }
        .stButton button[kind="secondary"]:hover {
            background-color: #3498db !important;
        }

        .stButton button[kind="tertiary"] {
            color: var(--text-secondary) !important;
            font-family: 'DM Sans', sans-serif !important;
            transition: color 0.2s ease;
        }
        .stButton button[kind="tertiary"]:hover {
            color: var(--text-primary) !important;
        }

        /* ── Metrics ───────────────────────────────── */
        [data-testid="stMetric"] {
            background-color: var(--bg-surface) !important;
            border: 1px solid var(--border-subtle) !important;
            border-radius: var(--radius-md) !important;
            padding: 16px !important;
        }
        [data-testid="stMetricLabel"] {
            color: var(--text-secondary) !important;
            font-family: 'DM Sans', sans-serif !important;
            font-size: 0.8rem !important;
            text-transform: uppercase;
            letter-spacing: 0.06em;
        }
        [data-testid="stMetricValue"] {
            color: var(--text-primary) !important;
            font-family: 'DM Sans', sans-serif !important;
            font-weight: 600 !important;
        }

        /* ── Expanders ─────────────────────────────── */
        .streamlit-expanderHeader {
            background-color: var(--bg-surface) !important;
            border: 1px solid var(--border-subtle) !important;
            border-radius: var(--radius-md) !important;
            font-family: 'DM Sans', sans-serif !important;
        }
        details[data-testid="stExpander"] {
            border: 1px solid var(--border-subtle) !important;
            border-radius: var(--radius-md) !important;
            background-color: var(--bg-surface) !important;
        }

        /* ── Dividers ──────────────────────────────── */
        hr {
            border-color: var(--border-subtle) !important;
            margin: 1.5rem 0 !important;
        }

        /* ── Containers ──────────────────────────── */
        [data-testid="stVerticalBlock"] > div[data-testid="stVerticalBlockBorderWrapper"] {
            border-color: var(--border-subtle) !important;
            border-radius: var(--radius-md) !important;
        }

        /* ── Code blocks ───────────────────────────── */
        .stCodeBlock, code {
            font-family: 'DM Mono', 'Fira Code', monospace !important;
            background-color: var(--bg-surface) !important;
            border-radius: var(--radius-sm) !important;
        }

        /* ── Altair chart ──────────────────────────── */
        .vega-embed .vega-actions a {
            color: var(--text-secondary) !important;
        }

        /* ── Scrollbar ─────────────────────────────── */
        ::-webkit-scrollbar {
            width: 6px;
            height: 6px;
        }
        ::-webkit-scrollbar-track {
            background: var(--bg-base);
        }
        ::-webkit-scrollbar-thumb {
            background: var(--bg-hover);
            border-radius: 3px;
        }
        ::-webkit-scrollbar-thumb:hover {
            background: var(--text-muted);
        }
    </style>
    """, unsafe_allow_html=True)

# Status colors — refined palette
STATUS_COLORS = {
    "aggregated": "#4a9eed",   # Cool blue
    "processing": "#e5a00d",   # Warm amber
    "production": "#e07850",   # Coral
    "published": "#3ddc84",    # Mint green
    "failed": "#e55d5d"        # Soft red
}

STAGES = ["aggregated", "processing", "production", "published", "failed"]
