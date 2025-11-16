# -*- coding: utf-8 -*-
"""
Enterprise Service Integration
Phase 5.2: Ticket systems, monitoring, asset management
"""

import logging
import json
import requests
from sebas.datetime import datetime
from typing import Optional, Dict, List, Any, Tuple


class TicketSystem:
    """Abstract base class for ticket system integrations."""

    def create_ticket(self, title: str, description: str, **kwargs) -> Tuple[bool, Any]:
        raise NotImplementedError

    def get_ticket(self, ticket_id: str) -> Tuple[bool, Any]:
        raise NotImplementedError

    def update_ticket(self, ticket_id: str, updates: Dict[str, Any]) -> Tuple[bool, Any]:
        raise NotImplementedError


# ------------------- ServiceNow -------------------
class ServiceNowIntegration(TicketSystem):
    """ServiceNow ticket system integration."""

    def __init__(self, instance_url: str, username: str, password: str):
        self.instance_url = instance_url.rstrip('/')
        self.username = username
        self.password = password
        self.api_base = f"{self.instance_url}/api/now/table"

    def create_ticket(self, title: str, description: str, **kwargs) -> Tuple[bool, Any]:
        """Create a ServiceNow incident."""
        try:
            ticket_data = {'short_description': title, 'description': description, **kwargs}
            response = requests.post(
                f"{self.api_base}/incident",
                json=ticket_data,
                auth=(self.username, self.password),
                headers={'Content-Type': 'application/json'},
                timeout=15
            )
            if 200 <= response.status_code < 300:
                return True, response.json().get('result', {})
            logging.warning(f"[ServiceNow] API error {response.status_code}: {response.text[:120]}")
            return False, {}
        except requests.RequestException as e:
            logging.exception("[ServiceNow] Network error while creating ticket")
            return False, {"error": str(e)}
        except Exception:
            logging.exception("[ServiceNow] Unexpected error creating ticket")
            return False, {}

    def get_ticket(self, ticket_id: str) -> Tuple[bool, Any]:
        """Retrieve a ServiceNow incident by ID."""
        try:
            response = requests.get(
                f"{self.api_base}/incident/{ticket_id}",
                auth=(self.username, self.password),
                timeout=15
            )
            if 200 <= response.status_code < 300:
                return True, response.json().get('result', {})
            return False, {"error": f"HTTP {response.status_code}"}
        except requests.RequestException as e:
            logging.exception("[ServiceNow] Network error while getting ticket")
            return False, {"error": str(e)}
        except Exception:
            logging.exception("[ServiceNow] Unexpected error getting ticket")
            return False, {}

    def update_ticket(self, ticket_id: str, updates: Dict[str, Any]) -> Tuple[bool, str]:
        """Update an existing ServiceNow incident."""
        try:
            response = requests.patch(
                f"{self.api_base}/incident/{ticket_id}",
                json=updates,
                auth=(self.username, self.password),
                headers={'Content-Type': 'application/json'},
                timeout=15
            )
            if 200 <= response.status_code < 300:
                return True, "Ticket updated"
            return False, f"HTTP {response.status_code}"
        except requests.RequestException as e:
            logging.exception("[ServiceNow] Network error while updating ticket")
            return False, str(e)
        except Exception:
            logging.exception("[ServiceNow] Unexpected error updating ticket")
            return False, "Unexpected failure"


