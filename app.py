import streamlit as st
import pandas as pd
from datetime import datetime
import json
from document_search import DocumentSearchEngine
import os

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
    
    # Sidebar for filters and settings
    with st.sidebar:
        st.header("🔧 Search Settings")
        
        # Search type
        search_type = st.selectbox(
            "Search Type",
            ["Natural Language", "Keyword Search"],
            help="Choose between natural language queries or keyword-based search"
        )
        
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
    
    # Main content area
    st.markdown('<div class="search-container">', unsafe_allow_html=True)
    
    # Search input
    if search_type == "Natural Language":
        query = st.text_area(
            "Enter your search query",
            placeholder="Ask a question or describe what you're looking for...",
            height=100,
            help="Use natural language to search for information in your documents"
        )
    else:
        keywords_input = st.text_input(
            "Enter keywords (comma-separated)",
            placeholder="AI, revenue, Germany, 2024",
            help="Enter keywords separated by commas for keyword-based search"
        )
        query = keywords_input
    
    # Search button
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        search_button = st.button("🔍 Search", type="primary", use_container_width=True)
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Search results
    if search_button and query:
        with st.spinner("Searching documents..."):
            try:
                if search_type == "Natural Language":
                    # Perform semantic search
                    results = search_engine.search(query, top_k=top_k, filters=filters)
                    
                    # Generate answer if results found
                    if results:
                        answer_result = search_engine.answer_question(query, results)
                        
                        # Display answer
                        st.subheader("🤖 AI Answer")
                        st.markdown(f"**Answer:** {answer_result['answer']}")
                        
                        # Confidence score
                        confidence = answer_result['confidence']
                        st.progress(confidence)
                        st.caption(f"Confidence: {confidence:.2%}")
                        
                        # Sources
                        if answer_result['sources']:
                            st.subheader("📚 Sources")
                            for i, source in enumerate(answer_result['sources']):
                                with st.expander(f"Source {i+1}: {source['title']}"):
                                    st.write(f"**Author:** {source['author']}")
                                    st.write(f"**Date:** {source['date']}")
                                    st.write(f"**Relevance Score:** {source['relevance_score']:.3f}")
                                    st.write(f"**Content:** {source['chunk_text']}")
                    
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
                if results:
                    st.subheader(f"📄 Search Results ({len(results)} found)")
                    
                    for i, result in enumerate(results):
                        with st.container():
                            st.markdown(f"""
                            <div class="result-card">
                                <h4>{result['title']}</h4>
                                <p><strong>Author:</strong> {result.get('author', 'Unknown')} | 
                                   <strong>Date:</strong> {result.get('date', 'Unknown')} | 
                                   <strong>Location:</strong> {result.get('location', 'Unknown')}</p>
                                <p><strong>Relevance Score:</strong> <span class="score-badge">{result['relevance_score']:.3f}</span></p>
                                <p><strong>Content:</strong> {result['chunk_text'][:300]}{'...' if len(result['chunk_text']) > 300 else ''}</p>
                            </div>
                            """, unsafe_allow_html=True)
                            
                            # Feedback mechanism
                            col1, col2, col3, col4 = st.columns([1, 1, 1, 1])
                            with col1:
                                if st.button(f"👍 Relevant", key=f"relevant_{i}"):
                                    search_engine.update_relevance_score(result['chunk_id'], 1.0)
                                    st.success("Feedback recorded!")
                            with col2:
                                if st.button(f"👎 Not Relevant", key=f"not_relevant_{i}"):
                                    search_engine.update_relevance_score(result['chunk_id'], 0.0)
                                    st.success("Feedback recorded!")
                            with col3:
                                if st.button(f"🔍 More Like This", key=f"more_{i}"):
                                    # Could implement similar document search here
                                    st.info("Feature coming soon!")
                            with col4:
                                if st.button(f"📋 Copy", key=f"copy_{i}"):
                                    st.write("Content copied to clipboard!")
                            
                            st.divider()
                
                else:
                    st.warning("No results found. Try adjusting your search terms or filters.")
                    
            except Exception as e:
                st.error(f"Error during search: {e}")
    
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