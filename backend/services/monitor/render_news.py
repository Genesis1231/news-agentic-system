from config import logger
import re
import streamlit as st
import pandas as pd
from typing import Dict, Any, List

from .render_production import render_production
from .styles import STATUS_COLORS, STAGES

# Map status to Streamlit markdown color names
STATUS_ST_COLORS = {
    "aggregated": "blue",
    "processing": "orange",
    "production": "orange",
    "published": "green",
    "failed": "red"
}


def render_news_detail_page(news: pd.Series, logs: List[str] | None = None) -> None:
    """Render detailed view of a news item."""

    if news is None or news.empty:
        st.error("News data has no content!")
        return

    # Back button
    if st.button("<< Back to Newsroom", key="back_button", type="tertiary"):
        st.session_state.selected_news = None
        st.rerun()

    news_id = news.get('id')
    source = news.get('source', 'Unknown')
    url = news.get('url') or '#'
    headline = news.get('headline', 'Untitled')
    status = news.get('status', 'failed')
    raw_details = news.get('details')
    details = raw_details if isinstance(raw_details, dict) else {}

    # Header
    st.title(headline, anchor=False)
    st.caption(f"ID: {news_id} · Source: {source} · [{url}]({url})")

    # Logs expander
    if logs is None:
        raw_logs = news.get('log')
        logs = raw_logs if isinstance(raw_logs, list) else ["No logs available yet."]
    if not logs:
        logs = ["No logs available yet."]
    with st.expander("View Logs", expanded=False):
        st.code("\n\n".join(str(entry) for entry in logs[::-1]), wrap_lines=True)

    # Status timeline
    render_status_timeline(status)

    st.divider()
    
    # Source + Classification side by side
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Source", anchor=False)
        render_source_section(news)

    with col2:
        st.subheader("Classification", anchor=False)
        render_classification(details)

    # Coverage depth tabs — always FLASH, optionally DEEP
    coverage = details.get('evaluation', {}).get('coverage_depth', ["FLASH"])
    if not coverage:
        coverage = ["FLASH"]
    coverage_tabs = [f"**{item.capitalize()} News**" for item in coverage]
    for i, tab in enumerate(st.tabs(coverage_tabs)):
        with tab:
            depth = coverage[i].lower()

            st.subheader("Creative Processing", anchor=False)
            render_processing_pipeline(details, depth)

            st.divider()

            st.subheader("Media Production", anchor=False)
            render_production(details, depth)

            st.divider()

            st.subheader("Distribution Channels", anchor=False)
            render_distribution_status(details)


def render_status_timeline(status: str) -> None:
    """Render status timeline as a horizontal pipeline using Streamlit columns."""

    try:
        current_stage_index = STAGES.index(status) if status in STAGES else -1
    except ValueError:
        current_stage_index = -1
        st.error(f"Error: Unknown status - {status}")

    # Pipeline steps in columns
    cols = st.columns(len(STAGES))
    for i, stage in enumerate(STAGES):
        with cols[i]:
            is_current = (i == current_stage_index)
            is_completed = (i < current_stage_index and current_stage_index != 4)
            is_failed = (stage == "failed" and current_stage_index == 4)

            if is_failed:
                color = "red"
            elif is_current:
                color = STATUS_ST_COLORS.get(stage, "orange")
            elif is_completed:
                color = STATUS_ST_COLORS.get(stage, "green")
            else:
                color = "gray"

            label = stage.capitalize()

            # Each step always shows its color. Reached steps are bold with filled icon.
            alert_map = {
                "aggregated": st.info,
                "processing": st.warning,
                "production": st.warning,
                "published": st.success,
                "failed": st.error,
            }
            alert_fn = alert_map.get(stage, st.info)

            if is_completed or is_current or is_failed:
                if is_completed:
                    alert_fn(f"**✓ {label}**")
                else:
                    alert_fn(f"**● {label}**")
            else:
                alert_fn(f"○ {label}")