# ------------------- Jira -------------------
class JiraIntegration(TicketSystem):
    """Jira ticket system integration."""

    def __init__(self, server_url: str, username: str, api_token: str):
        self.server_url = server_url.rstrip('/')
        self.username = username
        self.api_token = api_token
        self.api_base = f"{self.server_url}/rest/api/2"

    def create_ticket(self, title: str, description: str, project_key: str = "PROJ",
                      issue_type: str = "Task", **kwargs) -> Tuple[bool, Any]:
        """Create a Jira issue."""
        try:
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
                timeout=15
            )
            if 200 <= response.status_code < 300:
                return True, response.json()
            logging.warning(f"[Jira] API error {response.status_code}: {response.text[:120]}")
            return False, {"error": f"HTTP {response.status_code}"}
        except requests.RequestException as e:
            logging.exception("[Jira] Network error while creating ticket")
            return False, {"error": str(e)}
        except Exception:
            logging.exception("[Jira] Unexpected error creating ticket")
            return False, {}

    def get_ticket(self, ticket_id: str) -> Tuple[bool, Any]:
        """Retrieve Jira issue details."""
        try:
            from requests.auth import HTTPBasicAuth
            response = requests.get(
                f"{self.api_base}/issue/{ticket_id}",
                auth=HTTPBasicAuth(self.username, self.api_token),
                timeout=15
            )
            if 200 <= response.status_code < 300:
                return True, response.json()
            return False, {"error": f"HTTP {response.status_code}"}
        except requests.RequestException as e:
            logging.exception("[Jira] Network error while fetching ticket")
            return False, {"error": str(e)}
        except Exception:
            logging.exception("[Jira] Unexpected error fetching ticket")
            return False, {}

    def update_ticket(self, ticket_id: str, updates: Dict[str, Any]) -> Tuple[bool, str]:
        """Update a Jira issue."""
        try:
            from requests.auth import HTTPBasicAuth
            issue_data = {'fields': updates}
            response = requests.put(
                f"{self.api_base}/issue/{ticket_id}",
                json=issue_data,
                auth=HTTPBasicAuth(self.username, self.api_token),
                headers={'Content-Type': 'application/json'},
                timeout=15
            )
            if 200 <= response.status_code < 300:
                return True, "Ticket updated"
            return False, f"HTTP {response.status_code}"
        except requests.RequestException as e:
            logging.exception("[Jira] Network error while updating ticket")
            return False, str(e)
        except Exception:
            logging.exception("[Jira] Unexpected error updating ticket")
            return False, "Unexpected failure"


# ------------------- Monitoring System -------------------
class MonitoringSystemIntegration:
    """Base class for monitoring system integrations."""

    def send_alert(self, alert_name: str, message: str, severity: str = "warning") -> bool:
        raise NotImplementedError

    def get_status(self) -> Dict[str, Any]:
        raise NotImplementedError


# ------------------- Documentation Generator -------------------
class DocumentationGenerator:
    """Documentation auto-generation helper."""

    def generate_api_documentation(self, api_spec: Dict[str, Any]) -> str:
        """Generate Markdown documentation from API spec."""
        try:
            doc = "# API Documentation\n\n"
            if 'info' in api_spec:
                info = api_spec['info']
                doc += f"## {info.get('title', 'API')}\n\n"
                doc += f"**Version:** {info.get('version', '1.0')}\n\n"
                if info.get('description'):
                    doc += f"{info['description']}\n\n"

            if 'paths' in api_spec:
                doc += "## Endpoints\n\n"
                for path, methods in api_spec['paths'].items():
                    doc += f"### {path}\n\n"
                    for method, details in methods.items():
                        doc += f"**{method.upper()}** {path}\n\n"
                        if details.get('summary'):
                            doc += f"{str(details['summary'])}\n\n"
                        if details.get('parameters'):
                            doc += "Parameters:\n"
                            for param in details['parameters']:
                                doc += f"- `{param.get('name', '')}` ({param.get('type', 'string')}): {param.get('description', '')}\n"
                            doc += "\n"
            return doc
        except Exception:
            logging.exception("[DocsGen] Failed to generate API documentation")
            return "# API Documentation\n\n_Generation failed._\n"

    def generate_configuration_documentation(self, config: Dict[str, Any]) -> str:
        """Generate Markdown documentation for configuration dictionary."""
        try:
            doc = "# Configuration Documentation\n\n"
            doc += f"Generated: {datetime.now().isoformat()}\n\n"
            for key, value in config.items():
                doc += f"## {key}\n\n"
                if isinstance(value, dict):
                    doc += "Type: Object\n\n"
                    for subkey, subval in value.items():
                        doc += f"- `{subkey}`: {json.dumps(subval, ensure_ascii=False)}\n"
                elif isinstance(value, list):
                    doc += "Type: Array\n\n"
                    doc += f"Default: {json.dumps(value, ensure_ascii=False)}\n\n"
                else:
                    doc += f"Type: {type(value).__name__}\n\n"
                    doc += f"Default: {json.dumps(value, ensure_ascii=False)}\n\n"
            return doc
        except Exception:
            logging.exception("[DocsGen] Failed to generate configuration documentation")
            return "# Configuration Documentation\n\n_Generation failed._\n"
