from config import logger
import streamlit as st
from .styles import STAGES
from .render_data import fetch_news_data, generate_sample_news

from backend.core.database import DataInterface


def render_panel(database: DataInterface, logout_callback=None) -> None:
    """Set up the sidebar with filters and controls"""

    with st.sidebar:
        # Branding header
        st.markdown("""
        <div style="padding: 8px 0 20px 0; border-bottom: 1px solid rgba(255,255,255,0.06); margin-bottom: 20px;">
            <div style="font-family: 'DM Sans', sans-serif; font-size: 1.5rem; font-weight: 700;
                        letter-spacing: -0.04em; color: #d4a843;">BURST</div>
            <div style="font-family: 'DM Sans', sans-serif; font-size: 0.7rem; color: #5a6069;
                        letter-spacing: 0.1em; text-transform: uppercase; margin-top: 2px;">Newsroom</div>
        </div>
        """, unsafe_allow_html=True)

        # Search box
        st.session_state.search_query = st.text_input("Search", "", placeholder="Search headlines...", label_visibility="collapsed")

        # Status filter
        st.session_state.status_filter = st.multiselect(
            label="Status",
            options=STAGES,
            default=[],
            accept_new_options=False,
            placeholder="Filter by status..."
        )

        # Source filter
        source_options = []
        if not st.session_state.news_data.empty and 'source' in st.session_state.news_data.columns:
            source_options = st.session_state.news_data['source'].unique()

        st.session_state.source_filter = st.multiselect(
            label="Source",
            options=source_options,
            default=[],
            accept_new_options=False,
            placeholder="Filter by source..."
        )

        # Sort options
        st.session_state.sort_by = st.selectbox("Sort", ["Newest First", "Oldest First"], label_visibility="collapsed")

        # Spacer
        st.markdown("<div style='margin-top: 1.5rem;'></div>", unsafe_allow_html=True)

        # Refresh button
        if st.button("Refresh Data", width='stretch', key='sidebar_refresh', type='primary'):
            st.cache_data.clear()
            try:
                st.session_state.news_data = fetch_news_data(database)
                if st.session_state.news_data.empty:
                    st.session_state.news_data = generate_sample_news(30)
            except Exception as e:
                logger.error(f"Error refreshing news data: {str(e)}")
                st.session_state.news_data = generate_sample_news(30)

            st.session_state.selected_news = None
            st.rerun()

        # Logout button
        if st.button("Sign Out", width="stretch", key='logout_button', type='tertiary'):
            if logout_callback:
                logout_callback()
            else:
                st.session_state.authenticated = False
                logger.debug("Logout function failed, forced logout.")
                st.rerun()
