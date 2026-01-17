import os
from typing import Optional

def get_secret(key: str, default: Optional[str] = None) -> str:
    """Get secret from os.getenv or st.secrets.
    
    Tries to load from environment variable first, then Streamlit secrets.
    """
    value = os.getenv(key)
    if value:
        return value
    
    try:
        import streamlit as st
        return st.secrets.get(key, default) or default or ""
    except (ImportError, FileNotFoundError):
        return default or ""

