# -*- coding: utf-8 -*-
"""
File Skill - Handles file operations like create, search, open with advanced features
"""

from datetime import datetime, timedelta
from pathlib import Path
from sebas.skills.base_skill import BaseSkill
from typing import Dict, List, Any, Optional, Tuple
import logging
import os
import shutil
import time
import json
import threading
import mimetypes
import fnmatch
try:
    import win32api
    import win32con
    WIN32_AVAILABLE = True
except ImportError:
    WIN32_AVAILABLE = False
    logging.warning("pywin32 not available, some file operations may be limited")


class FileSkill(BaseSkill):
    """
    Skill for handling file and folder operations with advanced features.
    """

    def __init__(self, assistant_ref):
        super().__init__(assistant_ref)
        self.recent_files_file = os.path.join(os.path.expanduser('~'), '.sebas_recent_files.json')
        self.file_cache_file = os.path.join(os.path.expanduser('~'), '.sebas_file_cache.json')
        self.search_config_file = os.path.join(os.path.expanduser('~'), '.sebas_search_config.json')
        self.recent_files = self._load_recent_files()
        self.file_cache = self._load_file_cache()
        self.search_config = self._load_search_config()
        self.cache_lock = threading.RLock()
        self.recent_lock = threading.RLock()

        # Default search paths and exclusions
        self.default_search_paths = [
            os.path.expanduser('~'),
            os.path.join(os.path.expanduser('~'), 'Documents'),
            os.path.join(os.path.expanduser('~'), 'Desktop'),
            os.path.join(os.path.expanduser('~'), 'Downloads'),
        ]

        self.default_exclusions = [
            '.git', '__pycache__', 'node_modules', '.venv', 'build', 'dist',
            '*.tmp', '*.temp', '*.log', 'Thumbs.db', 'desktop.ini'
        ]

    def get_intents(self) -> List[str]:
        return [
            'create_folder',
            'delete_path',
            'search_files',
            'open_file',
            'open_recent_file',
            'list_recent_files',
            'move_file',
            'copy_file',
            'rename_file',
            'show_file_info',
            'preview_file',
            'search_files_advanced',
            'find_files_by_type',
            'find_files_by_date',
            'configure_search_paths',
            'backup_file',
            # Phase 3.1: Advanced file operations
            'copy_recursive',
            'move_recursive',
            'delete_recursive',
            'search_file_content',
            'find_duplicate_files',
            # Phase 3: Compression utilities
            'compress_path',
            'extract_archive',
            # Phase 3: Cloud sync scaffolding
            'cloud_backup'
        ]

    def can_handle(self, intent: str) -> bool:
        return intent in self.get_intents()

    def handle(self, intent: str, slots: Dict[str, Any]) -> bool:
        try:
            if intent == 'create_folder':
                return self._handle_create_folder(slots)
            elif intent == 'delete_path':
                return self._handle_delete_path(slots)
            elif intent == 'search_files':
                return self._handle_search_files(slots)
            elif intent == 'open_file':
                return self._handle_open_file(slots)
            elif intent == 'open_recent_file':
                return self._handle_open_recent_file(slots)
            elif intent == 'list_recent_files':
                return self._handle_list_recent_files()
            elif intent == 'move_file':
                return self._handle_move_file(slots)
            elif intent == 'copy_file':
                return self._handle_copy_file(slots)
            elif intent == 'rename_file':
                return self._handle_rename_file(slots)
            elif intent == 'show_file_info':
                return self._handle_show_file_info(slots)
            elif intent == 'preview_file':
                return self._handle_preview_file(slots)
            elif intent == 'search_files_advanced':
                return self._handle_search_files_advanced(slots)
            elif intent == 'find_files_by_type':
                return self._handle_find_files_by_type(slots)
            elif intent == 'find_files_by_date':
                return self._handle_find_files_by_date(slots)
            elif intent == 'configure_search_paths':
                return self._handle_configure_search_paths(slots)
            elif intent == 'backup_file':
                return self._handle_backup_file(slots)
            # Phase 3.1: Advanced file operations
            elif intent == 'copy_recursive':
                return self._handle_copy_recursive(slots)
            elif intent == 'move_recursive':
                return self._handle_move_recursive(slots)
            elif intent == 'delete_recursive':
                return self._handle_delete_recursive(slots)
            elif intent == 'search_file_content':
                return self._handle_search_file_content(slots)
            elif intent == 'find_duplicate_files':
                return self._handle_find_duplicate_files(slots)
            elif intent == 'compress_path':
                return self._handle_compress_path(slots)
            elif intent == 'extract_archive':
                return self._handle_extract_archive(slots)
            elif intent == 'cloud_backup':
                return self._handle_cloud_backup(slots)
            return False
        except Exception as e:
            self.logger.exception(f"Error handling file intent {intent}")
            self.assistant.speak("An error occurred while executing that command")
            return False

    def _handle_create_folder(self, slots: Dict[str, Any]) -> bool:
        folder_path = slots.get('path', '').strip().strip('"')
        if folder_path and self.assistant._validate_safe_path(folder_path):
            self.assistant.create_folder(folder_path)
            return True
        else:
            self.assistant.speak("Please specify a valid folder path")
            return False

    def _handle_delete_path(self, slots: Dict[str, Any]) -> bool:
        path = slots.get('path', '').strip().strip('"')
        if path and self.assistant._validate_safe_path(path):
            if self.assistant.confirm_action(f"Are you sure you want to delete {path}?"):
                self.assistant.delete_path(path)
                return True
        else:
            self.assistant.speak("Please specify a valid file or folder path to delete")
        return False

    def _handle_search_files(self, slots: Dict[str, Any]) -> bool:
        query = slots.get('query', '')
        if query:
            # Enhanced search - find files by content or name
            results = self._advanced_file_search(query)
            if results:
                # Open first result and list others
                first_result = results[0]
                try:
                    os.startfile(first_result)
                    self.assistant.speak(f"Opening {os.path.basename(first_result)}. Found {len(results)} matching files.")
                except Exception:
                    self.assistant.speak(f"Found {len(results)} files matching '{query}'")
                return True
            else:
                # Fallback to Windows search
                import subprocess
                try:
                    subprocess.run(['explorer.exe', f'search-ms:query={query}'], check=False)
                    self.assistant.speak(f"Searching for {query}")
                    return True
                except Exception:
                    self.assistant.speak("Search functionality not available")
                    return False
        else:
            self.assistant.speak("Please specify what to search for")
            return False

    def _handle_open_file(self, slots: Dict[str, Any]) -> bool:
        file_path = slots.get('path', '').strip().strip('"')
        if file_path and os.path.exists(file_path):
            try:
                os.startfile(file_path)
                self.assistant.speak(f"Opening {os.path.basename(file_path)}")
                self._track_recent_file(file_path)
                return True
            except Exception:
                self.assistant.speak("Could not open the file")
                return False
        else:
            self.assistant.speak("File not found")
            return False

    # ----------------------- Advanced File Management Methods -----------------------

    def _handle_open_recent_file(self, slots: Dict[str, Any]) -> bool:
        index = slots.get('index', 1)
        try:
            index = int(index) - 1  # Convert to 0-based
        except ValueError:
            index = 0

        with self.recent_lock:
            if index < len(self.recent_files):
                file_path = self.recent_files[index]['path']
                if os.path.exists(file_path):
                    try:
                        os.startfile(file_path)
                        self.assistant.speak(f"Opening {os.path.basename(file_path)}")
                        self._track_recent_file(file_path)
                        return True
                    except Exception as e:
                        self.logger.exception(f"Failed to open recent file {file_path}")
                        self.assistant.speak("Failed to open the file")
                        return False
                else:
                    self.assistant.speak("File no longer exists")
                    # Remove from recent files
                    self.recent_files.pop(index)
                    self._save_recent_files()
                    return False
            else:
                self.assistant.speak("No recent file at that position")
                return False

    def _handle_list_recent_files(self) -> bool:
        with self.recent_lock:
            if not self.recent_files:
                self.assistant.speak("No recent files")
                return True

            recent_list = []
            for i, file_info in enumerate(self.recent_files[:10], 1):
                filename = os.path.basename(file_info['path'])
                recent_list.append(f"{i}. {filename}")

            self.assistant.speak(f"Recent files: {', '.join(recent_list)}")
            return True

    def _handle_move_file(self, slots: Dict[str, Any]) -> bool:
        source = slots.get('source', '').strip().strip('"')
        destination = slots.get('destination', '').strip().strip('"')

        if not source or not destination:
            self.assistant.speak("Please specify source and destination paths")
            return False

        if not os.path.exists(source):
            self.assistant.speak("Source file not found")
            return False

        # Safety check
        if not self._is_safe_file_operation(source, destination):
            self.assistant.speak("Operation not allowed for safety reasons")
            return False

        # Confirm destructive operation
        if os.path.exists(destination):
            if not self.assistant.confirm_action(f"Destination {destination} already exists. Overwrite?"):
                return True  # User cancelled, but not an error

        try:
            shutil.move(source, destination)
            self.assistant.speak("File moved successfully")
            return True
        except Exception as e:
            self.logger.exception(f"Failed to move file from {source} to {destination}")
            self.assistant.speak("Failed to move file")
            return False

    def _handle_copy_file(self, slots: Dict[str, Any]) -> bool:
        source = slots.get('source', '').strip().strip('"')
        destination = slots.get('destination', '').strip().strip('"')

        if not source or not destination:
            self.assistant.speak("Please specify source and destination paths")
            return False

        if not os.path.exists(source):
            self.assistant.speak("Source file not found")
            return False

        # Safety check
        if not self._is_safe_file_operation(source, destination):
            self.assistant.speak("Operation not allowed for safety reasons")
            return False

        try:
            if os.path.isdir(source):
                shutil.copytree(source, destination)
                self.assistant.speak("Folder copied successfully")
            else:
                shutil.copy2(source, destination)
                self.assistant.speak("File copied successfully")
            return True
        except Exception as e:
            self.logger.exception(f"Failed to copy from {source} to {destination}")
            self.assistant.speak("Failed to copy")
            return False

    def _handle_rename_file(self, slots: Dict[str, Any]) -> bool:
        old_path = slots.get('old_path', '').strip().strip('"')
        new_name = slots.get('new_name', '').strip()

        if not old_path or not new_name:
            self.assistant.speak("Please specify file path and new name")
            return False

        if not os.path.exists(old_path):
            self.assistant.speak("File not found")
            return False

        directory = os.path.dirname(old_path)
        new_path = os.path.join(directory, new_name)

        # Safety check
        if not self._is_safe_file_operation(old_path, new_path):
            self.assistant.speak("Operation not allowed for safety reasons")
            return False

        if os.path.exists(new_path):
            if not self.assistant.confirm_action(f"File {new_name} already exists. Overwrite?"):
                return True

        try:
            os.rename(old_path, new_path)
            self.assistant.speak("File renamed successfully")
            return True
        except Exception as e:
            self.logger.exception(f"Failed to rename {old_path} to {new_path}")
            self.assistant.speak("Failed to rename file")
            return False

    def _handle_show_file_info(self, slots: Dict[str, Any]) -> bool:
        file_path = slots.get('path', '').strip().strip('"')
        if not file_path or not os.path.exists(file_path):
            self.assistant.speak("File not found")
            return False

        try:
            stat = os.stat(file_path)
            file_size = self._format_file_size(stat.st_size)
            modified_time = datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S')
            created_time = datetime.fromtimestamp(stat.st_ctime).strftime('%Y-%m-%d %H:%M:%S')
            file_type = self._get_file_type(file_path)

            info = f"File: {os.path.basename(file_path)}, Size: {file_size}, Type: {file_type}, Modified: {modified_time}"
            self.assistant.speak(info)
            return True
        except Exception as e:
            self.logger.exception(f"Failed to get info for {file_path}")
            self.assistant.speak("Failed to get file information")
            return False

    def _handle_preview_file(self, slots: Dict[str, Any]) -> bool:
        file_path = slots.get('path', '').strip().strip('"')
        if not file_path or not os.path.exists(file_path):
            self.assistant.speak("File not found")
            return False

        try:
            if os.path.isdir(file_path):
                # Preview directory contents
                items = os.listdir(file_path)
                files_count = len([i for i in items if os.path.isfile(os.path.join(file_path, i))])
                dirs_count = len([i for i in items if os.path.isdir(os.path.join(file_path, i))])
                self.assistant.speak(f"Folder contains {files_count} files and {dirs_count} folders")
                return True

            # Preview file content
            file_type = self._get_file_type(file_path)
            if file_type.startswith('text/') or file_path.lower().endswith(('.txt', '.py', '.js', '.html', '.css', '.json', '.xml', '.md')):
                # Text file preview
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read(500)  # First 500 characters
                        if len(content) == 500:
                            content += "..."
                        self.assistant.speak(f"File preview: {content}")
                        return True
                except Exception:
                    pass

            # For other files, show metadata
            stat = os.stat(file_path)
            file_size = self._format_file_size(stat.st_size)
            self.assistant.speak(f"{os.path.basename(file_path)}: {file_type}, {file_size}")
            return True

        except Exception as e:
            self.logger.exception(f"Failed to preview {file_path}")
            self.assistant.speak("Failed to preview file")
            return False

    def _handle_search_files_advanced(self, slots: Dict[str, Any]) -> bool:
        query = slots.get('query', '')
        file_type = slots.get('file_type', '')
        location = slots.get('location', '')

        if not query:
            self.assistant.speak("Please specify what to search for")
            return False

        results = self._advanced_file_search(query, file_type=file_type, location=location)
        if results:
            # Open first result and summarize others
            first_result = results[0]
            try:
                os.startfile(first_result)
                self.assistant.speak(f"Opening {os.path.basename(first_result)}. Found {len(results)} matching files.")
            except Exception:
                self.assistant.speak(f"Found {len(results)} files matching '{query}'")
            return True
        else:
            self.assistant.speak("No matching files found")
            return False

    def _handle_find_files_by_type(self, slots: Dict[str, Any]) -> bool:
        file_type = slots.get('file_type', '').lower()
        location = slots.get('location', '')

        if not file_type:
            self.assistant.speak("Please specify file type")
            return False

        # Map common type names to extensions
        type_extensions = {
            'pdf': ['*.pdf'],
            'word': ['*.doc', '*.docx'],
            'excel': ['*.xls', '*.xlsx'],
            'powerpoint': ['*.ppt', '*.pptx'],
            'image': ['*.jpg', '*.jpeg', '*.png', '*.gif', '*.bmp', '*.tiff'],
            'video': ['*.mp4', '*.avi', '*.mkv', '*.mov', '*.wmv'],
            'audio': ['*.mp3', '*.wav', '*.flac', '*.aac'],
            'text': ['*.txt', '*.rtf'],
            'code': ['*.py', '*.js', '*.html', '*.css', '*.java', '*.cpp', '*.c', '*.cs']
        }

        extensions = type_extensions.get(file_type, [f'*.{file_type}'])
        results = self._search_by_extensions(extensions, location)

        if results:
            self.assistant.speak(f"Found {len(results)} {file_type} files")
            # Open first result
            try:
                os.startfile(results[0])
            except Exception:
                pass
            return True
        else:
            self.assistant.speak(f"No {file_type} files found")
            return False

    def _handle_find_files_by_date(self, slots: Dict[str, Any]) -> bool:
        date_filter = slots.get('date_filter', '').lower()
        location = slots.get('location', '')

        if not date_filter:
            self.assistant.speak("Please specify date filter (today, yesterday, week, month)")
            return False

        # Parse date filter
        now = datetime.now()
        if date_filter == 'today':
            start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
        elif date_filter == 'yesterday':
            start_date = (now - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        elif date_filter == 'week':
            start_date = now - timedelta(days=7)
        elif date_filter == 'month':
            start_date = now - timedelta(days=30)
        else:
            self.assistant.speak("Invalid date filter")
            return False

        results = self._search_by_date(start_date, location)
        if results:
            self.assistant.speak(f"Found {len(results)} files modified since {date_filter}")
            # Open first result
            try:
                os.startfile(results[0])
            except Exception:
                pass
            return True
        else:
            self.assistant.speak(f"No files found modified since {date_filter}")
            return False

    def _handle_configure_search_paths(self, slots: Dict[str, Any]) -> bool:
        action = slots.get('action', '').lower()
        path = slots.get('path', '').strip().strip('"')

        if action == 'add' and path:
            if os.path.isdir(path):
                with self.cache_lock:
                    if 'custom_search_paths' not in self.search_config:
                        self.search_config['custom_search_paths'] = []
                    if path not in self.search_config['custom_search_paths']:
                        self.search_config['custom_search_paths'].append(path)
                        self._save_search_config()
                        self.assistant.speak("Search path added")
                    else:
                        self.assistant.speak("Path already in search paths")
                return True
            else:
                self.assistant.speak("Invalid directory path")
                return False

        elif action == 'remove' and path:
            with self.cache_lock:
                if 'custom_search_paths' in self.search_config and path in self.search_config['custom_search_paths']:
                    self.search_config['custom_search_paths'].remove(path)
                    self._save_search_config()
                    self.assistant.speak("Search path removed")
                else:
                    self.assistant.speak("Path not found in search paths")
            return True

        elif action == 'list':
            paths = self.default_search_paths.copy()
            with self.cache_lock:
                custom_paths = self.search_config.get('custom_search_paths', [])
                paths.extend(custom_paths)

            path_names = [os.path.basename(p) if os.path.exists(p) else f"{os.path.basename(p)} (not found)" for p in paths]
            self.assistant.speak(f"Search paths: {', '.join(path_names)}")
            return True

        else:
            self.assistant.speak("Please specify action (add, remove, list) and optionally a path")
            return False

    def _handle_backup_file(self, slots: Dict[str, Any]) -> bool:
        file_path = slots.get('path', '').strip().strip('"')
        if not file_path or not os.path.exists(file_path):
            self.assistant.speak("File not found")
            return False

        try:
            # Create backup in same directory with timestamp
            base, ext = os.path.splitext(file_path)
            backup_path = f"{base}_backup_{int(time.time())}{ext}"

            if os.path.isdir(file_path):
                shutil.copytree(file_path, backup_path)
            else:
                shutil.copy2(file_path, backup_path)

            self.assistant.speak(f"Backup created: {os.path.basename(backup_path)}")
            return True
        except Exception as e:
            self.logger.exception(f"Failed to backup {file_path}")
            self.assistant.speak("Failed to create backup")
            return False
    
    # Phase 3.1: Advanced file operation handlers
    def _handle_copy_recursive(self, slots: Dict[str, Any]) -> bool:
        """Handle recursive copy command."""
        if not self.assistant.has_permission('copy_recursive'):
            return False
        
        if not self.file_ops:
            self.assistant.speak("Advanced file operations not available")
            return False
        
        try:
            source = slots.get('source', '').strip().strip('"')
            destination = slots.get('destination', '').strip().strip('"')
            pattern = slots.get('pattern')
            overwrite = slots.get('overwrite', False)
            
            if not source or not destination:
                self.assistant.speak("Please specify source and destination paths")
                return False
            
            if not self.assistant.confirm_action(f"Copy files from {source} to {destination}?"):
                return False
            
            success, result = self.file_ops.copy_recursive(
                source=source,
                destination=destination,
                pattern=pattern,
                overwrite=overwrite
            )
            
            if success:
                files_copied = result.get('files_copied', 0)
                self.assistant.speak(f"Copied {files_copied} files successfully")
            else:
                error = result.get('error', 'Unknown error')
                self.assistant.speak(f"Copy failed: {error}")
            
            return success
            
        except Exception:
            logging.exception("Failed to copy recursive")
            self.assistant.speak("Failed to copy files")
            return False
    
    def _handle_move_recursive(self, slots: Dict[str, Any]) -> bool:
        """Handle recursive move command."""
        if not self.assistant.has_permission('move_recursive'):
            return False
        
        if not self.file_ops:
            self.assistant.speak("Advanced file operations not available")
            return False
        
        try:
            source = slots.get('source', '').strip().strip('"')
            destination = slots.get('destination', '').strip().strip('"')
            pattern = slots.get('pattern')
            overwrite = slots.get('overwrite', False)
            
            if not source or not destination:
                self.assistant.speak("Please specify source and destination paths")
                return False
            
            if not self.assistant.confirm_action(f"Move files from {source} to {destination}?"):
                return False
            
            success, result = self.file_ops.move_recursive(
                source=source,
                destination=destination,
                pattern=pattern,
                overwrite=overwrite
            )
            
            if success:
                files_moved = result.get('files_moved', 0)
                self.assistant.speak(f"Moved {files_moved} files successfully")
            else:
                error = result.get('error', 'Unknown error')
                self.assistant.speak(f"Move failed: {error}")
            
            return success
            
        except Exception:
            logging.exception("Failed to move recursive")
            self.assistant.speak("Failed to move files")
            return False
    
    def _handle_delete_recursive(self, slots: Dict[str, Any]) -> bool:
        """Handle recursive delete command."""
        if not self.assistant.has_permission('delete_recursive'):
            return False
        
        if not self.file_ops:
            self.assistant.speak("Advanced file operations not available")
            return False
        
        try:
            path = slots.get('path', '').strip().strip('"')
            pattern = slots.get('pattern')
            dry_run = slots.get('dry_run', False)
            
            if not path:
                self.assistant.speak("Please specify a path")
                return False
            
            if not self.assistant.confirm_action(f"Delete files matching pattern in {path}?"):
                return False
            
            success, result = self.file_ops.delete_recursive(
                path=path,
                pattern=pattern,
                dry_run=dry_run
            )
            
            if success:
                files_deleted = result.get('files_deleted', 0)
                if dry_run:
                    self.assistant.speak(f"Would delete {files_deleted} files (dry run)")
                else:
                    self.assistant.speak(f"Deleted {files_deleted} files successfully")
            else:
                error = result.get('error', 'Unknown error')
                self.assistant.speak(f"Delete failed: {error}")
            
            return success
            
        except Exception:
            logging.exception("Failed to delete recursive")
            self.assistant.speak("Failed to delete files")
            return False
    
    def _handle_search_file_content(self, slots: Dict[str, Any]) -> bool:
        """Handle search file content command."""
        try:
            if not self.file_ops:
                self.assistant.speak("Advanced file operations not available")
                return False
            
            search_path = slots.get('path', os.path.expanduser('~'))
            search_text = slots.get('text', '')
            file_pattern = slots.get('pattern')
            case_sensitive = slots.get('case_sensitive', False)
            use_regex = slots.get('use_regex', False)
            
            if not search_text:
                self.assistant.speak("Please specify text to search for")
                return False
            
            results = self.file_ops.search_file_content(
                search_path=search_path,
                search_text=search_text,
                file_pattern=file_pattern,
                case_sensitive=case_sensitive,
                use_regex=use_regex,
                max_results=50
            )
            
            if results:
                count = len(results)
                files_found = len(set(r['file'] for r in results))
                self.assistant.speak(f"Found {count} matches in {files_found} files")
            else:
                self.assistant.speak("No matches found")
            
            return True
            
        except Exception:
            logging.exception("Failed to search file content")
            self.assistant.speak("Failed to search file content")
            return False
    
    def _handle_find_duplicate_files(self, slots: Dict[str, Any]) -> bool:
        """Handle find duplicate files command."""
        try:
            if not self.file_ops:
                self.assistant.speak("Advanced file operations not available")
                return False
            
            search_path = slots.get('path', os.path.expanduser('~'))
            file_pattern = slots.get('pattern')
            min_size = slots.get('min_size', 0)
            
            duplicates = self.file_ops.find_duplicate_files(
                search_path=search_path,
                file_pattern=file_pattern,
                min_size=min_size
            )
            
            if duplicates:
                total_duplicates = sum(len(group) for group in duplicates)
                groups = len(duplicates)
                self.assistant.speak(f"Found {groups} groups of duplicate files ({total_duplicates} total files)")
            else:
                self.assistant.speak("No duplicate files found")
            
            return True
            
        except Exception:
            logging.exception("Failed to find duplicate files")
            self.assistant.speak("Failed to find duplicate files")
            return False

    # ----------------------- Compression Handlers (Phase 3) -----------------------
    def _handle_compress_path(self, slots: Dict[str, Any]) -> bool:
        try:
            source = slots.get('path', '').strip().strip('"')
            archive = slots.get('archive', '').strip().strip('"')
            include_root = bool(slots.get('include_root', True))
            if not source:
                self.assistant.speak("Please specify a file or folder to compress")
                return False
            if not archive:
                base = os.path.basename(source.rstrip(os.sep)) or 'archive'
                archive = os.path.join(os.path.dirname(source), f"{base}.zip")
            if not hasattr(self, 'file_ops') or self.file_ops is None:
                try:
                    from sebas.integrations.file_operations import FileOperations
                    self.file_ops = FileOperations()
                except Exception:
                    self.assistant.speak("Compression utilities not available")
                    return False
            success, info = self.file_ops.zip_path(source, archive, include_root=include_root)
            if success:
                self.assistant.speak(f"Archive created: {os.path.basename(info.get('archive', archive))}")
                return True
            else:
                self.assistant.speak(f"Compression failed: {info.get('error', 'unknown error')}")
                return False
        except Exception:
            self.logger.exception("compress_path failed")
            self.assistant.speak("Failed to create archive")
            return False

    def _handle_extract_archive(self, slots: Dict[str, Any]) -> bool:
        try:
            archive = slots.get('archive', '').strip().strip('"')
            destination = slots.get('destination', '').strip().strip('"') or os.path.dirname(archive)
            overwrite = bool(slots.get('overwrite', False))
            if not archive:
                self.assistant.speak("Please specify an archive to extract")
                return False
            if not hasattr(self, 'file_ops') or self.file_ops is None:
                try:
                    from sebas.integrations.file_operations import FileOperations
                    self.file_ops = FileOperations()
                except Exception:
                    self.assistant.speak("Extraction utilities not available")
                    return False
            success, info = self.file_ops.unzip_archive(archive, destination, overwrite=overwrite)
            if success:
                self.assistant.speak(f"Archive extracted to {destination}")
                return True
            else:
                self.assistant.speak(f"Extraction failed: {info.get('error', 'unknown error')}")
                return False
        except Exception:
            self.logger.exception("extract_archive failed")
            self.assistant.speak("Failed to extract archive")
            return False

    # ----------------------- Cloud Backup (Scaffold) -----------------------
    def _handle_cloud_backup(self, slots: Dict[str, Any]) -> bool:
        try:
            provider = (slots.get('provider') or '').lower()  # 'onedrive' or 'google'
            path = slots.get('path', '').strip().strip('"')
            if not provider or not path:
                self.assistant.speak("Please specify provider and path")
                return False
            try:
                from sebas.integrations.cloud_sync import CloudSync
            except Exception:
                self.assistant.speak("Cloud sync not available in this build")
                return False
            client = CloudSync.from_env(provider)
            if client is None:
                self.assistant.speak("Cloud credentials not configured. Please set environment variables.")
                return False
            ok, info = client.upload_path(path)
            if ok:
                self.assistant.speak("Backup completed successfully")
                return True
            else:
                self.assistant.speak(f"Backup failed: {info.get('error', 'unknown error')}")
                return False
        except Exception:
            self.logger.exception("cloud_backup failed")
            self.assistant.speak("Cloud backup failed")
            return False

    # ----------------------- Helper Methods -----------------------

    def _load_recent_files(self) -> List[Dict[str, Any]]:
        try:
            if os.path.isfile(self.recent_files_file):
                with open(self.recent_files_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        return data
            return []
        except Exception as e:
            self.logger.exception("Failed to load recent files")
            return []

    def _save_recent_files(self):
        try:
            with self.recent_lock:
                with open(self.recent_files_file, 'w', encoding='utf-8') as f:
                    json.dump(self.recent_files, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.logger.exception("Failed to save recent files")

    def _load_file_cache(self) -> Dict[str, Any]:
        try:
            if os.path.isfile(self.file_cache_file):
                with open(self.file_cache_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return {}
        except Exception as e:
            self.logger.exception("Failed to load file cache")
            return {}

    def _load_search_config(self) -> Dict[str, Any]:
        try:
            if os.path.isfile(self.search_config_file):
                with open(self.search_config_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return {}
        except Exception as e:
            self.logger.exception("Failed to load search config")
            return {}

    def _save_search_config(self):
        try:
            with open(self.search_config_file, 'w', encoding='utf-8') as f:
                json.dump(self.search_config, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.logger.exception("Failed to save search config")

    def _track_recent_file(self, file_path: str):
        """Track recently opened files"""
        try:
            with self.recent_lock:
                # Remove if already exists
                self.recent_files = [f for f in self.recent_files if f['path'] != file_path]

                # Add to beginning
                self.recent_files.insert(0, {
                    'path': file_path,
                    'opened_at': time.time(),
                    'basename': os.path.basename(file_path)
                })

                # Keep only last 20
                self.recent_files = self.recent_files[:20]

                # Save periodically
                if len(self.recent_files) % 5 == 0:
                    self._save_recent_files()
        except Exception as e:
            self.logger.exception("Failed to track recent file")

    def _is_safe_file_operation(self, source: str, destination: str) -> bool:
        """Check if file operation is safe"""
        try:
            # Get absolute paths
            source_abs = os.path.abspath(source)
            dest_abs = os.path.abspath(destination)

            # Prevent operations on system directories
            system_dirs = [
                os.path.join(os.environ.get('SystemRoot', 'C:\\Windows')),
                os.path.join(os.environ.get('SystemRoot', 'C:\\Windows'), 'System32'),
                os.environ.get('ProgramFiles', ''),
                os.environ.get('ProgramFiles(x86)', '')
            ]

            for sys_dir in system_dirs:
                if sys_dir and (source_abs.startswith(sys_dir) or dest_abs.startswith(sys_dir)):
                    return False

            # Prevent operations in root directories
            if len(source_abs.split(os.sep)) <= 2 or len(dest_abs.split(os.sep)) <= 2:
                return False

            return True
        except Exception:
            return False

    def _advanced_file_search(self, query: str, file_type: str = '', location: str = '') -> List[str]:
        """Advanced file search with multiple strategies"""
        results = []

        # Determine search paths
        search_paths = self.default_search_paths.copy()
        if location and os.path.isdir(location):
            search_paths = [location]
        elif hasattr(self, 'search_config'):
            custom_paths = self.search_config.get('custom_search_paths', [])
            search_paths.extend(custom_paths)

        # Search each path
        for search_path in search_paths:
            if not os.path.exists(search_path):
                continue

            try:
                for root, dirs, files in os.walk(search_path):
                    # Skip excluded directories
                    dirs[:] = [d for d in dirs if not self._is_excluded_path(os.path.join(root, d))]

                    for file in files:
                        if self._is_excluded_path(file):
                            continue

                        file_path = os.path.join(root, file)

                        # Filter by file type if specified
                        if file_type:
                            if not fnmatch.fnmatch(file.lower(), f'*.{file_type.lower()}'):
                                continue

                        # Check if file matches query (name or content)
                        if self._file_matches_query(file_path, query):
                            results.append(file_path)

                            # Limit results
                            if len(results) >= 50:
                                break

                    if len(results) >= 50:
                        break

            except Exception as e:
                self.logger.exception(f"Error searching in {search_path}")

        return results

    def _file_matches_query(self, file_path: str, query: str) -> bool:
        """Check if file matches search query"""
        query_lower = query.lower()
        filename = os.path.basename(file_path).lower()

        # Check filename
        if query_lower in filename:
            return True

        # For text files, check content
        if self._is_text_file(file_path):
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read(10000).lower()  # Read first 10KB
                    if query_lower in content:
                        return True
            except Exception:
                pass

        return False

    def _is_text_file(self, file_path: str) -> bool:
        """Check if file is a text file"""
        mime_type, _ = mimetypes.guess_type(file_path)
        if mime_type and mime_type.startswith('text/'):
            return True

        # Check extensions
        text_extensions = {'.txt', '.py', '.js', '.html', '.css', '.json', '.xml', '.md', '.csv', '.log'}
        return Path(file_path).suffix.lower() in text_extensions

    def _is_excluded_path(self, path: str) -> bool:
        """Check if path should be excluded from search"""
        path_lower = path.lower()
        name = os.path.basename(path_lower)

        # Check exclusions
        for exclusion in self.default_exclusions:
            if exclusion.startswith('*.'):
                if fnmatch.fnmatch(name, exclusion):
                    return True
            elif exclusion in path_lower:
                return True

        return False

    def _search_by_extensions(self, extensions: List[str], location: str = '') -> List[str]:
        """Search for files by extension patterns"""
        results = []

        search_paths = [location] if location and os.path.isdir(location) else self.default_search_paths.copy()
        if hasattr(self, 'search_config'):
            custom_paths = self.search_config.get('custom_search_paths', [])
            search_paths.extend(custom_paths)

        for search_path in search_paths:
            if not os.path.exists(search_path):
                continue

            try:
                for root, dirs, files in os.walk(search_path):
                    dirs[:] = [d for d in dirs if not self._is_excluded_path(os.path.join(root, d))]

                    for file in files:
                        if self._is_excluded_path(file):
                            continue

                        for ext in extensions:
                            if fnmatch.fnmatch(file.lower(), ext.lower()):
                                results.append(os.path.join(root, file))
                                break

                        if len(results) >= 50:
                            break

                    if len(results) >= 50:
                        break

            except Exception as e:
                self.logger.exception(f"Error searching in {search_path}")

        return results

    def _search_by_date(self, start_date: datetime, location: str = '') -> List[str]:
        """Search for files modified after a certain date"""
        results = []

        search_paths = [location] if location and os.path.isdir(location) else self.default_search_paths.copy()
        if hasattr(self, 'search_config'):
            custom_paths = self.search_config.get('custom_search_paths', [])
            search_paths.extend(custom_paths)

        for search_path in search_paths:
            if not os.path.exists(search_path):
                continue

            try:
                for root, dirs, files in os.walk(search_path):
                    dirs[:] = [d for d in dirs if not self._is_excluded_path(os.path.join(root, d))]

                    for file in files:
                        if self._is_excluded_path(file):
                            continue

                        file_path = os.path.join(root, file)
                        try:
                            stat = os.stat(file_path)
                            modified_time = datetime.fromtimestamp(stat.st_mtime)
                            if modified_time >= start_date:
                                results.append(file_path)
                        except Exception:
                            continue

                        if len(results) >= 50:
                            break

                    if len(results) >= 50:
                        break

            except Exception as e:
                self.logger.exception(f"Error searching in {search_path}")

        # Sort by modification time (newest first)
        results.sort(key=lambda x: os.path.getmtime(x), reverse=True)
        return results

    def _format_file_size(self, size_bytes: int) -> str:
        """Format file size in human readable format"""
        size = float(size_bytes)
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} TB"

    def _get_file_type(self, file_path: str) -> str:
        """Get human readable file type"""
        mime_type, _ = mimetypes.guess_type(file_path)
        if mime_type:
            return mime_type

        # Fallback to extension-based detection
        ext = Path(file_path).suffix.lower()
        type_map = {
            '.txt': 'Text file',
            '.pdf': 'PDF document',
            '.doc': 'Word document',
            '.docx': 'Word document',
            '.xls': 'Excel spreadsheet',
            '.xlsx': 'Excel spreadsheet',
            '.jpg': 'JPEG image',
            '.png': 'PNG image',
            '.mp4': 'MP4 video',
            '.mp3': 'MP3 audio'
        }
        return type_map.get(ext, f"{ext.upper()} file" if ext else "Unknown file type")
