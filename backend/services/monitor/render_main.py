import streamlit as st
import pandas as pd
from datetime import datetime, timezone, timedelta
import altair as alt

from .styles import STATUS_COLORS

# Map status to Streamlit markdown color names
STATUS_ST_COLORS = {
    "aggregated": "blue",
    "processing": "orange",
    "production": "orange",
    "published": "green",
    "failed": "red"
}


def render_news_board(news_data: pd.DataFrame) -> None:
    """Render the main news board with metrics and cards"""

    if news_data.empty:
        st.info("No news items found matching your criteria")
        return

    render_metrics_section(news_data)

    # Pagination setup
    if 'page' not in st.session_state:
        st.session_state.page = 1
    if 'items_per_page' not in st.session_state:
        st.session_state.items_per_page = 30

    total_items = len(news_data)
    items_per_page = st.session_state.items_per_page
    total_pages = (total_items + items_per_page - 1) // items_per_page

    if st.session_state.page > total_pages:
        st.session_state.page = total_pages if total_pages > 0 else 1

    start_idx = (st.session_state.page - 1) * items_per_page
    end_idx = start_idx + items_per_page
    page_data = news_data.iloc[start_idx:end_idx]

    # Display news cards in a grid
    cols = st.columns(3)
    for i, (_, news) in enumerate(page_data.iterrows()):
        with cols[i % 3]:
            render_news_card(news, f"{news.get('id', 'unknown')}_{start_idx + i}")

    # Pagination controls
    items_per_page_options = [30, 60, 120]
    col1, col2, col3, col4 = st.columns([7, 1, 1, 1])

    with col1:
        st.caption(f"Page {st.session_state.page} of {total_pages}")

    if total_pages > 1:
        with col2:
            if st.session_state.page > 1:
                if st.button("Prev", key="prev_page", type="tertiary"):
                    st.session_state.page -= 1
                    st.rerun()
        with col3:
            if st.session_state.page < total_pages:
                if st.button("Next", key="next_page", type="tertiary"):
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

    if selected_items_per_page != st.session_state.items_per_page:
        st.session_state.items_per_page = selected_items_per_page
        st.session_state.page = 1
        st.rerun()


def render_trend_chart(news_data: pd.DataFrame) -> None:
    """Render a bar chart showing hourly news processing trend"""

    if news_data.empty:
        st.info("No news items found.")
        return

    try:
        hourly_counts = process_hourly_trend_data(news_data)
    except Exception as exc:
        st.warning("Unable to render trend chart due to invalid timestamp data.")
        st.caption(f"Chart error: {exc}")
        return

    chart = create_trend_chart(
        df=hourly_counts,
        time_column='hour',
        value_column='count',
        title='News Trend (Past 24 Hours)',
        height=400
    )

    if chart:
        st.altair_chart(chart, use_container_width=True)


def render_metrics_section(filtered_data: pd.DataFrame) -> None:
    """Render metrics section with key statistics"""

    if filtered_data.empty:
        st.info("No news items found matching your criteria")
        return

    metrics_cols = st.columns(4)

    with metrics_cols[0]:
        st.metric(label="Total Items", value=len(filtered_data), border=True)

    with metrics_cols[1]:
        now = datetime.now(timezone.utc)
        hour_ago = now - timedelta(hours=1)
        recent_count = 0
        if 'timestamp' in filtered_data.columns:
            recent_count = len(filtered_data[filtered_data['timestamp'] >= hour_ago])
        st.metric(label="Last Hour", value=recent_count, border=True)

    with metrics_cols[2]:
        published_count = len(filtered_data[filtered_data['status'] == 'published']) if 'status' in filtered_data.columns else 0
        st.metric(label="Published", value=published_count, border=True)

    with metrics_cols[3]:
        if 'source' in filtered_data.columns and not filtered_data.empty:
            top_source = filtered_data['source'].value_counts().idxmax()
            top_source_count = filtered_data['source'].value_counts().max()
        else:
            top_source = "N/A"
            top_source_count = 0
        st.metric(label="Top Source", value=f"{str(top_source).capitalize()} ({top_source_count})", border=True)


