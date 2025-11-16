# -*- coding: utf-8 -*-
"""
SEBAS Skills Package
Stage 1 Mk.I + Stage 2 Enhanced
"""

import os
import logging
import threading
from pathlib import Path

# Import base skill class
from sebas.skills.base_skill import BaseSkill

# Auto-discovery paths
SKILLS_DIR = Path(__file__).parent
DEFAULT_SEARCH_PATHS = [
    os.path.expanduser('~'),
    os.path.join(os.path.expanduser('~'), 'Documents'),
    os.path.join(os.path.expanduser('~'), 'Desktop'),
    os.path.join(os.path.expanduser('~'), 'Downloads'),
]

DEFAULT_EXCLUSIONS = [
    '.git', '__pycache__', 'node_modules', '.venv', 'build', 'dist',
    '*.tmp', '*.temp', '*.log', 'Thumbs.db', 'desktop.ini'
]

# Shared locks for thread-safe file operations
CACHE_LOCK = threading.RLock()
RECENT_LOCK = threading.RLock()

# Stage 1 Core Skills
STAGE1_SKILLS = [
    'system_skill',
    'app_skill', 
    'network_skill',
    'datetime_skill',
]

# Stage 2 Extended Skills
STAGE2_SKILLS = [
    'volume_skill',
    'storage_skill',
    'security_skill',
    'service_skill',
    'monitoring_skill',
    'file_skill',
]

# Stage 2 Advanced Skills
STAGE2_ADVANCED = [
    'smart_home_skill',
    'ai_analytics_skill',
    'compliance_skill',
    'code_skill',
    'automation_skill',
]

# All available skills
ALL_SKILLS = STAGE1_SKILLS + STAGE2_SKILLS + STAGE2_ADVANCED

# Export
__all__ = [
    'BaseSkill',
    'SKILLS_DIR',
    'DEFAULT_SEARCH_PATHS',
    'DEFAULT_EXCLUSIONS',
    'CACHE_LOCK',
    'RECENT_LOCK',
    'STAGE1_SKILLS',
    'STAGE2_SKILLS',
    'STAGE2_ADVANCED',
    'ALL_SKILLS',
]

# Log initialization
logging.info(f"[Skills Package] Initialized with {len(ALL_SKILLS)} available skills")