def render_source_section(news: pd.Series) -> None:
    """Render source section."""

    author = news.get('author') or 'Unknown'
    ts = news.get('timestamp')
    timestamp = ts.strftime('%Y-%m-%d %H:%M:%S') if pd.notna(ts) else 'N/A'
    raw_details = news.get('details')
    details = raw_details if isinstance(raw_details, dict) else {}

    content = details.get('content', 'No content available.')

    # Parse structured tweet content (retweets/quotes with tagged sections)
    main_match = re.search(r'<main_content>(.*?)</main_content>', content or '', re.DOTALL)
    retweet_match = re.search(r'<retweeted_content>(.*?)</retweeted_content>', content or '', re.DOTALL)
    # Extract the "Retweeted from ..." prefix line between the tags
    prefix_match = re.search(r'</main_content>\s*(.*?)\s*<retweeted_content>', content or '', re.DOTALL)

    if not main_match and not prefix_match:
        prefix_match = re.search(r'^(.*?)<retweeted_content>', content or '', re.DOTALL)

    with st.container(border=True):
        st.caption(f"**{author}** · {timestamp}")

        if main_match or retweet_match:
            # Structured retweet/quote — render as subsections
            if main_match:
                main_text = main_match.group(1).strip()
                st.markdown(main_text)

            if retweet_match:
                retweet_text = retweet_match.group(1).strip()
                prefix_text = prefix_match.group(1).strip() if prefix_match else "Retweeted"
                prefix_text = re.sub(r'<[^>]+>', '', prefix_text).strip()

                with st.expander(f"{prefix_text}", expanded=True, icon="🔁"):
                    st.markdown(retweet_text)
        else:
            # Regular tweet — show as-is
            content_snippet = content if content and len(content) <= 1000 else (content[:1000] + '...' if content else '')
            st.markdown(content_snippet)

    media = details.get('media', {})
    for media_type in ['photo', 'video']:
        media_list = media.get(media_type, {})
        if urls := media_list.get('urls'):
            with st.expander(f"{media_type.capitalize()}s", expanded=True):
                media_description = media_list.get('description')
                if media_description:
                    with st.popover("Description"):
                        st.markdown(media_description, unsafe_allow_html=True)

                if media_type == 'photo':
                    if not isinstance(urls, list) or len(urls) == 1:
                        st.image(urls, width="stretch")
                    else:
                        num_images = len(urls)
                        cols_per_row = 2 if num_images == 4 else min(num_images, 3)
                        img_cols = st.columns(cols_per_row)
                        for j in range(num_images):
                            with img_cols[j % cols_per_row]:
                                st.image(urls[j], width="stretch")

                elif media_type == 'video':
                    if isinstance(urls, str):
                        st.video(urls, width="stretch")
                    elif isinstance(urls, list):
                        for vid_url in urls:
                            st.video(vid_url, width="stretch")


def render_classification(details: Dict[str, Any]) -> None:
    """Render classification metrics and entity tags."""

    classification = details.get("classification", {})

    cols = st.columns([1, 1])
    with cols[0]:
        st.metric(label="Category", value=', '.join(classification.get('news_category', ['N/A'])), border=True)
        st.metric(label="News Type", value=', '.join(classification.get('news_type', ['N/A'])), border=True)
        st.metric(label="Impact Score", value=classification.get('score', 0), border=True)
    with cols[1]:
        st.metric(label="Sentiment", value=classification.get('sentiment', 'N/A'), border=True)
        st.metric(label="Source Level", value=classification.get('source_level', 'N/A'), border=True)
        st.metric(label="Relevance", value=f"{classification.get('relevance', 0):.2f}", border=True)

    # Entity tags as pills
    if entities := classification.get('entities'):
        st.subheader("Entities")
        entity_cols = st.columns(min(len(entities), 4)) # Max 4 per row
        for idx, entity in enumerate(entities):
            with entity_cols[idx % 4]:
                st.info(entity)

    # Analysis block
    if analysis := classification.get('analysis'):
        with st.container(border=True):
            st.caption("ANALYSIS")
            st.markdown(analysis)