def render_news_card(news: pd.Series, card_id: str) -> None:
    """Render a single news card using native Streamlit components"""

    status = news.get('status', 'failed')
    news_id = news.get('id')
    source = news.get('source', 'Unknown')
    author = news.get('author', 'Unknown')
    headline = news.get('headline', 'Untitled')

    # Relative time
    timestamp = news.get('timestamp')
    if isinstance(timestamp, datetime):
        seconds = (datetime.now(timezone.utc) - timestamp).total_seconds()
    else:
        if timestamp is None:
            seconds = 0
        else:
            try:
                timestamp_dt = pd.to_datetime(timestamp)
                seconds = (datetime.now(timezone.utc) - timestamp_dt).total_seconds()
            except Exception:
                seconds = 0
    time_str = (
        f"{int(seconds)}s ago" if seconds < 60 else
        f"{int(seconds // 60)}m ago" if seconds < 3600 else
        f"{int(seconds // 3600)}h ago" if seconds < 86400 else
        f"{int(seconds // 86400)}d ago"
    )

    color = STATUS_ST_COLORS.get(status, "gray")

    with st.container(border=True):
        st.caption(f"#{news_id}: :{color}[{status.capitalize()}] · {time_str} ")
        st.subheader(headline)
        st.caption(f"{source.capitalize()} · {author}")

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
    """Create a bar chart for time-based trends with amber/charcoal theme"""

    if df.empty:
        return None

    max_count = int(df[value_column].max()) if not df[value_column].empty else 1
    y_max = max(max_count + 1, 5)  # At least 5 for visual clarity

    chart = alt.Chart(df).mark_bar(
        color='#d4a843',
        opacity=0.85,
        cornerRadiusTopLeft=3,
        cornerRadiusTopRight=3
    ).encode(
        x=alt.X(f'{time_column}:T', axis=alt.Axis(format='%_I%p', title=None, labelColor='#8b919a', labelFont='DM Sans')),
        y=alt.Y(f'{value_column}:Q',
                axis=alt.Axis(tickMinStep=1, title=None, labelColor='#8b919a', labelFont='DM Sans'),
                scale=alt.Scale(domain=[0, y_max])
        ),
        tooltip=[alt.Tooltip(f'{time_column}:T', format='%b %d, %H:%M'), value_column]
    ).properties(
        title=alt.TitleParams(title, fontSize=18, color='#e8eaed', font='DM Sans', fontWeight=600),
        width='container',
        height=height
    ).configure_view(
        strokeWidth=0
    ).configure_axis(
        gridColor='#1a1e27',
        grid=True,
        domainColor='#1a1e27'
    )

    return chart


def process_hourly_trend_data(
    df: pd.DataFrame,
    timestamp_col: str = 'timestamp',
    past_hours: int = 24
) -> pd.DataFrame:
    """Process data for hourly trend visualization"""

    if df.empty:
        return pd.DataFrame()

    if timestamp_col not in df.columns:
        return pd.DataFrame()

    now = pd.Timestamp.now(tz='UTC')
    df_copy = df.copy()

    # Normalize timestamps to UTC to avoid tz-aware vs tz-naive merge errors.
    df_copy[timestamp_col] = pd.to_datetime(df_copy[timestamp_col], utc=True, errors='coerce')
    df_copy = df_copy.dropna(subset=[timestamp_col])

    if df_copy.empty:
        return pd.DataFrame()

    df_copy['hour'] = df_copy[timestamp_col].dt.floor('h')

    # Use pd.Timestamp for the end so timezone representation matches the data.
    hour_range = pd.date_range(
        end=now.floor('h'),
        periods=past_hours,
        freq='h'
    )
    hour_df = pd.DataFrame({'hour': hour_range})

    hourly_counts = df_copy.groupby('hour').size().reset_index(name='count')
    hourly_counts = pd.merge(hour_df, hourly_counts, on='hour', how='left').fillna(0)

    hourly_counts['count'] = hourly_counts['count'].astype(int)
    hourly_counts['hour_str'] = hourly_counts['hour'].dt.strftime('%H:00')

    return hourly_counts
