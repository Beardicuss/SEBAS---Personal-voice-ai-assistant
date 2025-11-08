# -*- coding: utf-8 -*-
"""
Advanced File Operations
Phase 3.1: Bulk File Management
"""

import logging
import os
import shutil
import re
import hashlib
from typing import List, Dict, Optional, Tuple, Callable, Set
from pathlib import Path
from datetime import datetime
import fnmatch


class FileOperations:
    """
    Advanced file operations for bulk file management.
    """
    
    def __init__(self):
        """Initialize File Operations."""
        self.operation_stats = {
            'files_processed': 0,
            'files_copied': 0,
            'files_moved': 0,
            'files_deleted': 0,
            'errors': 0,
            'bytes_processed': 0
        }
    
    def copy_recursive(self, source: str, destination: str,
                      pattern: Optional[str] = None,
                      exclude_patterns: Optional[List[str]] = None,
                      overwrite: bool = False,
                      progress_callback: Optional[Callable] = None) -> Tuple[bool, Dict]:
        """
        Recursively copy files from source to destination.
        
        Args:
            source: Source directory
            destination: Destination directory
            pattern: Optional file pattern (wildcards or regex)
            exclude_patterns: List of patterns to exclude
            overwrite: Whether to overwrite existing files
            progress_callback: Optional callback function(processed, total, current_file)
            
        Returns:
            Tuple of (success, stats_dict)
        """
        self.operation_stats = {
            'files_processed': 0,
            'files_copied': 0,
            'files_moved': 0,
            'files_deleted': 0,
            'errors': 0,
            'bytes_processed': 0
        }
        
        try:
            source_path = Path(source)
            dest_path = Path(destination)
            
            if not source_path.exists():
                return False, {'error': f'Source path does not exist: {source}'}
            
            # Create destination if it doesn't exist
            if source_path.is_dir():
                dest_path.mkdir(parents=True, exist_ok=True)
            else:
                dest_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Count total files first (for progress)
            if progress_callback:
                total = sum(1 for _ in self._walk_files(source_path, pattern, exclude_patterns))
                processed = 0
            
            # Copy files
            for file_path in self._walk_files(source_path, pattern, exclude_patterns):
                try:
                    rel_path = file_path.relative_to(source_path)
                    dest_file = dest_path / rel_path if source_path.is_dir() else dest_path
                    
                    # Check if destination exists
                    if dest_file.exists() and not overwrite:
                        self.operation_stats['errors'] += 1
                        continue
                    
                    # Create parent directory
                    dest_file.parent.mkdir(parents=True, exist_ok=True)
                    
                    # Copy file
                    shutil.copy2(file_path, dest_file)
                    
                    file_size = file_path.stat().st_size
                    self.operation_stats['files_copied'] += 1
                    self.operation_stats['files_processed'] += 1
                    self.operation_stats['bytes_processed'] += file_size
                    
                    if progress_callback:
                        processed += 1
                        progress_callback(processed, total, str(file_path))
                        
                except Exception as e:
                    logging.exception(f"Failed to copy {file_path}: {e}")
                    self.operation_stats['errors'] += 1
            
            return True, self.operation_stats.copy()
            
        except Exception:
            logging.exception(f"Failed to copy recursive from {source} to {destination}")
            return False, {'error': 'Copy operation failed'}
    
    def move_recursive(self, source: str, destination: str,
                      pattern: Optional[str] = None,
                      exclude_patterns: Optional[List[str]] = None,
                      overwrite: bool = False,
                      progress_callback: Optional[Callable] = None) -> Tuple[bool, Dict]:
        """
        Recursively move files from source to destination.
        
        Args:
            source: Source directory
            destination: Destination directory
            pattern: Optional file pattern (wildcards or regex)
            exclude_patterns: List of patterns to exclude
            overwrite: Whether to overwrite existing files
            progress_callback: Optional callback function
            
        Returns:
            Tuple of (success, stats_dict)
        """
        self.operation_stats = {
            'files_processed': 0,
            'files_copied': 0,
            'files_moved': 0,
            'files_deleted': 0,
            'errors': 0,
            'bytes_processed': 0
        }
        
        try:
            source_path = Path(source)
            dest_path = Path(destination)
            
            if not source_path.exists():
                return False, {'error': f'Source path does not exist: {source}'}
            
            # Create destination if needed
            if source_path.is_dir():
                dest_path.mkdir(parents=True, exist_ok=True)
            else:
                dest_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Count total files first
            if progress_callback:
                total = sum(1 for _ in self._walk_files(source_path, pattern, exclude_patterns))
                processed = 0
            
            # Move files
            for file_path in self._walk_files(source_path, pattern, exclude_patterns):
                try:
                    rel_path = file_path.relative_to(source_path)
                    dest_file = dest_path / rel_path if source_path.is_dir() else dest_path
                    
                    # Check if destination exists
                    if dest_file.exists() and not overwrite:
                        self.operation_stats['errors'] += 1
                        continue
                    
                    # Create parent directory
                    dest_file.parent.mkdir(parents=True, exist_ok=True)
                    
                    # Move file
                    shutil.move(str(file_path), str(dest_file))
                    
                    file_size = dest_file.stat().st_size
                    self.operation_stats['files_moved'] += 1
                    self.operation_stats['files_processed'] += 1
                    self.operation_stats['bytes_processed'] += file_size
                    
                    if progress_callback:
                        processed += 1
                        progress_callback(processed, total, str(file_path))
                        
                except Exception as e:
                    logging.exception(f"Failed to move {file_path}: {e}")
                    self.operation_stats['errors'] += 1
            
            return True, self.operation_stats.copy()
            
        except Exception:
            logging.exception(f"Failed to move recursive from {source} to {destination}")
            return False, {'error': 'Move operation failed'}
    
    def delete_recursive(self, path: str,
                        pattern: Optional[str] = None,
                        exclude_patterns: Optional[List[str]] = None,
                        dry_run: bool = False,
                        progress_callback: Optional[Callable] = None) -> Tuple[bool, Dict]:
        """
        Recursively delete files matching pattern.
        
        Args:
            path: Root path to delete from
            pattern: Optional file pattern (wildcards or regex)
            exclude_patterns: List of patterns to exclude
            dry_run: If True, don't actually delete, just report what would be deleted
            progress_callback: Optional callback function
            
        Returns:
            Tuple of (success, stats_dict)
        """
        self.operation_stats = {
            'files_processed': 0,
            'files_copied': 0,
            'files_moved': 0,
            'files_deleted': 0,
            'errors': 0,
            'bytes_processed': 0
        }
        
        try:
            root_path = Path(path)
            
            if not root_path.exists():
                return False, {'error': f'Path does not exist: {path}'}
            
            # Count total files first
            if progress_callback:
                total = sum(1 for _ in self._walk_files(root_path, pattern, exclude_patterns))
                processed = 0
            
            # Delete files
            files_to_delete = []
            for file_path in self._walk_files(root_path, pattern, exclude_patterns):
                files_to_delete.append(file_path)
            
            for file_path in files_to_delete:
                try:
                    file_size = file_path.stat().st_size
                    
                    if not dry_run:
                        if file_path.is_file():
                            file_path.unlink()
                        elif file_path.is_dir():
                            shutil.rmtree(file_path)
                    
                    self.operation_stats['files_deleted'] += 1
                    self.operation_stats['files_processed'] += 1
                    self.operation_stats['bytes_processed'] += file_size
                    
                    if progress_callback:
                        processed += 1
                        progress_callback(processed, total, str(file_path))
                        
                except Exception as e:
                    logging.exception(f"Failed to delete {file_path}: {e}")
                    self.operation_stats['errors'] += 1
            
            return True, self.operation_stats.copy()
            
        except Exception:
            logging.exception(f"Failed to delete recursive from {path}")
            return False, {'error': 'Delete operation failed'}
    
    def search_file_content(self, search_path: str, search_text: str,
                           file_pattern: Optional[str] = None,
                           case_sensitive: bool = False,
                           use_regex: bool = False,
                           max_results: int = 100) -> List[Dict]:
        """
        Search for text content in files.
        
        Args:
            search_path: Directory to search in
            file_pattern: Optional file pattern filter (e.g., "*.txt", "*.py")
            search_text: Text to search for
            case_sensitive: Whether search is case sensitive
            use_regex: Whether search_text is a regex pattern
            max_results: Maximum number of results to return
            
        Returns:
            List of dicts with file path and line matches
        """
        results = []
        
        try:
            root_path = Path(search_path)
            
            if not root_path.exists():
                return results
            
            # Compile regex if needed
            if use_regex:
                flags = 0 if case_sensitive else re.IGNORECASE
                pattern = re.compile(search_text, flags)
            else:
                pattern = None
                search_lower = search_text.lower() if not case_sensitive else search_text
            
            # Walk through files
            for file_path in self._walk_files(root_path, file_pattern):
                try:
                    # Skip binary files (basic check)
                    try:
                        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                            for line_num, line in enumerate(f, 1):
                                if len(results) >= max_results:
                                    return results
                                
                                match = False
                                if use_regex:
                                    if pattern.search(line):
                                        match = True
                                else:
                                    if case_sensitive:
                                        match = search_text in line
                                    else:
                                        match = search_lower in line.lower()
                                
                                if match:
                                    results.append({
                                        'file': str(file_path),
                                        'line': line_num,
                                        'content': line.strip()
                                    })
                    except (UnicodeDecodeError, PermissionError):
                        # Skip binary or inaccessible files
                        continue
                        
                except Exception:
                    logging.exception(f"Error searching in {file_path}")
                    continue
            
            return results
            
        except Exception:
            logging.exception(f"Failed to search file content in {search_path}")
            return results
    
    def find_duplicate_files(self, search_path: str,
                            file_pattern: Optional[str] = None,
                            min_size: int = 0,
                            hash_algorithm: str = 'md5') -> List[List[str]]:
        """
        Find duplicate files by content hash.
        
        Args:
            search_path: Directory to search in
            file_pattern: Optional file pattern filter
            min_size: Minimum file size in bytes to consider
            hash_algorithm: Hash algorithm ('md5', 'sha1', 'sha256')
            
        Returns:
            List of lists, each containing paths of duplicate files
        """
        file_hashes = {}
        duplicates = []
        
        try:
            root_path = Path(search_path)
            
            if not root_path.exists():
                return duplicates
            
            # Get hash function
            hash_func = {
                'md5': hashlib.md5,
                'sha1': hashlib.sha1,
                'sha256': hashlib.sha256
            }.get(hash_algorithm.lower(), hashlib.md5)
            
            # Calculate hashes
            for file_path in self._walk_files(root_path, file_pattern):
                try:
                    file_size = file_path.stat().st_size
                    
                    if file_size < min_size:
                        continue
                    
                    # Calculate file hash
                    file_hash = self._calculate_file_hash(file_path, hash_func)
                    
                    if file_hash:
                        if file_hash not in file_hashes:
                            file_hashes[file_hash] = []
                        file_hashes[file_hash].append(str(file_path))
                        
                except Exception:
                    logging.exception(f"Error processing {file_path}")
                    continue
            
            # Find duplicates
            for file_hash, paths in file_hashes.items():
                if len(paths) > 1:
                    duplicates.append(paths)
            
            return duplicates
            
        except Exception:
            logging.exception(f"Failed to find duplicate files in {search_path}")
            return duplicates

    # ----------------------- Compression Utilities (Phase 3) -----------------------
    def zip_path(self, source_path: str, archive_path: str, include_root: bool = True) -> Tuple[bool, Dict]:
        """Create a ZIP archive from a file or directory.

        Args:
            source_path: File or directory to compress
            archive_path: Destination .zip file path
            include_root: If True and source is a directory, include the top-level folder

        Returns:
            (success, details)
        """
        try:
            src = Path(source_path)
            if not src.exists():
                return False, {"error": f"Source not found: {source_path}"}
            archive_path = str(archive_path if archive_path.lower().endswith('.zip') else f"{archive_path}.zip")
            import zipfile
            with zipfile.ZipFile(archive_path, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
                if src.is_file():
                    zf.write(src, arcname=src.name)
                    return True, {"files": 1, "bytes": src.stat().st_size, "archive": archive_path}
                # Directory
                root = src if include_root else src
                base_len = len(str(src.parent)) + 1 if include_root else len(str(src)) + 1
                files = 0
                total_bytes = 0
                for dirpath, _, filenames in os.walk(src):
                    for name in filenames:
                        fp = Path(dirpath) / name
                        arcname = str(fp)[base_len:]
                        if include_root:
                            arcname = str(src.name / Path(arcname)) if hasattr(Path(src.name), 'joinpath') else f"{src.name}/{arcname}"
                        zf.write(fp, arcname=arcname)
                        files += 1
                        try:
                            total_bytes += fp.stat().st_size
                        except Exception:
                            pass
                return True, {"files": files, "bytes": total_bytes, "archive": archive_path}
        except Exception:
            logging.exception("zip_path failed")
            return False, {"error": "Zip operation failed"}

    def unzip_archive(self, archive_path: str, destination: str, overwrite: bool = False) -> Tuple[bool, Dict]:
        """Extract a ZIP archive to destination directory.

        Args:
            archive_path: .zip file path
            destination: directory to extract to
            overwrite: if True, allows overwriting existing files
        """
        try:
            import zipfile
            ap = Path(archive_path)
            if not ap.exists() or not ap.is_file():
                return False, {"error": f"Archive not found: {archive_path}"}
            dest = Path(destination)
            dest.mkdir(parents=True, exist_ok=True)
            files = 0
            bytes_total = 0
            with zipfile.ZipFile(ap, 'r') as zf:
                for info in zf.infolist():
                    target = dest / info.filename
                    if target.exists() and not overwrite:
                        continue
                    if info.is_dir():
                        target.mkdir(parents=True, exist_ok=True)
                    else:
                        target.parent.mkdir(parents=True, exist_ok=True)
                        with zf.open(info, 'r') as src, open(target, 'wb') as out:
                            data = src.read()
                            out.write(data)
                            bytes_total += len(data)
                        files += 1
            return True, {"files": files, "bytes": bytes_total, "destination": str(dest)}
        except Exception:
            logging.exception("unzip_archive failed")
            return False, {"error": "Unzip operation failed"}
    
    def _walk_files(self, root_path: Path, pattern: Optional[str] = None,
                   exclude_patterns: Optional[List[str]] = None):
        """Walk through files matching pattern."""
        if root_path.is_file():
            if self._matches_pattern(root_path, pattern, exclude_patterns):
                yield root_path
            return
        
        for dirpath, dirnames, filenames in os.walk(root_path):
            # Filter directories to exclude
            dirnames[:] = [d for d in dirnames if not self._should_exclude(d, exclude_patterns)]
            
            for filename in filenames:
                file_path = Path(dirpath) / filename
                if self._matches_pattern(file_path, pattern, exclude_patterns):
                    yield file_path
    
    def _matches_pattern(self, file_path: Path, pattern: Optional[str] = None,
                        exclude_patterns: Optional[List[str]] = None) -> bool:
        """Check if file matches pattern."""
        filename = file_path.name
        full_path = str(file_path)
        
        # Check exclude patterns first
        if exclude_patterns:
            for exclude in exclude_patterns:
                if fnmatch.fnmatch(filename, exclude) or fnmatch.fnmatch(full_path, exclude):
                    return False
                try:
                    if re.search(exclude, filename) or re.search(exclude, full_path):
                        return False
                except re.error:
                    pass
        
        # Check include pattern
        if pattern:
            if fnmatch.fnmatch(filename, pattern) or fnmatch.fnmatch(full_path, pattern):
                return True
            try:
                if re.search(pattern, filename) or re.search(pattern, full_path):
                    return True
            except re.error:
                pass
            return False
        
        return True
    
    def _should_exclude(self, name: str, exclude_patterns: Optional[List[str]] = None) -> bool:
        """Check if directory should be excluded."""
        if not exclude_patterns:
            return False
        
        for exclude in exclude_patterns:
            if fnmatch.fnmatch(name, exclude):
                return True
            try:
                if re.search(exclude, name):
                    return True
            except re.error:
                pass
        
        return False
    
    def _calculate_file_hash(self, file_path: Path, hash_func) -> Optional[str]:
        """Calculate hash of a file."""
        try:
            hash_obj = hash_func()
            with open(file_path, 'rb') as f:
                for chunk in iter(lambda: f.read(4096), b''):
                    hash_obj.update(chunk)
            return hash_obj.hexdigest()
        except Exception:
            logging.exception(f"Failed to calculate hash for {file_path}")
            return None

