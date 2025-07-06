import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    """Configuration settings for the document search application."""
    
    # Anthropic API settings
    ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY')
    
    # Document processing settings
    DOCUMENTS_DIR = os.getenv('DOCUMENTS_DIR', 'documents')
    CHUNK_SIZE = int(os.getenv('CHUNK_SIZE', '500'))
    CHUNK_OVERLAP = int(os.getenv('CHUNK_OVERLAP', '50'))
    
    # Search settings
    DEFAULT_TOP_K = int(os.getenv('DEFAULT_TOP_K', '5'))
    MAX_TOP_K = int(os.getenv('MAX_TOP_K', '20'))
    
    # Model settings
    EMBEDDING_MODEL = os.getenv('EMBEDDING_MODEL', 'all-MiniLM-L6-v2')
    LLM_MODEL = os.getenv('LLM_MODEL', 'claude-3-5-sonnet-20241022')
    
    # UI settings
    STREAMLIT_PORT = int(os.getenv('STREAMLIT_PORT', '8501'))
    STREAMLIT_HOST = os.getenv('STREAMLIT_HOST', 'localhost')
    
    @classmethod
    def validate(cls):
        """Validate required configuration."""
        if not cls.ANTHROPIC_API_KEY:
            raise ValueError(
                "ANTHROPIC_API_KEY is required. Please set it in your environment "
                "variables or .env file."
            )
        
        if not os.path.exists(cls.DOCUMENTS_DIR):
            raise ValueError(f"Documents directory '{cls.DOCUMENTS_DIR}' does not exist.")
        
        return True 