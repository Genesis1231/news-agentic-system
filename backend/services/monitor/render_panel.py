from config import logger
import streamlit as st
from redis import Redis
from .styles import STAGES
from .render_data import fetch_news_data, generate_sample_news


def render_panel(redis_client: Redis, logout_callback=None) -> None:
    """Set up the sidebar with filters and controls"""

    with st.sidebar:
        st.title("Burst Newsroom")

        # Search box
        st.session_state.search_query = st.text_input("Search", "", placeholder="Search headlines...")
        
        st.divider()
        
        # Status filter
        st.session_state.status_filter = st.multiselect(
            label="Status", 
            options=STAGES, 
            default=[],
            accept_new_options=False,
            placeholder="Select status..."
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
            placeholder="Select sources..."
        ) 
        
        # Sort options
        st.session_state.sort_by = st.selectbox("Sort By", ["Newest First", "Oldest First"])
        
        st.divider()
        
        # Refresh button at bottom of sidebar
        if st.button("⟳ Refresh Data", use_container_width=True, key='sidebar_refresh', type='primary'):
            # Clear cache to force refresh
            st.cache_data.clear()
            try:
                # Try to fetch real data from Redis
                st.session_state.news_data = fetch_news_data(redis_client)
                
                # If no data found, use sample data
                if st.session_state.news_data.empty:
                    st.session_state.news_data = generate_sample_news(30)
                    
            except Exception as e:
                logger.error(f"Error refreshing news data: {str(e)}")
                st.session_state.news_data = generate_sample_news(30)
                
            st.session_state.selected_news = None
            st.rerun()
            
        # Logout button
        if st.button("← Logout", width="stretch", key='logout_button', type='tertiary'):
            if logout_callback:
                logout_callback()
            else:
                st.session_state.authenticated = False
                logger.debug("Logout function failed, forced logout.")
                st.rerun()

