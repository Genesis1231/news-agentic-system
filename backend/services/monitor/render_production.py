from config import logger
import streamlit as st
import asyncio
from typing import Dict, Any

from backend.utils.TTS import TTSGenerator
from pydub import AudioSegment
import io

def render_production(details: Dict[str, Any], depth: str) -> None:
    """ Render production status for content. """
    
    if not (production_script := details.get(f"{depth}_script")):
        st.caption(f"{depth.capitalize()} media production not started yet.")
        return


    # Split script into sections by line breaks
    script_sections = production_script.split('\n') if production_script else []

    # Initialize session state for edited sections and save status if not exists
    if f"{depth}_saved_sections" not in st.session_state:
        st.session_state[f"{depth}_saved_sections"] = script_sections.copy()

    if f"audio_{depth}" not in st.session_state:
        st.session_state[f"audio_{depth}"] = {}
        
    if f"subtitle_{depth}" not in st.session_state:
        st.session_state[f"subtitle_{depth}"] = {}

    # Display each section in a row with 4 columns
    for i, section in enumerate(script_sections):
        if section.strip():  # Skip empty lines
            
            col1, col2 = st.columns([4,1])

            with col1:
                # Make script section editable - remove value from edited_sections, let key handle state
                # Initial value is original section; Streamlit will persist edits via key
                edited_section = st.text_area(
                    f"Section {i+1}",
                    value=section.strip(),
                    height=100,
                    key=f"edit_{depth}_{i}",
                    label_visibility="collapsed"
                )

                # Remove manual update to edited_sections (unnecessary now)

            with col2:
                subcol1, subcol2 = st.columns([1,1])
                with subcol1:
                    audio_button_disabled = st.session_state.get(f"audio_{depth}_{i}", False)
                    if st.button(
                        label="Audio", 
                        key=f"gen_audio_btn_{depth}_{i}", 
                        width="stretch", 
                        disabled=audio_button_disabled
                    ):
                        st.session_state[f"audio_{depth}_{i}"] = True

                with subcol2:
                    video_button_disabled = st.session_state.get(f"video_{depth}_{i}", False)
      
                    if not st.session_state.get(f"audio_{depth}", {}).get(i):
                        video_button_disabled = True
                    
                    button_label = "Pending" if video_button_disabled else "Video"
                    if st.button(
                        label=button_label, 
                        key=f"gen_video_btn_{depth}_{i}", 
                        width="stretch", 
                        disabled=video_button_disabled,
                    ):
                        st.info("Video generation started for this section...")
                        # TODO: Implement video generation for this specific section

                               # Individual save button for each section
                # Compute save_status directly from widget state
                saved_content = st.session_state[f"{depth}_saved_sections"][i] if i < len(st.session_state[f"{depth}_saved_sections"]) else section.strip()
                edited_content = st.session_state.get(f"edit_{depth}_{i}", saved_content)  # Default to saved/original if no edits yet
                save_status = (edited_content == saved_content)
                button_help = "Section saved" if save_status else "Save this section"

                if st.button(
                    "💾 Save", 
                    key=f"save_{depth}_{i}", 
                    width="stretch", 
                    help=button_help, 
                    disabled=save_status,
                    type="primary"
                ):
                    # Update saved_sections directly from widget state
                    # Extend saved_sections if i is out of bounds (for dynamic additions)
                    saved_sections = st.session_state[f"{depth}_saved_sections"]
                    if i >= len(saved_sections):
                        saved_sections.extend([""] * (i - len(saved_sections) + 1))  # Pad with empties or originals as needed
                    saved_sections[i] = st.session_state[f"edit_{depth}_{i}"]

                    logger.info(f"Saved section {i+1} for {depth}: {saved_sections[i]}")
                    # Existing persistence logic here if any
                    st.rerun()
                    
            if st.session_state.get(f"audio_{depth}_{i}"):
                # Generate audio for the section
                try:
                    with st.spinner("Generating audio news... (this may take a few minutes)"):
                        script = st.session_state.get(f"{depth}_saved_sections", {})[i]
                        if not script:
                            raise ValueError("Script is empty.")

                        audio_generator: TTSGenerator = TTSGenerator()
                        audio_path, subtitle_path = asyncio.run(audio_generator.generate(script))
                        st.session_state[f"audio_{depth}_{i}"] = False
                        
                        if not audio_path:
                            logger.error("Generation failed; no audio path returned.")
                            st.rerun()

                        st.session_state[f"audio_{depth}"][i] = audio_path
                        st.session_state[f"subtitle_{depth}"][i] = subtitle_path
                        st.rerun()
                        
                except Exception as e:
                    logger.error(f"Unexpected error in audio generation for section {i} in {depth}: {str(e)}")
                    st.session_state[f"audio_{depth}_{i}"] = False
                    st.error(f"Audio generation failed: {str(e)}")
            
            # Display the audio file for the section
            if audio_path := st.session_state.get(f"audio_{depth}", {}).get(i):
                st.audio(audio_path, format="audio/mp3")
                
            st.divider()


    # Check if we have any audio files to play
    col1, col2 = st.columns(2, border=True)
    with col1:
        if st.button("Test All Audio", type="tertiary"):
            audio_files = st.session_state.get(f"audio_{depth}", {})
            if audio_files and len(audio_files) > 0:   
                # sort the audio files by the key
                ordered_audio_files = [audio_files[i] for i in sorted(audio_files.keys()) if audio_files[i]]
                
                audio_buffer = combine_audio(ordered_audio_files)            
                st.audio(audio_buffer.getvalue(), format="audio/mp3")
    with col2:
        if st.button("Test All Video", type="tertiary"):
            video_files = st.session_state.get(f"video_{depth}", {})

                
def combine_audio(audio_files: list) -> io.BytesIO:
    """Combine audio files into a single audio file."""
    
    combined = AudioSegment.empty()
    for path in audio_files:
        combined += AudioSegment.from_mp3(path)

    buffer = io.BytesIO()
    combined.export(buffer, format="mp3")

    return buffer
    


    # if video_status := production.get("video"):
    #     st.markdown("---")
    #     st.subheader("Overall Video Production", anchor=False)
    #     if video_status == "start":
    #         st.spinner("Rendering video news... (this may take several minutes)")
    #     else:
    #         col1, col2 = st.columns(2, vertical_alignment="center")
    #         with col1:
    #             st.success(" Video production completed.", icon="🎬")
    #         with col2:
    #             with st.popover("Preview"):
    #                 st.video(video_status)