def render_processing_pipeline(details: Dict[str, Any], depth: str) -> None:
    """Render processing pipeline using native Streamlit components."""

    if not details or "evaluation" not in details:
        st.caption("Creative processing not started yet.")
        return

    current_stage = details.get(f"{depth}_processing_stage", "pending")
    stages = [
        ("Pending", "Waiting to start"),
        ("Research", "Gather context"),
        ("Writing", "Generate script"),
        ("Review", "Validate content"),
        ("Approval", "Review & approve"),
        ("Finalization", "Finalize for production")
    ]

    try:
        current_idx = next(i for i, (s, _) in enumerate(stages) if s.lower() == current_stage)
    except StopIteration:
        current_idx = 0

    # Render pipeline in 3-column grid
    cols = st.columns(3)
    for idx, (stage, description) in enumerate(stages):
        with cols[idx % 3]:
            is_current = (idx == current_idx)
            is_completed = (idx < current_idx)

            if is_completed:
                color = "green"
                icon = "✓"
            elif is_current:
                color = "orange"
                icon = "●"
            else:
                color = "gray"
                icon = "○"

            with st.container(border=True):
                st.markdown(f":{color}[{icon}] **{stage}**" if (is_current or is_completed) else f":{color}[{icon}] {stage}")
                st.caption(description)

    # Display final script or draft
    if final_script := details.get(f"{depth}_script"):
        st.subheader("Final Script", anchor=False)
        st.code(final_script, wrap_lines=True, language="text")

    elif draft := details.get(f"{depth}_draft"):
        formatted_draft = draft.replace('\\n', '\n')
        word_count = len(formatted_draft.split())

        col1, col2 = st.columns(2)
        with col1:
            st.subheader(f"Draft Script ({word_count} words)", anchor=False, divider=True)
            st.markdown(formatted_draft)
        with col2:
            review = details.get(f"{depth}_review")
            st.subheader("Review", anchor=False, divider=True)
            st.markdown(review)


def render_production_status(details: Dict[str, Any], depth: str) -> None:
    """Render production status for content."""

    if not (production := details.get(f"{depth}_production")):
        st.caption("Media production not started yet.")
        return

    if text := production.get("text"):
        with st.container(border=True):
            st.caption("SCRIPT")
            st.markdown(text)

    if audio_status := production.get("audio"):
        if audio_status == "start":
            st.spinner("Generating audio news... (this may take a few minutes)")
        else:
            col1, col2 = st.columns(2, vertical_alignment="center")
            with col1:
                st.success("Audio production completed.", icon="📢")
            with col2:
                with st.popover("Preview"):
                    st.audio(audio_status, format="audio/mp3")

    if video_status := production.get("video"):
        if video_status == "start":
            st.spinner("Rendering video news... (this may take several minutes)")
        else:
            col1, col2 = st.columns(2, vertical_alignment="center")
            with col1:
                st.success("Video production completed.", icon="🎬")
            with col2:
                with st.popover("Preview"):
                    st.video(video_status)


def render_distribution_status(details) -> None:
    """Render distribution status with platform cards."""

    if 'distribution' not in details:
        st.caption("News distribution not started yet.")
        return

    platforms = details.get('platforms', [])
    cols = st.columns(4)
    for idx, platform in enumerate(['YouTube', 'Twitter', 'Spotify', 'Apple Podcasts']):
        with cols[idx]:
            is_published = platform in platforms
            with st.container(border=True):
                st.markdown(f"**{platform}**")
                if is_published:
                    st.caption(":green[Published ✓]")
                else:
                    st.caption(":gray[Pending]")
