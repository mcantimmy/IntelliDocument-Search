#!/usr/bin/env python3
"""
Test script to verify the installation of IntelliDocument Search.
"""

import sys
import os

def test_imports():
    """Test that all required packages can be imported."""
    print("Testing imports...")
    
    try:
        import streamlit
        print("✅ Streamlit imported successfully")
    except ImportError as e:
        print(f"❌ Streamlit import failed: {e}")
        return False
    
    try:
        import anthropic
        print("✅ Anthropic imported successfully")
    except ImportError as e:
        print(f"❌ Anthropic import failed: {e}")
        return False
    
    try:
        import sentence_transformers
        print("✅ Sentence Transformers imported successfully")
    except ImportError as e:
        print(f"❌ Sentence Transformers import failed: {e}")
        return False
    
    try:
        import faiss
        print("✅ FAISS imported successfully")
    except ImportError as e:
        print(f"❌ FAISS import failed: {e}")
        return False
    
    try:
        import pandas
        print("✅ Pandas imported successfully")
    except ImportError as e:
        print(f"❌ Pandas import failed: {e}")
        return False
    
    try:
        import numpy
        print("✅ NumPy imported successfully")
    except ImportError as e:
        print(f"❌ NumPy import failed: {e}")
        return False
    
    return True

def test_config():
    """Test configuration loading."""
    print("\nTesting configuration...")
    
    try:
        from config import Config
        print("✅ Config module imported successfully")
        
        # Test if API key is set (don't validate, just check if it exists)
        if Config.ANTHROPIC_API_KEY:
            print("✅ Anthropic API key is set")
        else:
            print("⚠️  Anthropic API key is not set (you'll need to set it in .env file)")
        
        return True
    except Exception as e:
        print(f"❌ Config test failed: {e}")
        return False

def test_documents():
    """Test document loading."""
    print("\nTesting document loading...")
    
    try:
        from document_search import DocumentSearchEngine
        
        # This will fail if API key is not set, but we can test the import
        print("✅ DocumentSearchEngine imported successfully")
        
        # Check if documents directory exists
        if os.path.exists("documents"):
            print("✅ Documents directory exists")
            
            # Count .txt files
            txt_files = [f for f in os.listdir("documents") if f.endswith('.txt')]
            print(f"✅ Found {len(txt_files)} .txt files in documents directory")
            
            if txt_files:
                print("   Files found:")
                for file in txt_files:
                    print(f"   - {file}")
        else:
            print("❌ Documents directory not found")
            return False
        
        return True
    except Exception as e:
        print(f"❌ Document loading test failed: {e}")
        return False

def test_streamlit():
    """Test Streamlit app."""
    print("\nTesting Streamlit app...")
    
    try:
        import app
        print("✅ Streamlit app imported successfully")
        return True
    except Exception as e:
        print(f"❌ Streamlit app test failed: {e}")
        return False

def main():
    """Run all tests."""
    print("🔍 IntelliDocument Search - Installation Test")
    print("=" * 50)
    
    tests = [
        test_imports,
        test_config,
        test_documents,
        test_streamlit
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
    
    print("\n" + "=" * 50)
    print(f"Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Your installation is ready.")
        print("\nNext steps:")
        print("1. Set your Anthropic API key in a .env file")
        print("2. Run: streamlit run app.py")
        print("3. Open http://localhost:8501 in your browser")
    else:
        print("❌ Some tests failed. Please check the errors above.")
        print("\nTroubleshooting:")
        print("1. Make sure you're in the correct virtual environment")
        print("2. Run: pip install -r requirements.txt")
        print("3. Check that all dependencies are installed correctly")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 