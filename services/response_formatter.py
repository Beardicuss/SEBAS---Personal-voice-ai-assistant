# -*- coding: utf-8 -*-
"""
Response Formatter - Stage 2 Mk.II
Formats assistant responses with visual display support
"""

import logging
from typing import Dict, Any, List, Optional


class ResponseFormatter:
    """Formats responses for both speech and visual display."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def format_response(self, intent: str, slots: Dict[str, Any], 
                       result: Any) -> Dict[str, Any]:
        """
        Format a skill response for output.
        
        Returns:
            Dict with keys:
                - text: Text to speak
                - display: Whether to show visual window
                - display_data: Data to display visually
                - display_type: Type of display (text, list, table, etc.)
        """
        response = {
            'text': '',
            'display': False,
            'display_data': None,
            'display_type': 'text'
        }
        
        # Format based on intent type
        if intent in self._visual_intents():
            response['display'] = True
            response.update(self._format_visual(intent, result))
        else:
            response['text'] = self._format_text(intent, result)
        
        return response
    
    def _visual_intents(self) -> List[str]:
        """Intents that require visual display."""
        return [
            'get_ip_address',
            'list_services',
            'list_workflows',
            'get_activity_log',
            'list_recent_files',
            'get_system_performance',
            'detect_anomalies',
            'get_network_stats',
        ]
    
    def _format_visual(self, intent: str, result: Any) -> Dict[str, Any]:
        """Format data for visual display."""
        if intent == 'get_ip_address':
            return {
                'text': f"Your IP address is {result}",
                'display_data': {'IP Address': result},
                'display_type': 'key_value'
            }
        
        elif intent in ['list_services', 'list_workflows']:
            return {
                'text': f"Found {len(result)} items",
                'display_data': result,
                'display_type': 'list'
            }
        
        elif intent == 'get_system_performance':
            return {
                'text': "System performance data",
                'display_data': result,
                'display_type': 'table'
            }
        
        else:
            return {
                'text': str(result),
                'display_data': result,
                'display_type': 'text'
            }
    
    def _format_text(self, intent: str, result: Any) -> str:
        """Format simple text response."""
        if isinstance(result, bool):
            return "Command completed" if result else "Command failed"
        return str(result)


# Fixed __all__ declaration - must be a simple list
__all__ = ['ResponseFormatter']