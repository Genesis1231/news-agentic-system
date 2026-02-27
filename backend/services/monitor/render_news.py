from config import logger
import streamlit as st
import pandas as pd
from typing import Dict, Any

from .render_production import render_production
from .styles import STATUS_COLORS, STAGES

def render_news_detail_page(news: pd.Series) -> None:
    """Render detailed view of a news item."""

    if news is None or news.empty:
        st.error("News data has no content!")
        return

    # Back button
    if st.button("← Back to Newsroom", key="back_button", type="tertiary"):
        st.session_state.selected_news = None
        st.rerun()
    
    news_id = news.get('id')
    source = news.get('source')
    url = news.get('url', '#')
    headline = news.get('headline')
    status = news.get('status', 'failed')
    details = news.get('details', {})
    
    # Header and metadata
    st.title(headline, anchor=False)
    st.markdown(
        f"""
        <div style="color: #aaaaaa; font-size: 16px; margin-bottom: 20px;">
            ID: {news_id} | Source: {source} | URL: <a style="color: #3498db; text-decoration: none;" href='{url}' target='_blank'>{url}</a>
        </div>
        """, 
        unsafe_allow_html=True)
    
    # Display logs
    logs = news.get('log', ["No logs available yet."])
    with st.expander("View Detailed Logs", expanded=False):
        st.code("\n\n".join(logs[::-1]), wrap_lines=True)
    
    # Process timeline data
    render_status_timeline(status)
    
    st.divider()
    
    # Source section
    col1, col2 = st.columns(2)
    with col1:    
        st.subheader("Source", anchor=False)
        render_source_section(news)

    with col2:
        st.subheader("Classification", anchor=False)
        render_classification(details)
        
    
    coverage = details.get('evaluation', {}).get('coverage_depth', ["FLASH"])
    coverage_tabs = [f"**{item.capitalize()} News**" for item in coverage]
    for i, tab in enumerate(st.tabs(coverage_tabs)):
        with tab:
            # Get the depth
            depth = coverage[i].lower()
            
            # Processing pipeline section
            st.subheader("Creative Processing", anchor=False)
            render_processing_pipeline(details, depth)

            st.divider()
            
            # Media production status
            st.subheader("Media Production", anchor=False)
            render_production(details, depth)
            
            st.divider()
            
            # Distribution section
            st.subheader("Distribution Channels", anchor=False)    
            render_distribution_status(details)

def render_status_timeline(status: str) -> None:
    """ Render status timeline for content. """
    
    try:
        current_stage_index = STAGES.index(status) if status in STAGES else -1
    except ValueError:
        current_stage_index = -1 # Handle case where status might not be in STAGES
        st.error(f"Error: Unknown status - {status}")

    # Render timeline visualization
    cols = st.columns(len(STAGES))
    for i, stage in enumerate(STAGES):
        with cols[i]:
            is_current = (i == current_stage_index)
            is_completed_or_current = (i <= current_stage_index and current_stage_index != 4)
            
            # Determine background color
            if is_completed_or_current or is_current:
                bg_color = STATUS_COLORS.get(stage, "#666666") # Use defined color or default grey
                text_color = "white"
            else:
                bg_color = "#555555" # Grey out future stages
                text_color = "#aaaaaa"
            
            border = "2px solid white" if is_current else "1px solid #666666" # Highlight current, subtle border otherwise
            font_weight = "bold" if is_current else "normal"
            
            # Simplified display: just the stage name
            st.markdown(f"""
            <div style="background-color: {bg_color}; border: {border}; color: {text_color}; 
                         padding: 10px; border-radius: 5px; text-align: center; height: 60px; display: flex; align-items: center; justify-content: center;">
                <div style="font-weight: {font_weight};">{stage.capitalize()}</div>
            </div>
            """, unsafe_allow_html=True)

