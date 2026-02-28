import streamlit as st
import pandas as pd
from datetime import datetime, timezone, timedelta
import altair as alt


def render_news_board(news_data: pd.DataFrame) -> None:
    """Render the main news board with metrics and cards"""

    if news_data.empty:
        st.info("No news items found matching your criteria")
        return

    # Display metrics section
    with st.container():
        render_metrics_section(news_data)

    st.divider()
    st.header("News Items", anchor=False)

    # Pagination setup
    # Initialize pagination state if not already set
    if 'page' not in st.session_state:
        st.session_state.page = 1
    if 'items_per_page' not in st.session_state:
        st.session_state.items_per_page = 30

    # Calculate pagination
    total_items = len(news_data)
    items_per_page = st.session_state.items_per_page
    total_pages = (total_items + items_per_page - 1) // items_per_page  # Ceiling division

    # Ensure current page is valid
    if st.session_state.page > total_pages:
        st.session_state.page = total_pages if total_pages > 0 else 1

    # Get data for current page
    start_idx = (st.session_state.page - 1) * items_per_page
    end_idx = start_idx + items_per_page
    page_data = news_data.iloc[start_idx:end_idx]

    # Display news cards in a grid
    cols = st.columns(3)
    for i, (_, news) in enumerate(page_data.iterrows()):
        with cols[i % 3]:
            render_news_card(news, str(news.get('id', f'unknown_{i}')))

    st.divider()
    
    # Pagination controls
    items_per_page_options = [30, 60, 120]
    col1, col2, col3, col4 = st.columns([7, 1, 1, 1])

    with col1:
        st.markdown(f"<div style='vertical-align: middle;'>Page {st.session_state.page} of {total_pages}</div>", unsafe_allow_html=True)
          
    if total_pages > 1:
        with col2:
            # Previous button with custom blue styling
            if st.session_state.page > 1:
                if st.button("Previous Page", width=100, key="prev_page", type="tertiary"):
                    st.session_state.page -= 1
                    st.rerun()
        with col3:
            # Next button with custom blue styling
            if st.session_state.page < total_pages:
                if st.button("Next Page", width=100, key="next_page", type="tertiary"):
                    st.session_state.page += 1
                    st.rerun()
                    
    with col4:
        
        selected_items_per_page = st.selectbox(
            "Items per page:",
            options=items_per_page_options,
            index=items_per_page_options.index(st.session_state.items_per_page),
            key="items_per_page_selector",
            label_visibility="collapsed"
        )

    # Update items per page if changed
    if selected_items_per_page != st.session_state.items_per_page:
        st.session_state.items_per_page = selected_items_per_page
        st.session_state.page = 1  # Reset to first page
        st.rerun()
        


def render_trend_chart(news_data: pd.DataFrame) -> None:
    """Render a line chart showing hourly news processing trend"""

    if news_data.empty:
        st.info("No news items found.")
        return
    
    # Process hourly trends data using the utility function
    hourly_counts = process_hourly_trend_data(news_data)
    
    # Create the chart using the visualization function
    chart = create_trend_chart(
        df=hourly_counts,
        time_column='hour',
        value_column='count',
        title='News Trend (Past 24 Hours)',
        height=400
    )

    if chart:
        st.altair_chart(chart, width='stretch')


def render_metrics_section(filtered_data: pd.DataFrame) -> None:
    """Render metrics section with key statistics"""
    
    if filtered_data.empty:
        st.info("No news items found matching your criteria")
        return
    
    metrics_cols = st.columns(4)

    with metrics_cols[0]:
        # Display total news count
        total_news = len(filtered_data)
        st.metric(label="Total News Items", value=total_news)
     
    with metrics_cols[1]:
        # Display news items in last hour
        now = datetime.now(timezone.utc)
        hour_ago = now - timedelta(hours=1)
        
        if 'timestamp' in filtered_data.columns:
            recent_count = len(filtered_data[filtered_data['timestamp'] >= hour_ago])
        else:
            recent_count = 0
            
        st.metric(label="Last Hour", value=recent_count)        

    with metrics_cols[2]:
        # Display published news count
        published_count = len(filtered_data[filtered_data['status'] == 'published']) if 'status' in filtered_data.columns else 0
        st.metric(label="Total Published", value=published_count)
       
    with metrics_cols[3]:
        # Display top source
        if 'source' in filtered_data.columns and not filtered_data.empty:
            top_source = filtered_data['source'].value_counts().idxmax()
            top_source_count = filtered_data['source'].value_counts().max()
        else:
            top_source = "N/A"
            top_source_count = 0
        
        st.metric(label="Top Source", value=f"{top_source.capitalize()} ({top_source_count})")

