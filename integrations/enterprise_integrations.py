# -*- coding: utf-8 -*-
"""
Enterprise Service Integration
Phase 5.2: Ticket systems, monitoring, asset management
"""

import logging
import json
from typing import Optional, Dict, List, Any
from datetime import datetime


class TicketSystem:
    """Base class for ticket system integration."""
    
    def create_ticket(self, title: str, description: str, **kwargs) -> Dict[str, Any]:
        """Create a ticket. To be implemented by subclasses."""
        raise NotImplementedError
    
    def get_ticket(self, ticket_id: str) -> Dict[str, Any]:
        """Get ticket details. To be implemented by subclasses."""
        raise NotImplementedError
    
    def update_ticket(self, ticket_id: str, updates: Dict[str, Any]) -> bool:
        """Update a ticket. To be implemented by subclasses."""
        raise NotImplementedError


class ServiceNowIntegration(TicketSystem):
    """ServiceNow ticket system integration."""
    
    def __init__(self, instance_url: str, username: str, password: str):
        """
        Initialize ServiceNow integration.
        
        Args:
            instance_url: ServiceNow instance URL
            username: Username
            password: Password or API token
        """
        self.instance_url = instance_url.rstrip('/')
        self.username = username
        self.password = password
        self.api_base = f"{self.instance_url}/api/now/table"
    
    def create_ticket(self, title: str, description: str, **kwargs) -> Dict[str, Any]:
        """Create a ServiceNow incident."""
        try:
            import requests
            
            ticket_data = {
                'short_description': title,
                'description': description,
                **kwargs
            }
            
            response = requests.post(
                f"{self.api_base}/incident",
                json=ticket_data,
                auth=(self.username, self.password),
                headers={'Content-Type': 'application/json'},
                timeout=10
            )
            
            if response.status_code == 201:
                return response.json().get('result', {})
            else:
                logging.error(f"ServiceNow API error: {response.status_code}")
                return {}
                
        except ImportError:
            logging.warning("requests library not available for ServiceNow integration")
            return {}
        except Exception:
            logging.exception("Failed to create ServiceNow ticket")
            return {}
    
    def get_ticket(self, ticket_id: str) -> Dict[str, Any]:
        """Get ServiceNow incident."""
        try:
            import requests
            
            response = requests.get(
                f"{self.api_base}/incident/{ticket_id}",
                auth=(self.username, self.password),
                timeout=10
            )
            
            if response.status_code == 200:
                return response.json().get('result', {})
            else:
                return {}
                
        except ImportError:
            logging.warning("requests library not available")
            return {}
        except Exception:
            logging.exception("Failed to get ServiceNow ticket")
            return {}
    
    def update_ticket(self, ticket_id: str, updates: Dict[str, Any]) -> bool:
        """Update ServiceNow incident."""
        try:
            import requests
            
            response = requests.patch(
                f"{self.api_base}/incident/{ticket_id}",
                json=updates,
                auth=(self.username, self.password),
                headers={'Content-Type': 'application/json'},
                timeout=10
            )
            
            return response.status_code == 200
            
        except ImportError:
            logging.warning("requests library not available")
            return False
        except Exception:
            logging.exception("Failed to update ServiceNow ticket")
            return False