def render_source_section(news: pd.Series) -> None:
    """ Render source section for content. """
    
    author = news.get('author', 'Unknown')
    timestamp = news.get('timestamp').strftime('%Y-%m-%d %H:%M:%S')
    details = news.get('details', {})

    # Display content snippet in a streamlit container
    content_snippet = details.get('content', 'No content available.')

    if len(content_snippet) > 1000:
        content_snippet = content_snippet[:1000] + '...'
    
    st.markdown(
        f"<div style='border-radius: 8px; margin-bottom: 10px; padding: 20px; "
        f"background-color: #1e1e1e; border-left: 3px solid #3498db; '>"
        f"<b>{author}: </b> ({timestamp})<br />"
        f"{content_snippet}</div>",
        unsafe_allow_html=True
    )
    
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
                        # Display 2-3 images per row (max 3 columns)
                        num_images = len(urls)
                        cols_per_row = 2 if num_images == 4 else min(num_images, 3)
                        cols = st.columns(cols_per_row)

                        for i in range(num_images):
                            col_idx = i % cols_per_row
                            with cols[col_idx]:
                                st.image(urls[i], width="stretch")
                                
                elif media_type == 'video':
                    if isinstance(urls, str):
                        st.video(urls, width="stretch")
                    elif isinstance(urls, list):
                        for url in urls:
                            st.video(url, width="stretch")
                

    
def render_classification(details: Dict[str, Any]) -> None:
    """ Render classification for content. """
    
    classification = details.get("classification", {})
    
    metrics_data = [
        ("Category", ', '.join(classification.get('news_category', ['N/A']))),
        ("Geolocation", ', '.join(classification.get('geolocation', ['N/A']))),
        ("Potential Impact Score", classification.get('score', 0)),
        ("Source Level", classification.get('source_level', 'N/A')),
        ("Sentiment", classification.get('sentiment', 'N/A')),
        ("Relevance", f"{classification.get('relevance', 0):.2f}")
        ]
        
    cols = st.columns([1, 1])
    
    with cols[0]:
        st.metric(label="Category", value=metrics_data[0][1], border=True)
        st.metric(label="Geolocation", value=metrics_data[1][1], border=True)
        st.metric(label="Potential Impact Score", value=metrics_data[2][1], border=True)
    with cols[1]:
        st.metric(label="Sentiment", value=metrics_data[4][1], border=True)
        st.metric(label="Source Level", value=metrics_data[3][1], border=True)
        st.metric(label="Relevance", value=metrics_data[5][1], border=True)
    
    if entities := classification.get('entities'):
        # Convert entities to HTML buttons
        entity_list = " ".join(
            f"<button style='color: #CCC; font-size: 0.9em; background-color: #1e1e1e; border: 1px solid #CCC; border-radius: 6px; padding-left: 10px; padding-right: 10px; margin: 5px;'>{entity}</button>" 
            for entity in entities
        )
        entity_html = f"<div style='margin: 15px;'>{entity_list}</div>"
        
    if analysis := classification.get('analysis'):
        # Display analysis and entities
        st.markdown(f"""
            <div style="border: 1px solid #444; border-radius: 8px;">
                <div style='font-size: 0.9em; color: #fff; margin: 15px;'>
                    Analysis </div>
                <div style='color: #CCC; font-size: 1em; margin: 15px;'>
                    {analysis}
                </div>
                {entity_html or ""}
            </div>
            """, unsafe_allow_html=True)
        

