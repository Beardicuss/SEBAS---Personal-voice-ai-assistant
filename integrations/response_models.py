# -*- coding: utf-8 -*-
"""
Response Models for SEBAS Skills
Standardized output format with visual display flags
"""

from dataclasses import dataclass
from typing import Optional, Dict, Any, List
from enum import Enum


class DisplayType(Enum):
    """Types of visual displays"""
    NONE = "none"           # No visual display needed
    INFO = "info"           # Information window
    LIST = "list"           # Scrollable list
    TABLE = "table"         # Tabular data
    GRAPH = "graph"         # Chart/graph
    ERROR = "error"         # Error dialog
    WARNING = "warning"     # Warning dialog


@dataclass
class SkillResponse:
    """Standardized skill response format"""
    success: bool
    message: str
    display_type: DisplayType = DisplayType.NONE
    display_data: Optional[Dict[str, Any]] = None
    auto_close_seconds: Optional[int] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API transport"""
        return {
            'success': self.success,
            'message': self.message,
            'display_type': self.display_type.value,
            'display_data': self.display_data,
            'auto_close_seconds': self.auto_close_seconds
        }


# Helper functions for common response types
def info_response(message: str, data: Dict[str, Any], 
                 auto_close: int = 10) -> SkillResponse:
    """Create info display response"""
    return SkillResponse(
        success=True,
        message=message,
        display_type=DisplayType.INFO,
        display_data=data,
        auto_close_seconds=auto_close
    )


def list_response(message: str, items: List[Any], 
                 title: str = "Results") -> SkillResponse:
    """Create list display response"""
    return SkillResponse(
        success=True,
        message=message,
        display_type=DisplayType.LIST,
        display_data={'title': title, 'items': items},
        auto_close_seconds=None  # User must close manually
    )


def error_response(message: str, details: Optional[str] = None) -> SkillResponse:
    """Create error display response"""
    return SkillResponse(
        success=False,
        message=message,
        display_type=DisplayType.ERROR,
        display_data={'details': details} if details else None,
        auto_close_seconds=5
    )


def table_response(message: str, headers: List[str], 
                  rows: List[List[Any]]) -> SkillResponse:
    """Create table display response"""
    return SkillResponse(
        success=True,
        message=message,
        display_type=DisplayType.TABLE,
        display_data={'headers': headers, 'rows': rows},
        auto_close_seconds=None
    )


def warning_response(message: str, details: Optional[str] = None) -> SkillResponse:
    """Create warning display response"""
    return SkillResponse(
        success=True,
        message=message,
        display_type=DisplayType.WARNING,
        display_data={'details': details} if details else None,
        auto_close_seconds=8
    )