"""Streamlit application for the Social Media Content Writer."""

import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st
from dotenv import load_dotenv
from pymongo import MongoClient

from src.graph.workflow import stream_workflow
from src.utils.env import get_secret
from src.models.content import ContentOutput

load_dotenv()

# Page configuration
st.set_page_config(
    page_title="Social Media Content Writer",
    page_icon="✍️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS
st.markdown("""
<style>
    .stApp {
        max-width: 1200px;
        margin: 0 auto;
    }
</style>
""", unsafe_allow_html=True)

# Node name to description mapping
NODE_DESCRIPTIONS = {
    "arxiv_researcher": "🔍 Researching...",
    "tavily_researcher": "🔍 Researching...",
    "duckduckgo_researcher": "🔍 Researching...",
    "condenser": "📝 Summarizing...",
    "writer": "✍️ Writing post...",
    "reviewer": "⚖️ Evaluating...",
    "prompt_builder": "🔧 Refining...",
}


def save_to_mongodb(content: ContentOutput, session_id: str, researchers: list[str]) -> str | None:
    """Save content to MongoDB.
    
    Args:
        content: ContentOutput to save.
        session_id: Unique session identifier.
        researchers: List of researchers used.
    
    Returns:
        MongoDB document ID if saved, None otherwise.
    """
    mongodb_uri = get_secret("MONGODB_URI")
    if not mongodb_uri:
        return None
    
    try:
        client = MongoClient(mongodb_uri)
        db_name = get_secret("MONGODB_DB_NAME", "content_writer")
        db = client[db_name]
        
        document = {
            "session_id": session_id,
            "topic": content.topic,
            "created_at": datetime.now(timezone.utc),
            "researchers_used": researchers,
            "post_v1": content.post_v1,
            "post_v2": content.post_v2,
            "judge_score": content.nota_juiz,
            "needed_refinement": content.precisou_refinar,
            "iterations": content.iterations,
            "summary": content.condensed_summary,
        }
        
        result = db.posts.insert_one(document)
        client.close()
        return str(result.inserted_id)
    
    except Exception as e:
        st.warning(f"⚠️ Failed to save to MongoDB: {e}")
        return None


def init_session_state() -> None:
    """Initialize session state variables."""
    if "generated_content" not in st.session_state:
        st.session_state.generated_content = None
    if "is_generating" not in st.session_state:
        st.session_state.is_generating = False
    if "session_id" not in st.session_state:
        st.session_state.session_id = str(uuid.uuid4())


def render_sidebar() -> None:
    """Render the sidebar with researcher selection and results."""
    with st.sidebar:
        st.header("🔬 Researchers")
        
        use_tavily = st.checkbox("Tavily", value=True)
        use_duckduckgo = st.checkbox("DuckDuckGo", value=True)
        use_arxiv = st.checkbox("arXiv", value=False)
        
        # Build list of selected researchers
        researchers = []
        if use_tavily:
            researchers.append("tavily")
        if use_duckduckgo:
            researchers.append("duckduckgo")
        if use_arxiv:
            researchers.append("arxiv")
        
        st.session_state.selected_researchers = researchers
        
        # Show research results if content was generated
        if st.session_state.generated_content:
            content = st.session_state.generated_content
            
            st.divider()
            st.header("📚 Research Results")
            
            for summary in content.research_summaries:
                source_name = summary.source.upper()
                with st.expander(f"🔍 {source_name}"):
                    st.markdown(summary.content)
                    if summary.raw_results:
                        st.caption(f"Sources: {len(summary.raw_results)} results")


def render_main_content() -> None:
    """Render the main content area."""
    st.title("✍️ Social Media Content Writer")
    st.markdown("Generate LinkedIn content using AI.")

    # Topic input
    topic = st.text_input(
        "📌 What is the topic of your content?",
        placeholder="E.g., Benefits of AI automation for small businesses",
        disabled=st.session_state.is_generating,
    )
    
    # Get selected researchers
    researchers = getattr(st.session_state, 'selected_researchers', ["tavily", "duckduckgo"])
    
    generate_btn = st.button(
        "🚀 Generate Content",
        disabled=st.session_state.is_generating or not topic or not researchers,
        use_container_width=True,
    )
    
    if not researchers:
        st.warning("⚠️ Please select at least one researcher!")

    # Generation process
    if generate_btn and topic and researchers:
        st.session_state.is_generating = True
        st.session_state.generated_content = None

        with st.status("🔄 Generating content...", expanded=True) as status:
            try:
                final_state = {"topic": topic}
                shown_messages = set()
                
                # Stream the workflow with real-time updates
                for node_name, state_update in stream_workflow(topic, researchers):
                    description = NODE_DESCRIPTIONS.get(node_name, f"⚙️ {node_name}")
                    # Only show each message once
                    if description not in shown_messages:
                        st.write(description)
                        shown_messages.add(description)
                    
                    # Update simple fields
                    for key, value in state_update.items():
                        if key == "research_summaries":
                            # Accumulate research summaries manually to avoid overwrite
                            current_summaries = final_state.get("research_summaries", [])
                            new_summaries = value
                            
                            # Add only if not already present (by source)
                            existing_sources = {s.source for s in current_summaries}
                            for summary in new_summaries:
                                if summary.source not in existing_sources:
                                    current_summaries.append(summary)
                            
                            final_state["research_summaries"] = current_summaries
                        else:
                            final_state[key] = value

                # Create ContentOutput from final_state dict
                content = ContentOutput(
                    topic=topic,
                    post_v1=final_state.get("post_v1", ""),
                    post_v2=final_state.get("post_v2"),
                    final_content=final_state.get("post_v2") or final_state.get("post_v1", ""),
                    condensed_summary=final_state.get("condensed_summary", ""),
                    research_summaries=final_state.get("research_summaries", []),
                    iterations=final_state.get("iteration", 1),
                    nota_juiz=final_state.get("nota_juiz"),
                    precisou_refinar=final_state.get("precisou_refinar", False),
                )

                # Save to MongoDB
                st.write("💾 Saving...")
                mongo_id = save_to_mongodb(content, st.session_state.session_id, researchers)
                if mongo_id:
                    content.mongo_id = mongo_id

                st.session_state.generated_content = content
                st.session_state.is_generating = False
                
                status.update(label="✅ Content generated!", state="complete")
                
                # Force rerun to show results in sidebar
                st.rerun()

            except Exception as e:
                st.session_state.is_generating = False
                status.update(label=f"❌ Error: {str(e)}", state="error")
                st.error(f"Failed to generate content: {str(e)}")

    # Display generated content
    if st.session_state.generated_content:
        content = st.session_state.generated_content

        st.divider()

        # Display V1 and V2 side by side if V2 exists
        if content.precisou_refinar and content.post_v2:
            col_v1, col_v2 = st.columns(2)
            
            with col_v1:
                st.markdown("### 📱 Post V1")
                st.markdown(content.post_v1)
            
            with col_v2:
                st.markdown("### 📱 Post V2 ⭐")
                st.markdown(content.post_v2)
        else:
            # Only V1
            st.markdown("### 📱 LinkedIn Post")
            st.markdown(content.post_v1)


def main() -> None:
    """Main application entry point."""
    init_session_state()
    render_sidebar()
    render_main_content()


if __name__ == "__main__":
    main()