class JiraIntegration(TicketSystem):
    """Jira ticket system integration."""
    
    def __init__(self, server_url: str, username: str, api_token: str):
        """
        Initialize Jira integration.
        
        Args:
            server_url: Jira server URL
            username: Username or email
            api_token: Jira API token
        """
        self.server_url = server_url.rstrip('/')
        self.username = username
        self.api_token = api_token
        self.api_base = f"{self.server_url}/rest/api/2"
    
    def create_ticket(self, title: str, description: str, project_key: str = "PROJ",
                     issue_type: str = "Task", **kwargs) -> Dict[str, Any]:
        """Create a Jira issue."""
        try:
            import requests
            from requests.auth import HTTPBasicAuth
            
            issue_data = {
                'fields': {
                    'project': {'key': project_key},
                    'summary': title,
                    'description': description,
                    'issuetype': {'name': issue_type},
                    **kwargs.get('fields', {})
                }
            }
            
            response = requests.post(
                f"{self.api_base}/issue",
                json=issue_data,
                auth=HTTPBasicAuth(self.username, self.api_token),
                headers={'Content-Type': 'application/json'},
                timeout=10
            )
            
            if response.status_code == 201:
                return response.json()
            else:
                logging.error(f"Jira API error: {response.status_code}")
                return {}
                
        except ImportError:
            logging.warning("requests library not available for Jira integration")
            return {}
        except Exception:
            logging.exception("Failed to create Jira ticket")
            return {}
    
    def get_ticket(self, ticket_id: str) -> Dict[str, Any]:
        """Get Jira issue."""
        try:
            import requests
            from requests.auth import HTTPBasicAuth
            
            response = requests.get(
                f"{self.api_base}/issue/{ticket_id}",
                auth=HTTPBasicAuth(self.username, self.api_token),
                timeout=10
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                return {}
                
        except ImportError:
            logging.warning("requests library not available")
            return {}
        except Exception:
            logging.exception("Failed to get Jira ticket")
            return {}
    
    def update_ticket(self, ticket_id: str, updates: Dict[str, Any]) -> bool:
        """Update Jira issue."""
        try:
            import requests
            from requests.auth import HTTPBasicAuth
            
            issue_data = {'fields': updates}
            
            response = requests.put(
                f"{self.api_base}/issue/{ticket_id}",
                json=issue_data,
                auth=HTTPBasicAuth(self.username, self.api_token),
                headers={'Content-Type': 'application/json'},
                timeout=10
            )
            
            return response.status_code == 204
            
        except ImportError:
            logging.warning("requests library not available")
            return False
        except Exception:
            logging.exception("Failed to update Jira ticket")
            return False


class MonitoringSystemIntegration:
    """Base class for monitoring system integration."""
    
    def send_alert(self, alert_name: str, message: str, severity: str = "warning") -> bool:
        """Send alert. To be implemented by subclasses."""
        raise NotImplementedError
    
    def get_status(self) -> Dict[str, Any]:
        """Get system status. To be implemented by subclasses."""
        raise NotImplementedError


class DocumentationGenerator:
    """Documentation auto-generation."""
    
    def generate_api_documentation(self, api_spec: Dict[str, Any]) -> str:
        """Generate API documentation from spec."""
        try:
            doc = "# API Documentation\n\n"
            
            if 'info' in api_spec:
                info = api_spec['info']
                doc += f"## {info.get('title', 'API')}\n\n"
                doc += f"**Version:** {info.get('version', '1.0')}\n\n"
                if 'description' in info:
                    doc += f"{info['description']}\n\n"
            
            if 'paths' in api_spec:
                doc += "## Endpoints\n\n"
                for path, methods in api_spec['paths'].items():
                    doc += f"### {path}\n\n"
                    for method, details in methods.items():
                        doc += f"**{method.upper()}** {path}\n\n"
                        if 'summary' in details:
                            doc += f"{details['summary']}\n\n"
                        if 'parameters' in details:
                            doc += "Parameters:\n"
                            for param in details['parameters']:
                                doc += f"- `{param.get('name')}` ({param.get('type', 'string')}): {param.get('description', '')}\n"
                            doc += "\n"
            
            return doc
            
        except Exception:
            logging.exception("Failed to generate API documentation")
            return ""
    
    def generate_configuration_documentation(self, config: Dict[str, Any]) -> str:
        """Generate configuration documentation."""
        try:
            doc = "# Configuration Documentation\n\n"
            doc += f"Generated: {datetime.now().isoformat()}\n\n"
            doc += "## Configuration Options\n\n"
            
            for key, value in config.items():
                doc += f"### {key}\n\n"
                if isinstance(value, dict):
                    doc += f"Type: Object\n\n"
                    for subkey, subvalue in value.items():
                        doc += f"- `{subkey}`: {subvalue}\n"
                elif isinstance(value, list):
                    doc += f"Type: Array\n\n"
                    doc += f"Default: {json.dumps(value)}\n\n"
                else:
                    doc += f"Type: {type(value).__name__}\n\n"
                    doc += f"Default: {value}\n\n"
            
            return doc
            
        except Exception:
            logging.exception("Failed to generate configuration documentation")
            return ""

