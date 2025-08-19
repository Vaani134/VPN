

# === file_manager.py ===
"""
File Manager Module - Handles VPN file sharing functionality
"""

import os
import shutil
from datetime import datetime
from werkzeug.utils import secure_filename
import json

class FileManager:
    """Manages file sharing operations for VPN simulator"""
    
    def __init__(self, upload_folder):
        self.upload_folder = upload_folder
        self.metadata_file = os.path.join(upload_folder, '.file_metadata.json')
        self.metadata = self._load_metadata()
    
    def _load_metadata(self):
        """Load file metadata from JSON file"""
        try:
            if os.path.exists(self.metadata_file):
                with open(self.metadata_file, 'r') as f:
                    return json.load(f)
            return {}
        except Exception:
            return {}
    
    def _save_metadata(self):
        """Save file metadata to JSON file"""
        try:
            with open(self.metadata_file, 'w') as f:
                json.dump(self.metadata, f, indent=2)
        except Exception:
            pass
    
    def save_file(self, file, filename):
        """Save uploaded file and return metadata"""
        try:
            file_path = os.path.join(self.upload_folder, filename)
            file.save(file_path)
            
            # Get file stats
            file_stats = os.stat(file_path)
            file_size = file_stats.st_size
            
            # Create metadata
            file_info = {
                'filename': filename,
                'size': file_size,
                'size_mb': round(file_size / (1024 * 1024), 2),
                'upload_time': datetime.now().isoformat(),
                'path': file_path
            }
            
            # Store metadata
            self.metadata[filename] = file_info
            self._save_metadata()
            
            return file_info
            
        except Exception as e:
            return None
    
    def delete_file(self, filename):
        """Delete file and its metadata"""
        try:
            file_path = os.path.join(self.upload_folder, filename)
            
            if os.path.exists(file_path):
                os.remove(file_path)
                
                # Remove from metadata
                if filename in self.metadata:
                    del self.metadata[filename]
                    self._save_metadata()
                
                return True
            return False
            
        except Exception:
            return False
    
    def file_exists(self, filename):
        """Check if file exists"""
        file_path = os.path.join(self.upload_folder, filename)
        return os.path.exists(file_path)
    
    def get_file_info(self, filename):
        """Get file information"""
        if filename in self.metadata:
            return self.metadata[filename]
        
        # If not in metadata, generate it
        file_path = os.path.join(self.upload_folder, filename)
        if os.path.exists(file_path):
            file_stats = os.stat(file_path)
            return {
                'filename': filename,
                'size': file_stats.st_size,
                'size_mb': round(file_stats.st_size / (1024 * 1024), 2),
                'upload_time': datetime.fromtimestamp(file_stats.st_mtime).isoformat(),
                'path': file_path
            }
        return None
    
    def get_file_list(self):
        """Get list of all shared files with metadata"""
        files = []
        
        try:
            for filename in os.listdir(self.upload_folder):
                if filename.startswith('.'):  # Skip hidden files
                    continue
                
                file_info = self.get_file_info(filename)
                if file_info:
                    files.append(file_info)
            
            # Sort by upload time (newest first)
            files.sort(key=lambda x: x['upload_time'], reverse=True)
            return files
            
        except Exception:
            return []
    
    def get_transfer_stats(self):
        """Get file transfer statistics"""
        try:
            files = self.get_file_list()
            total_files = len(files)
            total_size = sum(f['size'] for f in files)
            total_size_mb = round(total_size / (1024 * 1024), 2)
            
            # Get file type distribution
            file_types = {}
            for file_info in files:
                ext = os.path.splitext(file_info['filename'])[1].lower()
                if not ext:
                    ext = 'no extension'
                file_types[ext] = file_types.get(ext, 0) + 1
            
            return {
                'total_files': total_files,
                'total_size_mb': total_size_mb,
                'file_types': file_types,
                'recent_files': files[:5]  # Last 5 files
            }
            
        except Exception:
            return {
                'total_files': 0,
                'total_size_mb': 0,
                'file_types': {},
                'recent_files': []
            }

