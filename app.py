import streamlit as st
import pandas as pd
from datetime import datetime
import json
from document_search import DocumentSearchEngine
import os

HISTORY_FILE = "query_history.json"
HISTORY_LIMIT = 3

def load_query_history():
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                history = json.load(f)
            if isinstance(history, list):
                return history[:HISTORY_LIMIT]
        except Exception:
            pass
    return []

def save_query_history(history):
    try:
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(history[:HISTORY_LIMIT], f)
    except Exception:
        pass

# Page configuration
st.set_page_config(
    page_title="IntelliDocument Search",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .search-container {
        background-color: #f0f2f6;
        padding: 2rem;
        border-radius: 10px;
        margin-bottom: 2rem;
    }
    .result-card {
        background-color: white;
        padding: 1.5rem;
        border-radius: 8px;
        border-left: 4px solid #1f77b4;
        margin-bottom: 1rem;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .score-badge {
        background-color: #1f77b4;
        color: white;
        padding: 0.25rem 0.5rem;
        border-radius: 4px;
        font-size: 0.8rem;
    }
    .feedback-buttons {
        display: flex;
        gap: 0.5rem;
        margin-top: 1rem;
    }
</style>
""", unsafe_allow_html=True)

@st.cache_resource
def load_search_engine():
    """Load the document search engine with caching."""
    try:
        engine = DocumentSearchEngine()
        return engine
    except Exception as e:
        st.error(f"Error loading search engine: {e}")
        return None

def main():
    # Header
    st.markdown('<h1 class="main-header">🔍 IntelliDocument Search</h1>', unsafe_allow_html=True)
    
    # Load search engine
    search_engine = load_search_engine()
    if not search_engine:
        st.error("Failed to load search engine. Please check your configuration.")
        return
    
    # Load query history
    query_history = load_query_history()

    # --- SESSION STATE MANAGEMENT ---
    if 'search_type' not in st.session_state:
        st.session_state['search_type'] = "Natural Language"
    if 'search_query' not in st.session_state:
        st.session_state['search_query'] = ""
    if 'search_results' not in st.session_state:
        st.session_state['search_results'] = None
    if 'last_search' not in st.session_state:
        st.session_state['last_search'] = None
    if 'feedback_given' not in st.session_state:
        st.session_state['feedback_given'] = set()
    if 'ai_answer' not in st.session_state:
        st.session_state['ai_answer'] = None

    # Dropdown for past queries
    selected_past_query = None
    if query_history:
        selected_past_query = st.selectbox(
            "Recent Queries",
            ["(Select a recent query)"] + query_history,
            index=0,
            help="Select a past query to populate the search bar"
        )
        # If a past query is selected, set it in session_state and trigger a search
        if (
            selected_past_query
            and selected_past_query != "(Select a recent query)"
            and selected_past_query != st.session_state['search_query']
        ):
            st.session_state['search_query'] = selected_past_query
            st.session_state['last_search'] = selected_past_query
            st.session_state['search_results'] = None  # Will trigger new search
            st.experimental_rerun()
    
    # Search type (let the widget manage session state)
    search_type = st.sidebar.selectbox(
        "Search Type",
        ["Natural Language", "Keyword Search"],
        index=["Natural Language", "Keyword Search"].index(st.session_state.get('search_type', "Natural Language")),
        help="Choose between natural language queries or keyword-based search",
        key="search_type"
    )
    
    # Search input
    if search_type == "Natural Language":
        query = st.text_area(
            "Enter your search query",
            value=st.session_state['search_query'],
            placeholder="Ask a question or describe what you're looking for...",
            height=100,
            help="Use natural language to search for information in your documents",
            key="search_query_area"
        )
    else:
        query = st.text_input(
            "Enter keywords (comma-separated)",
            value=st.session_state['search_query'],
            placeholder="AI, revenue, Germany, 2024",
            help="Enter keywords separated by commas for keyword-based search",
            key="search_query_input"
        )
    st.session_state['search_query'] = query
    
    # Search button
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        search_button = st.button("🔍 Search", type="primary", use_container_width=True)
    
    # Sidebar for filters and settings
    with st.sidebar:
        st.header("🔧 Search Settings")
        
        # Search type
        # This selectbox is now handled by st.session_state['search_type']
        
        # Number of results
        top_k = st.slider("Number of Results", 1, 20, 5)
        
        # Filters
        st.subheader("📋 Filters")
        
        # Get available metadata for filters
        all_metadata = search_engine.get_document_metadata()
        
        # Date filter
        dates = [doc.get('date') for doc in all_metadata if doc.get('date')]
        if dates:
            selected_date = st.selectbox("Date", ["All"] + list(set(dates)))
        else:
            selected_date = "All"
        
        # Author filter
        authors = [doc.get('author') for doc in all_metadata if doc.get('author')]
        if authors:
            selected_author = st.selectbox("Author", ["All"] + list(set(authors)))
        else:
            selected_author = "All"
        
        # Location filter
        locations = [doc.get('location') for doc in all_metadata if doc.get('location')]
        if locations:
            selected_location = st.selectbox("Location", ["All"] + list(set(locations)))
        else:
            selected_location = "All"
        
        # Document filter
        documents = [doc.get('title') for doc in all_metadata if doc.get('title')]
        if documents:
            selected_document = st.selectbox("Document", ["All"] + documents)
        else:
            selected_document = "All"
        
        # Build filters dictionary
        filters = {}
        if selected_date != "All":
            filters['date'] = selected_date
        if selected_author != "All":
            filters['author'] = selected_author
        if selected_location != "All":
            filters['location'] = selected_location
        if selected_document != "All":
            filters['title'] = selected_document
        
        # Sort options
        st.subheader("📊 Sort Options")
        sort_by = st.selectbox(
            "Sort by",
            ["Relevance Score", "Date", "Author", "Title"]
        )
        
        # Clear filters button
        if st.button("Clear All Filters"):
            st.rerun()
    
    # Search results
    if (search_button or st.session_state['search_results'] is None) and query.strip():
        # Update query history
        if query.strip() and (not query_history or query != query_history[0]):
            new_history = [query] + [q for q in query_history if q != query]
            save_query_history(new_history)
        # Clear previous answer
        st.session_state['ai_answer'] = None
        with st.spinner("Searching documents..."):
            try:
                if search_type == "Natural Language":
                    # Perform semantic search
                    results = search_engine.search(query, top_k=top_k, filters=filters)
                    
                    # Generate answer if results found
                    if results:
                        answer_result = search_engine.answer_question(query, results)
                        st.session_state['ai_answer'] = answer_result
                        
                else:
                    # Perform keyword search
                    keywords = [k.strip() for k in query.split(',') if k.strip()]
                    results = search_engine.keyword_search(keywords, top_k=top_k)
                
                # Sort results
                if sort_by == "Relevance Score":
                    results.sort(key=lambda x: x['relevance_score'], reverse=True)
                elif sort_by == "Date":
                    results.sort(key=lambda x: x.get('date', ''), reverse=True)
                elif sort_by == "Author":
                    results.sort(key=lambda x: x.get('author', ''))
                elif sort_by == "Title":
                    results.sort(key=lambda x: x.get('title', ''))
                
                # Display results
                st.session_state['search_results'] = results # Store results in session state
                st.session_state['last_search'] = query
                st.session_state['feedback_given'] = set()
                st.experimental_rerun() # Rerun to update UI
                    
            except Exception as e:
                st.error(f"Error during search: {e}")
    
    results = st.session_state['search_results']

    # --- AI ANSWER DISPLAY ---
    if search_type == "Natural Language" and st.session_state.get('ai_answer'):
        answer_result = st.session_state['ai_answer']
        st.subheader("🤖 AI Answer")
        st.markdown(f"**Answer:** {answer_result['answer']}")
        confidence = answer_result.get('confidence', 0)
        st.progress(confidence)
        st.caption(f"Confidence: {confidence:.2%}")
        if answer_result.get('sources'):
            st.subheader("📚 Sources")
            for i, source in enumerate(answer_result['sources']):
                with st.expander(f"Source {i+1}: {source['title']}"):
                    st.write(f"**Author:** {source['author']}")
                    st.write(f"**Date:** {source['date']}")
                    st.write(f"**Relevance Score:** {source['relevance_score']:.3f}")
                    st.write(f"**Content:** {source['chunk_text']}")

    # --- FEEDBACK LOGIC & RESULTS DISPLAY ---
    if results:
        st.subheader(f"📄 Search Results ({len(results)} found)")
        for i, result in enumerate(results):
            with st.container():
                doc_link = f"{result['doc_path']}#page-{result['page_number']}"
                st.markdown(f"""
                <div class="result-card">
                    <h4><a href="{doc_link}" target="_blank">{result['title']}</a></h4>
                    <p><strong>Author:</strong> {result.get('author', 'Unknown')} | 
                       <strong>Date:</strong> {result.get('date', 'Unknown')} | 
                       <strong>Location:</strong> {result.get('location', 'Unknown')}</p>
                    <p><strong>Page:</strong> {result.get('page_number', '?')} | <strong>Paragraph:</strong> {result.get('paragraph_number', '?')}</p>
                    <p><strong>Relevance Score:</strong> <span class="score-badge">{result['relevance_score']:.3f}</span></p>
                    <p><strong>Content:</strong> {result['chunk_text'][:300]}{'...' if len(result['chunk_text']) > 300 else ''}</p>
                </div>
                """, unsafe_allow_html=True)
                col1, col2, col3, col4 = st.columns([1, 1, 1, 1])
                with col1:
                    if st.button(f"👍 Relevant", key=f"relevant_{i}"):
                        search_engine.update_relevance_score(result['chunk_id'], 1.0)
                        st.session_state['feedback_given'].add(i)
                        st.success("Feedback recorded!")
                with col2:
                    if st.button(f"👎 Not Relevant", key=f"not_relevant_{i}"):
                        search_engine.update_relevance_score(result['chunk_id'], 0.0)
                        st.session_state['feedback_given'].add(i)
                        st.success("Feedback recorded!")
                with col3:
                    if st.button(f"🔍 More Like This", key=f"more_{i}"):
                        st.info("Feature coming soon!")
                with col4:
                    if st.button(f"📋 Copy", key=f"copy_{i}"):
                        st.write("Content copied to clipboard!")
                st.divider()

    # Document overview
    with st.expander("📚 Document Overview"):
        if all_metadata:
            df = pd.DataFrame(all_metadata)
            st.dataframe(
                df[['title', 'author', 'date', 'location']].fillna('Unknown'),
                use_container_width=True
            )
        else:
            st.info("No documents found in the documents directory.")

if __name__ == "__main__":
    main() 