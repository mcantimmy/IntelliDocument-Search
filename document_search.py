import os
import json
import re
from datetime import datetime
from typing import List, Dict, Tuple, Optional
import numpy as np
import pandas as pd
from sentence_transformers import SentenceTransformer
import faiss
import anthropic
from pathlib import Path
from config import Config

class DocumentSearchEngine:
    def __init__(self, documents_dir: str = None, model_name: str = None):
        """
        Initialize the document search engine.
        
        Args:
            documents_dir: Directory containing documents
            model_name: Sentence transformer model name
        """
        # Validate configuration
        Config.validate()
        
        self.documents_dir = Path(documents_dir or Config.DOCUMENTS_DIR)
        self.model = SentenceTransformer(model_name or Config.EMBEDDING_MODEL)
        self.documents = []
        self.embeddings = []
        self.faiss_index = None
        self.document_chunks = []
        self.metadata = []
        
        # Initialize Anthropic client
        self.anthropic_client = anthropic.Anthropic(api_key=Config.ANTHROPIC_API_KEY)
        
        # Load and process documents
        self._load_documents()
        self._create_embeddings()
        self._build_faiss_index()
    
    def _load_documents(self):
        """Load all documents from the documents directory."""
        print("Loading documents...")
        
        for file_path in self.documents_dir.glob("*.txt"):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Extract metadata from content
                metadata = self._extract_metadata(content, file_path.name)
                
                # Split content into chunks
                chunks = self._split_into_chunks(content)
                
                for i, chunk in enumerate(chunks):
                    self.document_chunks.append(chunk)
                    self.metadata.append({
                        **metadata,
                        'chunk_id': i,
                        'total_chunks': len(chunks),
                        'chunk_text': chunk[:300] + "..." if len(chunk) > 300 else chunk
                    })
                
                self.documents.append({
                    'filename': file_path.name,
                    'content': content,
                    'metadata': metadata,
                    'chunks': chunks
                })
                
                print(f"Loaded: {file_path.name} ({len(chunks)} chunks)")
                
            except Exception as e:
                print(f"Error loading {file_path}: {e}")
    
    def _extract_metadata(self, content: str, filename: str) -> Dict:
        """Extract metadata from document content."""
        metadata = {
            'filename': filename,
            'title': filename.replace('.txt', ''),
            'date': None,
            'author': None,
            'location': None,
            'page': 1  # Default page number
        }
        
        # Extract date
        date_patterns = [
            r'Date:\s*([^\n]+)',
            r'(\d{1,2}/\d{1,2}/\d{4})',
            r'(\d{4}-\d{1,2}-\d{1,2})'
        ]
        
        for pattern in date_patterns:
            match = re.search(pattern, content)
            if match:
                metadata['date'] = match.group(1).strip()
                break
        
        # Extract author
        author_patterns = [
            r'Author:\s*([^\n]+)',
            r'By:\s*([^\n]+)'
        ]
        
        for pattern in author_patterns:
            match = re.search(pattern, content)
            if match:
                metadata['author'] = match.group(1).strip()
                break
        
        # Extract location
        location_patterns = [
            r'Location:\s*([^\n]+)',
            r'([A-Z][a-z]+,\s*[A-Z]{2})'
        ]
        
        for pattern in location_patterns:
            match = re.search(pattern, content)
            if match:
                metadata['location'] = match.group(1).strip()
                break
        
        return metadata
    
    def _split_into_chunks(self, content: str, chunk_size: int = None, overlap: int = None) -> List[str]:
        """Split document content into overlapping chunks."""
        chunk_size = chunk_size or Config.CHUNK_SIZE
        overlap = overlap or Config.CHUNK_OVERLAP
        
        words = content.split()
        chunks = []
        
        for i in range(0, len(words), chunk_size - overlap):
            chunk_words = words[i:i + chunk_size]
            chunk = ' '.join(chunk_words)
            if chunk.strip():
                chunks.append(chunk)
        
        return chunks
    
    def _create_embeddings(self):
        """Create embeddings for all document chunks."""
        print("Creating embeddings...")
        
        if not self.document_chunks:
            return
        
        # Create embeddings
        embeddings = self.model.encode(self.document_chunks, show_progress_bar=True)
        self.embeddings = embeddings.astype('float32')
        
        print(f"Created {len(self.embeddings)} embeddings")
    
    def _build_faiss_index(self):
        """Build FAISS index for fast similarity search."""
        if len(self.embeddings) == 0:
            return
        
        print("Building FAISS index...")
        
        # Create FAISS index
        dimension = self.embeddings.shape[1]
        self.faiss_index = faiss.IndexFlatIP(dimension)  # Inner product for cosine similarity
        
        # Normalize embeddings for cosine similarity
        faiss.normalize_L2(self.embeddings)
        self.faiss_index.add(self.embeddings)
        
        print(f"FAISS index built with {self.faiss_index.ntotal} vectors")
    
    def search(self, query: str, top_k: int = 5, filters: Dict = None) -> List[Dict]:
        """
        Search for relevant documents using semantic similarity.
        
        Args:
            query: Search query
            top_k: Number of top results to return
            filters: Dictionary of filters (date, author, location, etc.)
        
        Returns:
            List of search results with relevance scores
        """
        if not self.faiss_index:
            return []
        
        # Create query embedding
        query_embedding = self.model.encode([query])
        query_embedding = query_embedding.astype('float32')
        faiss.normalize_L2(query_embedding)
        
        # Search
        scores, indices = self.faiss_index.search(query_embedding, top_k * 2)  # Get more results for filtering
        
        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx == -1:  # FAISS returns -1 for invalid indices
                continue
                
            metadata = self.metadata[idx].copy()
            metadata['relevance_score'] = float(score)
            metadata['chunk_text'] = self.document_chunks[idx]
            
            # Apply filters
            if filters and not self._apply_filters(metadata, filters):
                continue
            
            results.append(metadata)
            
            if len(results) >= top_k:
                break
        
        return results
    
    def _apply_filters(self, metadata: Dict, filters: Dict) -> bool:
        """Apply filters to metadata."""
        for key, value in filters.items():
            if key in metadata and metadata[key]:
                if key == 'date':
                    # Simple date filtering (can be enhanced)
                    if value and metadata[key] and value not in metadata[key]:
                        return False
                elif key in ['author', 'location']:
                    # Case-insensitive partial matching
                    if value and metadata[key]:
                        if value.lower() not in metadata[key].lower():
                            return False
                else:
                    # Exact matching for other fields
                    if value != metadata[key]:
                        return False
        return True
    
    def answer_question(self, question: str, context_results: List[Dict]) -> Dict:
        """
        Generate an answer to a question using the provided context.
        
        Args:
            question: The question to answer
            context_results: List of relevant document chunks
        
        Returns:
            Dictionary containing the answer and sources
        """
        if not context_results:
            return {
                'answer': 'I could not find relevant information to answer your question.',
                'sources': [],
                'confidence': 0.0
            }
        
        # Prepare context for LLM
        context_text = "\n\n".join([
            f"Document: {result['title']}\nAuthor: {result.get('author', 'Unknown')}\nDate: {result.get('date', 'Unknown')}\nContent: {result['chunk_text']}"
            for result in context_results[:3]  # Use top 3 results
        ])
        
        # Create prompt for Claude
        prompt = f"""You are a helpful assistant that answers questions based on the provided document context. 
        Please answer the following question using only the information provided in the context.
        If the context doesn't contain enough information to answer the question, say so.
        
        Context:
        {context_text}
        
        Question: {question}
        
        Please provide a clear, concise answer based on the context provided."""
        
        try:
            # Call Claude API
            response = self.anthropic_client.messages.create(
                model=Config.LLM_MODEL,
                max_tokens=1000,
                messages=[{"role": "user", "content": prompt}]
            )
            
            answer = response.content[0].text
            
            # Prepare sources
            sources = []
            for result in context_results[:3]:
                sources.append({
                    'title': result['title'],
                    'author': result.get('author', 'Unknown'),
                    'date': result.get('date', 'Unknown'),
                    'relevance_score': result['relevance_score'],
                    'chunk_text': result['chunk_text'][:300] + "..." if len(result['chunk_text']) > 300 else result['chunk_text']
                })
            
            return {
                'answer': answer,
                'sources': sources,
                'confidence': min(1.0, sum(r['relevance_score'] for r in context_results[:3]) / 3)
            }
            
        except Exception as e:
            return {
                'answer': f'Error generating answer: {str(e)}',
                'sources': [],
                'confidence': 0.0
            }
    
    def keyword_search(self, keywords: List[str], top_k: int = 5) -> List[Dict]:
        """
        Perform keyword-based search.
        
        Args:
            keywords: List of keywords to search for
            top_k: Number of top results to return
        
        Returns:
            List of search results
        """
        results = []
        
        for i, chunk in enumerate(self.document_chunks):
            score = 0
            chunk_lower = chunk.lower()
            
            for keyword in keywords:
                if keyword.lower() in chunk_lower:
                    score += 1
            
            if score > 0:
                metadata = self.metadata[i].copy()
                metadata['relevance_score'] = score / len(keywords)  # Normalize score
                metadata['chunk_text'] = chunk
                results.append(metadata)
        
        # Sort by relevance score and return top_k
        results.sort(key=lambda x: x['relevance_score'], reverse=True)
        return results[:top_k]
    
    def get_document_metadata(self) -> List[Dict]:
        """Get metadata for all documents."""
        unique_docs = {}
        
        for metadata in self.metadata:
            filename = metadata['filename']
            if filename not in unique_docs:
                unique_docs[filename] = metadata.copy()
                unique_docs[filename]['total_chunks'] = metadata['total_chunks']
        
        return list(unique_docs.values())
    
    def update_relevance_score(self, chunk_id: int, feedback_score: float):
        """
        Update relevance score based on user feedback.
        
        Args:
            chunk_id: ID of the chunk to update
            feedback_score: New relevance score (0-1)
        """
        if 0 <= chunk_id < len(self.metadata):
            # Simple feedback mechanism - can be enhanced with more sophisticated algorithms
            current_score = self.metadata[chunk_id].get('relevance_score', 0.5)
            updated_score = (current_score + feedback_score) / 2
            self.metadata[chunk_id]['relevance_score'] = updated_score 