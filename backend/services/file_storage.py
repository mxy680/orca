"""
File Storage - Manages user files (datasets, etc.).

Files are stored on host filesystem and mounted into user's Docker container.
"""
import os
from pathlib import Path
from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)


class FileStorage:
    """Manages file storage for users."""
    
    def __init__(self):
        self.workspace_root = Path(os.getenv("WORKSPACE_ROOT", "./workspace"))
        self.workspace_root.mkdir(parents=True, exist_ok=True)
    
    def store_file(self, user_id: str, file_content: bytes, filename: str) -> Dict[str, Any]:
        """
        Store a file for a user.
        
        Args:
            user_id: User identifier
            file_content: File content as bytes
            filename: Name of the file
            
        Returns:
            Dictionary with file metadata
        """
        # Create user directory if doesn't exist
        user_dir = self.workspace_root / user_id
        user_dir.mkdir(parents=True, exist_ok=True)
        
        # Save file
        file_path = user_dir / filename
        with open(file_path, 'wb') as f:
            f.write(file_content)
        
        file_size = file_path.stat().st_size
        
        logger.info(f"Stored file {filename} for user {user_id} ({file_size} bytes)")
        
        return {
            'path': str(file_path),
            'size': file_size,
            'filename': filename,
            'user_id': user_id
        }
    
    def get_user_files(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Get list of files for a user.
        
        Args:
            user_id: User identifier
            
        Returns:
            List of file metadata dictionaries
        """
        user_dir = self.workspace_root / user_id
        
        if not user_dir.exists():
            return []
        
        files = []
        for file_path in user_dir.iterdir():
            if file_path.is_file():
                stat = file_path.stat()
                files.append({
                    'name': file_path.name,
                    'size': stat.st_size,
                    'modified': stat.st_mtime
                })
        
        return files
    
    def get_file_path(self, user_id: str, filename: str) -> Path:
        """
        Get full path to a user's file.
        
        Args:
            user_id: User identifier
            filename: Name of the file
            
        Returns:
            Path object
        """
        return self.workspace_root / user_id / filename
    
    def delete_file(self, user_id: str, filename: str) -> bool:
        """
        Delete a user's file.
        
        Args:
            user_id: User identifier
            filename: Name of the file
            
        Returns:
            True if deleted, False if not found
        """
        file_path = self.get_file_path(user_id, filename)
        
        if file_path.exists():
            file_path.unlink()
            logger.info(f"Deleted file {filename} for user {user_id}")
            return True
        
        return False

