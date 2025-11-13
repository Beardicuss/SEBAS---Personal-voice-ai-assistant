# -*- coding: utf-8 -*-
"""
Advanced File Operations (Phase 3.1 - Hardened)
"""

import logging
import os
import shutil
import re
import hashlib
import fnmatch
from sebas.typing import List, Dict, Optional, Tuple, Callable
from sebas.pathlib import Path
from sebas.datetime import datetime
import zipfile


class FileOperations:
    """Robust file operations for SEBAS."""

    def __init__(self):
        self.operation_stats = self._reset_stats()

    def _reset_stats(self) -> Dict[str, int]:
        return {
            'files_processed': 0,
            'files_copied': 0,
            'files_moved': 0,
            'files_deleted': 0,
            'errors': 0,
            'skipped': 0,
            'bytes_processed': 0
        }

    # -------------------------------------------------------
    # Copy / Move / Delete
    # -------------------------------------------------------
    def copy_recursive(self, source: str, destination: str,
                       pattern: Optional[str] = None,
                       exclude_patterns: Optional[List[str]] = None,
                       overwrite: bool = False,
                       progress_callback: Optional[Callable] = None) -> Tuple[bool, Dict]:
        """Recursively copy files with pattern/exclusion filters."""
        self.operation_stats = self._reset_stats()
        try:
            src, dst = Path(source), Path(destination)
            if not src.exists():
                return False, {"error": f"Source not found: {source}"}

            dst.mkdir(parents=True, exist_ok=True)

            all_files = list(self._walk_files(src, pattern, exclude_patterns))
            total = len(all_files)
            for i, file_path in enumerate(all_files, 1):
                try:
                    rel = file_path.relative_to(src)
                    dest_file = dst / rel
                    dest_file.parent.mkdir(parents=True, exist_ok=True)

                    if dest_file.exists() and not overwrite:
                        self.operation_stats['skipped'] += 1
                        continue

                    shutil.copy2(file_path, dest_file)
                    size = file_path.stat().st_size
                    self.operation_stats['files_copied'] += 1
                    self.operation_stats['bytes_processed'] += size
                except Exception:
                    logging.exception(f"Failed to copy {file_path}")
                    self.operation_stats['errors'] += 1
                finally:
                    self.operation_stats['files_processed'] += 1
                    if progress_callback:
                        progress_callback(i, total, str(file_path))
            return True, self.operation_stats.copy()
        except Exception:
            logging.exception("copy_recursive failed")
            return False, {"error": "Copy operation failed"}

    def move_recursive(self, source: str, destination: str,
                       pattern: Optional[str] = None,
                       exclude_patterns: Optional[List[str]] = None,
                       overwrite: bool = False,
                       progress_callback: Optional[Callable] = None) -> Tuple[bool, Dict]:
        """Recursively move files."""
        self.operation_stats = self._reset_stats()
        try:
            src, dst = Path(source), Path(destination)
            if not src.exists():
                return False, {"error": f"Source not found: {source}"}
            dst.mkdir(parents=True, exist_ok=True)
            all_files = list(self._walk_files(src, pattern, exclude_patterns))
            total = len(all_files)

            for i, file_path in enumerate(all_files, 1):
                try:
                    rel = file_path.relative_to(src)
                    dest_file = dst / rel
                    dest_file.parent.mkdir(parents=True, exist_ok=True)

                    if dest_file.exists() and not overwrite:
                        self.operation_stats['skipped'] += 1
                        continue

                    shutil.move(str(file_path), str(dest_file))
                    size = dest_file.stat().st_size
                    self.operation_stats['files_moved'] += 1
                    self.operation_stats['bytes_processed'] += size
                except Exception:
                    logging.exception(f"Failed to move {file_path}")
                    self.operation_stats['errors'] += 1
                finally:
                    self.operation_stats['files_processed'] += 1
                    if progress_callback:
                        progress_callback(i, total, str(file_path))
            return True, self.operation_stats.copy()
        except Exception:
            logging.exception("move_recursive failed")
            return False, {"error": "Move operation failed"}

    def delete_recursive(self, path: str,
                         pattern: Optional[str] = None,
                         exclude_patterns: Optional[List[str]] = None,
                         dry_run: bool = False,
                         progress_callback: Optional[Callable] = None) -> Tuple[bool, Dict]:
        """Recursively delete files matching pattern."""
        self.operation_stats = self._reset_stats()
        try:
            root = Path(path)
            if not root.exists():
                return False, {"error": f"Path not found: {path}"}

            targets = list(self._walk_files(root, pattern, exclude_patterns))
            total = len(targets)

            for i, file_path in enumerate(targets, 1):
                try:
                    size = file_path.stat().st_size
                    if not dry_run:
                        if file_path.is_file():
                            file_path.unlink()
                        elif file_path.is_dir():
                            shutil.rmtree(file_path)
                    self.operation_stats['files_deleted'] += 1
                    self.operation_stats['bytes_processed'] += size
                except Exception:
                    logging.exception(f"Failed to delete {file_path}")
                    self.operation_stats['errors'] += 1
                finally:
                    self.operation_stats['files_processed'] += 1
                    if progress_callback:
                        progress_callback(i, total, str(file_path))
            return True, self.operation_stats.copy()
        except Exception:
            logging.exception("delete_recursive failed")
            return False, {"error": "Delete operation failed"}

    # -------------------------------------------------------
    # Search / Duplicates
    # -------------------------------------------------------
    def search_file_content(self, search_path: str, search_text: str,
                            file_pattern: Optional[str] = None,
                            case_sensitive: bool = False,
                            use_regex: bool = False,
                            max_results: int = 100) -> List[Dict]:
        """Search text or regex across files safely."""
        results = []
        root = Path(search_path)
        if not root.exists():
            return results

        try:
            flags = 0 if case_sensitive else re.IGNORECASE
            pattern = re.compile(search_text, flags) if use_regex else None
            search_lower = search_text.lower() if not case_sensitive and not use_regex else None

            for file_path in self._walk_files(root, file_pattern):
                try:
                    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                        for line_no, line in enumerate(f, 1):
                            if len(results) >= max_results:
                                return results
                            if use_regex and pattern and pattern.search(line):
                                results.append({"file": str(file_path), "line": line_no, "content": line.strip()})
                            elif not use_regex:
                                hay = line if case_sensitive else line.lower()
                                if search_lower and search_lower in hay:
                                    results.append({"file": str(file_path), "line": line_no, "content": line.strip()})
                except Exception:
                    continue
        except Exception:
            logging.exception("search_file_content failed")
        return results

    def find_duplicate_files(self, search_path: str,
                             file_pattern: Optional[str] = None,
                             min_size: int = 0,
                             hash_algorithm: str = "md5") -> List[List[str]]:
        """Find duplicate files by hash."""
        root = Path(search_path)
        if not root.exists():
            return []
        algo = {"md5": hashlib.md5, "sha1": hashlib.sha1, "sha256": hashlib.sha256}.get(hash_algorithm, hashlib.md5)
        hashes = {}
        try:
            for f in self._walk_files(root, file_pattern):
                try:
                    size = f.stat().st_size
                    if size < min_size:
                        continue
                    h = self._calculate_file_hash(f, algo)
                    if h:
                        hashes.setdefault(h, []).append(str(f))
                except Exception:
                    continue
            return [paths for paths in hashes.values() if len(paths) > 1]
        except Exception:
            logging.exception("find_duplicate_files failed")
            return []

    # -------------------------------------------------------
    # Compression
    # -------------------------------------------------------
    def zip_path(self, source_path: str, archive_path: str, include_root: bool = True) -> Tuple[bool, Dict]:
        """Zip files or directories safely."""
        try:
            src = Path(source_path)
            if not src.exists():
                return False, {"error": f"Not found: {source_path}"}
            archive_path = str(archive_path if str(archive_path).lower().endswith(".zip") else f"{archive_path}.zip")
            files = 0
            total_bytes = 0
            with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
                base = src.parent if include_root else src
                for path in self._walk_files(src):
                    arcname = str(path.relative_to(base))
                    zf.write(path, arcname)
                    files += 1
                    try:
                        total_bytes += path.stat().st_size
                    except Exception:
                        pass
            return True, {"files": files, "bytes": total_bytes, "archive": archive_path}
        except Exception:
            logging.exception("zip_path failed")
            return False, {"error": "Zip operation failed"}

    def unzip_archive(self, archive_path: str, destination: str, overwrite: bool = False) -> Tuple[bool, Dict]:
        """Unzip safely."""
        try:
            ap = Path(archive_path)
            if not ap.exists():
                return False, {"error": f"Archive not found: {archive_path}"}
            dest = Path(destination)
            dest.mkdir(parents=True, exist_ok=True)
            files = 0
            bytes_total = 0
            with zipfile.ZipFile(ap, "r") as zf:
                for info in zf.infolist():
                    target = dest / info.filename
                    if target.exists() and not overwrite:
                        continue
                    if info.is_dir():
                        target.mkdir(parents=True, exist_ok=True)
                    else:
                        target.parent.mkdir(parents=True, exist_ok=True)
                        with zf.open(info, "r") as src, open(target, "wb") as out:
                            data = src.read()
                            out.write(data)
                            bytes_total += len(data)
                        files += 1
            return True, {"files": files, "bytes": bytes_total, "destination": str(dest)}
        except Exception:
            logging.exception("unzip_archive failed")
            return False, {"error": "Unzip operation failed"}

    # -------------------------------------------------------
    # Helpers
    # -------------------------------------------------------
    def _walk_files(self, root: Path,
                    pattern: Optional[str] = None,
                    exclude: Optional[List[str]] = None):
        """Yield file paths respecting include/exclude filters."""
        if root.is_file():
            if self._matches_pattern(root, pattern, exclude):
                yield root
            return
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if not self._should_exclude(d, exclude)]
            for filename in filenames:
                p = Path(dirpath) / filename
                if self._matches_pattern(p, pattern, exclude):
                    yield p

    def _matches_pattern(self, path: Path,
                         pattern: Optional[str],
                         exclude: Optional[List[str]]) -> bool:
        name = path.name
        full = str(path)
        if exclude:
            for ex in exclude:
                try:
                    if fnmatch.fnmatch(name, ex) or fnmatch.fnmatch(full, ex) or re.search(ex, name):
                        return False
                except re.error:
                    continue
        if not pattern:
            return True
        try:
            if fnmatch.fnmatch(name, pattern) or fnmatch.fnmatch(full, pattern) or re.search(pattern, name):
                return True
        except re.error:
            pass
        return False

    def _should_exclude(self, name: str, exclude: Optional[List[str]]) -> bool:
        if not exclude:
            return False
        for ex in exclude:
            try:
                if fnmatch.fnmatch(name, ex) or re.search(ex, name):
                    return True
            except re.error:
                continue
        return False

    def _calculate_file_hash(self, path: Path, algo) -> Optional[str]:
        try:
            h = algo()
            with open(path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    h.update(chunk)
            return h.hexdigest()
        except Exception:
            logging.exception(f"Failed to hash {path}")
            return None