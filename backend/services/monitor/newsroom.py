from config import logger, configuration
import asyncio
import streamlit as st
from redis import Redis, ConnectionPool

from backend.core.database import DataInterface
from .styles import apply_dashboard_style
from .render_data import fetch_news_data, filter_news_dataframe, generate_sample_news
from .render_panel import render_panel


class Newsroom:
    """Main newsroom dashboard for visualizing news flow"""
    
    def __init__(self):
        self.redis_pool = self._get_redis_pool()
        self.redis_client = Redis(connection_pool=self.redis_pool)
        self.database = DataInterface("Dashboard")
        
        # Apply principle of readability and efficiency with minimal essential widgets
        self.initialize()

    def _get_redis_pool(self) -> ConnectionPool:
        """Get a Redis connection pool."""
        return ConnectionPool(
            host=configuration["redis"]["host"],
            port=configuration["redis"]["port"],
            db=configuration["redis"]["database"]["monitor"],
            max_connections=10,
            retry_on_timeout=True,  
            socket_timeout=5,
            socket_connect_timeout=5,
            decode_responses=True
        )

    def run(self):
        """Run the dashboard application"""

        # Check authentication first
        if not self.login():
            return

        # Fetch initial data
        try:
            news_data = fetch_news_data(self.redis_client)

            if not news_data.empty:
                st.session_state.news_data = news_data
                logger.debug(f"Fetched {len(news_data)} news items.")
            elif 'news_data' not in st.session_state:
                st.session_state.news_data = generate_sample_news(30)
                st.warning("No data in Redis. Displaying sample data.")
                
        except Exception as e:
            logger.error(f"Error fetching data: {e}")
            if 'news_data' not in st.session_state:
                st.session_state.news_data = generate_sample_news(3)
                st.error("Error fetching data. Displaying sample data.")

        # render sidebar and main content
        self.render_newsroom()
               
    def initialize(self) -> None:
        """Set up initial dashboard state and configuration"""
        
        # Apply dashboard style
        apply_dashboard_style()
        
        # Set page title and layout
        st.set_page_config(
            page_title="Newsroom Dashboard",
            layout="wide",
            initial_sidebar_state="expanded"
        )
        
        # Initialize session state variables
        defaults = {
            'selected_news': None,
            'status_filter': "All",
            'source_filter': "All",
            'sort_by': "Newest First"
        }
        
        for key, value in defaults.items():
            if key not in st.session_state:
                st.session_state[key] = value
        
        # Initialize filter values in session state
        st.session_state.search_query = ""
        st.session_state.status_filter = "All"
        st.session_state.source_filter = "All"
        st.session_state.sort_by = "Newest First"

    def login(self) -> bool:
        """Handle user authentication"""
        
        # Initialize authentication state
        if 'authenticated' not in st.session_state:
            st.session_state.authenticated = False

        if not st.session_state.authenticated:
            # Center the login form using columns
            col1, col2, col3 = st.columns([1, 1, 1])

            with col2:
                st.title("Newsroom Login")

                with st.form("login_form"):
                    username = st.text_input("Username", key="login_username")
                    password = st.text_input("Password", type="password", key="login_password")
                    login_button = st.form_submit_button("🔑 Login", width="stretch", type="primary")

                    if login_button:
                        if (username == configuration["auth"]["username"] and
                            password == configuration["auth"]["password"]):
                            st.session_state.authenticated = True
                            logger.debug(f"Newsroom Login successfully with username: {username}")
                            st.rerun()
                        else:
                            logger.error(f"Newsroom Login failed with username and password: {username} and {password}.")
                            st.error("Invalid username or password")

            return False
        
        return True

    def logout(self):
        """Handle user logout"""
        st.session_state.authenticated = False
        logger.debug("Newsroom Logout successfully.")
        st.rerun()

    def render_newsroom(self) -> None:
        """Render main content area, showing either news board or detail page."""
        
        logger.debug(f"Rendering content with selected_news={st.session_state.selected_news}")        
        
        render_panel(self.redis_client, logout_callback=self.logout)
        
        if raw_id := st.session_state.selected_news:
            # Find the selected news item by ID
            from .render_news import render_news_detail_page
            
            selected_news = st.session_state.news_data[
                st.session_state.news_data['id'] == raw_id
            ].iloc[0]
            
            # news_production = asyncio.run(self.database.get_single_news(raw_id))
            # if news_production:
            #     news_production = news_production.to_dict()
                
            render_news_detail_page(selected_news)
        else:
            # Show main news dashboard
            from .render_main import render_trend_chart, render_news_board
            
            render_trend_chart(st.session_state.news_data)
            
            filtered_data = filter_news_dataframe(
                df=st.session_state.news_data,
                search_query=st.session_state.search_query,
                status_filter=st.session_state.status_filter,
                source_filter=st.session_state.source_filter,
                sort_by=st.session_state.sort_by
            )
            
            render_news_board(filtered_data)