def render_news_card(news: pd.Series, card_id: str) -> None:
    """Render a single news card """

    # Get status and its color
    status = news.get('status')
    news_id = news.get('id')
    source = news.get('source', 'Unknown')
    author = news.get('author', 'Unknown')

    # Calculate time display
    timestamp = news.get('timestamp')
    seconds = (datetime.now(timezone.utc) - timestamp).total_seconds()

    # Format the time difference
    time_str = (
        f"{int(seconds)}s ago" if seconds < 60 else
        f"{int(seconds // 60)}m ago" if seconds < 3600 else
        f"{int(seconds // 3600)}h ago" if seconds < 86400 else
        f"{int(seconds // 86400)}d ago"
    )

    # Calculate progress based on status
    progress_map = {
        "aggregated": 25,
        "processing": 50,
        "production": 75,
        "published": 100,
        "failed": 0
    }
    progress = progress_map.get(status, 0)

    # Render news card
    headline = news.get('headline')

    with st.container():
        expander_text = f"{source.capitalize()} • {author} • {time_str}"
        with st.expander(f":gray[{expander_text}]", expanded=True, icon="📰"):
            # Center align all content within the card

            st.subheader(headline, anchor=False)
            st.caption(f"ID: {str(news_id)} | Status: {status.capitalize()}")
            st.progress(progress/100)

            def set_selected_news():
                st.session_state.selected_news = news_id

            st.button("View Details", width='stretch', key=f"view_{card_id}", type="secondary", on_click=set_selected_news)


def create_trend_chart(
    df: pd.DataFrame, 
    time_column: str = 'timestamp', 
    value_column: str = 'count',
    title: str = 'Processing Trend',
    height: int = 250
) -> alt.Chart | None:
    """Create a line chart for time-based trends
    
    Args:
        df: DataFrame containing time-series data
        time_column: Column name containing timestamps
        value_column: Column name containing values to plot
        title: Chart title
        height: Chart height in pixels
        
    Returns:
        Altair Chart object ready for display or None if data is empty
    """
    
    if df.empty:
        return None
    
    # Configure chart styling for dark theme
    theme_config = {
        'view': {'strokeWidth': 0},
        'axis': {
            'labelColor': '#f0f0f0',
            'titleColor': '#f0f0f0',
            'gridColor': '#333333',
            'grid': True
        },
        'title': {'color': '#f0f0f0'}
    }
    
    # Create the chart
    chart = alt.Chart(df).mark_bar(width=40, color='#00009B', opacity=0.9).encode(
        x=alt.X(f'{time_column}:T', axis=alt.Axis(format='%_I%p', title=None)),
        y=alt.Y(f'{value_column}:Q', 
               axis=alt.Axis(values=list(range(0, 10)), tickMinStep=1, title=None),
               scale=alt.Scale(domain=[0, 10])
        ),
        tooltip=[alt.Tooltip(f'{time_column}:T', format='%b %d, %H:%M'), value_column]
    ).properties(
        title=alt.TitleParams(title, fontSize=32),
        width='container',
        height=height
    )
    
    # Apply theme configurations
    for config_name, settings in theme_config.items():
        chart = getattr(chart, f'configure_{config_name}')(**settings)
    
    return chart

def process_hourly_trend_data(
    df: pd.DataFrame, 
    timestamp_col: str = 'timestamp',
    past_hours: int = 24
) -> pd.DataFrame:
    """Process data for hourly trend visualization"""

    if df.empty:
        return pd.DataFrame()
        
    # Get the current time for reference
    now = datetime.now(timezone.utc)
    
    # Process data for hourly trend
    df_copy = df.copy()
    
    # Ensure timestamps are datetime objects
    if not pd.api.types.is_datetime64_any_dtype(df_copy[timestamp_col]):
        df_copy[timestamp_col] = pd.to_datetime(df_copy[timestamp_col])
    
    # Round timestamps to hours for grouping
    df_copy['hour'] = df_copy[timestamp_col].dt.floor('h')
    
    # Create a complete range of hours
    hour_range = pd.date_range(
        end=now.replace(minute=0, second=0, microsecond=0), 
        periods=past_hours, 
        freq='h'
    )
    hour_df = pd.DataFrame({'hour': hour_range})
    
    # Count items per hour
    hourly_counts = df_copy.groupby('hour').size().reset_index(name='count')
    
    # Merge with complete hour range to ensure all hours are represented
    hourly_counts = pd.merge(hour_df, hourly_counts, on='hour', how='left').fillna(0)
    
    # Format for display
    hourly_counts['count'] = hourly_counts['count'].astype(int)
    hourly_counts['hour_str'] = hourly_counts['hour'].dt.strftime('%H:00')
    
    return hourly_counts