def render_processing_pipeline(details: Dict[str, Any], depth: str) -> None:
    """ Render processing pipeline for content. """
    
    if not details or not "evaluation" in details:
        st.caption("Creative processing not started yet.")
        return
    
    current_stage = details.get(f"{depth}_processing_stage", "pending")
    stages = [
        ("Pending", "Waiting for the processing to start"),
        ("Research", "Gather additional context"),
        ("Writing", "Generate content script"),
        ("Review", "Validate generated content"),
        ("Approval", "Review and approve content"),
        ("Finalization", "Finalize content for production")
    ]
    
    # Create a grid for stages
    cols = st.columns(3)
    for idx, (stage, description) in enumerate(stages):
        with cols[idx % 3]:
            is_current = stage.lower() == current_stage
            is_completed = stages.index((stage, description)) < stages.index((current_stage.capitalize(), dict(stages)[current_stage.capitalize()]))
            
            # Status indicator with improved visibility
            status_color = "#2ecc71" if is_completed else "#f39c12" if is_current else "#555555"
            st.markdown(f"""
            <div style="background-color: rgba(45, 45, 45, 0.7); padding: 10px; border-radius: 5px; margin-bottom: 10px; {"border: 1px solid #2ecc71;" if is_current else ""}">
                <div style="display: flex; align-items: center; gap: 10px;">
                    <div style="width: 10px; height: 10px; border-radius: 50%; background-color: {status_color};"></div>
                    <div style="font-weight: {'bold' if is_current else 'normal'};">{stage}</div>
                </div>
                <div style="font-size: 0.8em; color: #aaaaaa; margin-top: 5px;">{description}</div>
            </div>
            """, unsafe_allow_html=True)
    
    # Display final script
    if final_script := details.get(f"{depth}_script"):
        st.subheader("Final Script", anchor=False)
        st.code(final_script, wrap_lines=True, language="text")
        
    elif draft := details.get(f"{depth}_draft"):
        formatted_draft = draft.replace('\\n', '\n')
        word_count = len(formatted_draft.split())
        
        col1, col2 = st.columns(2)
        with col1:
            # Convert literal \n to actual newlines for proper display
            st.subheader(f"Draft Script ({word_count} words)", anchor=False, divider=True)
            st.markdown(formatted_draft)
        with col2:
            review = details.get(f"{depth}_review")
            st.subheader("Review", anchor=False, divider=True)
            st.markdown(review)

def render_production_status(details: Dict[str, Any], depth: str) -> None:
    """ Render production status for content. """
    
    if not (production := details.get(f"{depth}_production")):
        st.caption("Media production not started yet.")
        return

    # Display final script
    if text := production.get("text"):
        st.markdown(f"""
            <div style="background-color: #2d2d2d; border-radius: 8px; padding: 15px; height: 100%; margin: 10px;">
                <div style="color: #aaaaaa; font-size: 0.9em; margin-bottom: 10px;">
                    Script
                </div>
                <div style="font-size: 1.2em; margin-bottom: 10px;">
                    {text}
                </div>
            </div>
            """, unsafe_allow_html=True)

    if audio_status := production.get("audio"):
        
        if audio_status == "start":
            st.spinner("Generating audio news... (this may take a few minutes)")
        else:
            col1, col2 = st.columns(2, vertical_alignment="center")
            with col1:
                st.success(" Audio production completed.", icon="📢")
            with col2:
                with st.popover("Preview"):
                    st.audio(audio_status, format="audio/mp3")
    
    if video_status := production.get("video"):
        if video_status == "start":
            st.spinner("Rendering video news... (this may take several minutes)")
        else:
            col1, col2 = st.columns(2, vertical_alignment="center")
            with col1:
                st.success(" Video production completed.", icon="🎬")
            with col2:
                with st.popover("Preview"):
                    st.video(video_status)

def render_distribution_status(details) -> None:
    """ Render distribution status for content. """
    
    if 'distribution' not in details:
        st.caption("News distribution not started yet.")
        return

    platforms = details.get('platforms', [])
    cols = st.columns(4)
    for idx, platform in enumerate(['YouTube', 'Twitter', 'Spotify', 'Apple Podcasts']):
        with cols[idx]:
            is_published = platform in platforms
            st.markdown(f"""
            <div style="background-color: rgba(45, 45, 45, 0.7); padding: 10px; border-radius: 5px; text-align: center;">
                <div style="font-weight: bold; margin-bottom: 5px;">{platform}</div>
                <div style="color: {'#2ecc71' if is_published else '#888888'}; font-size: 0.9em;">
                    {"Published ✓" if is_published else "Pending"}
                </div>
            </div>
            """, unsafe_allow_html=True)