from config import logger, configuration
import streamlit as st
from redis import Redis, ConnectionPool

from backend.core.database import DataInterface
from .styles import apply_dashboard_style
from .render_data import fetch_news_data, fetch_news_logs, filter_news_dataframe, generate_sample_news
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

        # # Check authentication first
        # if not self.login():
        #     return

        # Fetch initial data
        try:
            news_data = fetch_news_data(self.database)

            if not news_data.empty:
                st.session_state.news_data = news_data
                logger.debug(f"Fetched {len(news_data)} news items.")
            elif 'news_data' not in st.session_state:
                st.session_state.news_data = generate_sample_news(30)
                st.info("No news items found. Showing sample data for preview.")

        except Exception as e:
            logger.error(f"Error fetching data: {e}")
            if 'news_data' not in st.session_state:
                st.session_state.news_data = generate_sample_news(3)
                st.error(f"Could not connect to the database — check that PostgreSQL is running. Showing sample data for now.")

        # render sidebar and main content
        self.render_newsroom()
               
    def initialize(self) -> None:
        """Set up initial dashboard state and configuration"""

        # Set page title and layout
        st.set_page_config(
            page_title="BURST Newsroom",
            layout="wide",
            initial_sidebar_state="expanded"
        )

        # Apply dashboard style
        apply_dashboard_style()
        
        # Initialize session state variables (only if not already set)
        defaults = {
            'selected_news': None,
            'search_query': "",
            'status_filter': [],
            'source_filter': [],
            'sort_by': "Newest First"
        }

        for key, value in defaults.items():
            if key not in st.session_state:
                st.session_state[key] = value

    def login(self) -> bool:
        """Handle user authentication"""
        
        # Initialize authentication state
        if 'authenticated' not in st.session_state:
            st.session_state.authenticated = False

        if not st.session_state.authenticated:
            # Center the login form using columns
            col1, col2, col3 = st.columns([1.2, 1, 1.2])

            with col2:
                st.markdown("""
                <div style="text-align: center; margin-top: 15vh; margin-bottom: 2rem;">
                    <div style="font-family: 'DM Sans', sans-serif; font-size: 2.4rem; font-weight: 700;
                                letter-spacing: -0.04em; color: #d4a843; margin-bottom: 6px;">BURST</div>
                    <div style="font-family: 'DM Sans', sans-serif; font-size: 0.9rem; color: #8b919a;
                                letter-spacing: 0.12em; text-transform: uppercase;">Newsroom Dashboard</div>
                </div>
                """, unsafe_allow_html=True)

                with st.form("login_form"):
                    username = st.text_input("Username", key="login_username", placeholder="Enter username")
                    password = st.text_input("Password", type="password", key="login_password", placeholder="Enter password")
                    login_button = st.form_submit_button("Sign In", width="stretch", type="primary")

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
        
        render_panel(self.database, logout_callback=self.logout)

        if raw_id := st.session_state.selected_news:
            # Find the selected news item by ID
            from .render_news import render_news_detail_page

            matches = st.session_state.news_data[
                st.session_state.news_data['id'] == raw_id
            ]

            if matches.empty:
                st.session_state.selected_news = None
                st.rerun()
                return

            selected_news = matches.iloc[0]

            # Fetch logs from Redis on-demand for the detail view
            logs = fetch_news_logs(self.redis_client, raw_id)
            render_news_detail_page(selected_news, logs=logs)
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
