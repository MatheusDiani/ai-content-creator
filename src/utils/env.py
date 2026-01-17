import os
from typing import Optional

def get_secret(key: str, default: Optional[str] = None) -> str:
    """Get secret from os.getenv or st.secrets.
    
    Tries to load from environment variable first, then Streamlit secrets.
    """
    value = os.getenv(key)
    if value:
        print(f"DEBUG: Found {key} in environment variables")
        return value
    
    try:
        import streamlit as st
        secret_value = st.secrets.get(key, default)
        if secret_value:
             print(f"DEBUG: Found {key} in Streamlit secrets")
             return secret_value
        else:
             print(f"DEBUG: {key} NOT found in Streamlit secrets")
             return default or ""
    except (ImportError, FileNotFoundError):
        print(f"DEBUG: Could not access Streamlit secrets for {key}")
        return default or ""
