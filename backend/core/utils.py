import os
from pathlib import Path

def get_backend_root() -> Path:
    """
    Get the absolute path to the backend directory.
    Assumes this file is in backend/core/utils.py
    """
    return Path(__file__).parent.parent.absolute()

def resolve_path(relative_path: str) -> str:
    """
    Resolves a relative path (like './model.pkl') to an absolute path
    relative to the backend directory.
    """
    if not relative_path:
        return ""
    
    p = Path(relative_path)
    
    # If it's already an absolute path, return it
    if p.is_absolute():
        return str(p)
    
    # Otherwise, resolve it relative to the backend root
    resolved = get_backend_root() / relative_path
    
    # Also handle the common case of leading ./
    if relative_path.startswith("./") or relative_path.startswith(".\\"):
        resolved = get_backend_root() / relative_path[2:]
        
    return str(resolved.absolute())
