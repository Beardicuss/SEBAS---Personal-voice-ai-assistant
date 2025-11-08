# -*- coding: utf-8 -*-
"""
Windows Firewall Management
Phase 2.2: Firewall rule creation and modification
"""

import logging
import subprocess
import platform
from typing import Optional, Dict, List, Tuple
from enum import Enum


class FirewallRuleDirection(Enum):
    """Firewall rule direction"""
    INBOUND = "inbound"
    OUTBOUND = "outbound"


class FirewallRuleAction(Enum):
    """Firewall rule action"""
    ALLOW = "allow"
    BLOCK = "block"


class FirewallRuleProtocol(Enum):
    """Firewall rule protocol"""
    TCP = "tcp"
    UDP = "udp"
    ANY = "any"


class FirewallManager:
    """
    Manages Windows Firewall rules.
    """
    
    def __init__(self):
        """Initialize Firewall Manager."""
        if platform.system() != 'Windows':
            raise RuntimeError("FirewallManager only works on Windows")
    
    def create_firewall_rule(self, name: str, direction: FirewallRuleDirection,
                            action: FirewallRuleAction, protocol: FirewallRuleProtocol,
                            local_port: Optional[int] = None,
                            remote_port: Optional[int] = None,
                            local_ip: Optional[str] = None,
                            remote_ip: Optional[str] = None,
                            program: Optional[str] = None,
                            enabled: bool = True) -> Tuple[bool, str]:
        """
        Create a firewall rule.
        
        Args:
            name: Rule name
            direction: Rule direction (inbound/outbound)
            action: Rule action (allow/block)
            protocol: Protocol (tcp/udp/any)
            local_port: Local port number (optional)
            remote_port: Remote port number (optional)
            local_ip: Local IP address (optional)
            remote_ip: Remote IP address (optional)
            program: Program path (optional)
            enabled: Whether rule is enabled
            
        Returns:
            Tuple of (success, message)
        """
        try:
            cmd = [
                "netsh", "advfirewall", "firewall", "add", "rule",
                f"name={name}",
                f"dir={direction.value}",
                f"action={action.value}",
                f"protocol={protocol.value}"
            ]
            
            if local_port:
                cmd.append(f"localport={local_port}")
            if remote_port:
                cmd.append(f"remoteport={remote_port}")
            if local_ip:
                cmd.append(f"localip={local_ip}")
            if remote_ip:
                cmd.append(f"remoteip={remote_ip}")
            if program:
                cmd.append(f"program={program}")
            
            cmd.append(f"enable={'yes' if enabled else 'no'}")
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                logging.info(f"Firewall rule {name} created")
                return True, f"Firewall rule {name} created successfully"
            else:
                error = result.stderr.strip() or result.stdout.strip()
                return False, error
                
        except Exception:
            logging.exception(f"Failed to create firewall rule: {name}")
            return False, "Failed to create firewall rule"
    
    def delete_firewall_rule(self, name: str) -> Tuple[bool, str]:
        """
        Delete a firewall rule.
        
        Args:
            name: Rule name
            
        Returns:
            Tuple of (success, message)
        """
        try:
            result = subprocess.run(
                ["netsh", "advfirewall", "firewall", "delete", "rule", f"name={name}"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                logging.info(f"Firewall rule {name} deleted")
                return True, f"Firewall rule {name} deleted successfully"
            else:
                error = result.stderr.strip() or result.stdout.strip()
                return False, error
                
        except Exception:
            logging.exception(f"Failed to delete firewall rule: {name}")
            return False, "Failed to delete firewall rule"
    
    def list_firewall_rules(self, name_filter: Optional[str] = None) -> List[Dict[str, str]]:
        """
        List firewall rules.
        
        Args:
            name_filter: Optional name filter
            
        Returns:
            List of rule information dicts
        """
        try:
            cmd = ["netsh", "advfirewall", "firewall", "show", "rule", "name=all"]
            if name_filter:
                cmd = ["netsh", "advfirewall", "firewall", "show", "rule", f"name={name_filter}"]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode != 0:
                return []
            
            rules = []
            current_rule = {}
            
            for line in result.stdout.split('\n'):
                line = line.strip()
                if not line:
                    if current_rule:
                        rules.append(current_rule)
                        current_rule = {}
                    continue
                
                if 'Rule Name' in line and ':' in line:
                    if current_rule:
                        rules.append(current_rule)
                    current_rule = {'name': line.split(':', 1)[1].strip()}
                elif ':' in line:
                    key, value = line.split(':', 1)
                    key = key.strip().lower().replace(' ', '_')
                    value = value.strip()
                    if current_rule:
                        current_rule[key] = value
            
            if current_rule:
                rules.append(current_rule)
            
            return rules
            
        except Exception:
            logging.exception("Failed to list firewall rules")
            return []
    
    def enable_firewall_rule(self, name: str) -> Tuple[bool, str]:
        """
        Enable a firewall rule.
        
        Args:
            name: Rule name
            
        Returns:
            Tuple of (success, message)
        """
        try:
            result = subprocess.run(
                ["netsh", "advfirewall", "firewall", "set", "rule", f"name={name}", "new", "enable=yes"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                return True, f"Rule {name} enabled"
            else:
                error = result.stderr.strip() or result.stdout.strip()
                return False, error
                
        except Exception:
            logging.exception(f"Failed to enable firewall rule: {name}")
            return False, "Failed to enable firewall rule"
    
    def disable_firewall_rule(self, name: str) -> Tuple[bool, str]:
        """
        Disable a firewall rule.
        
        Args:
            name: Rule name
            
        Returns:
            Tuple of (success, message)
        """
        try:
            result = subprocess.run(
                ["netsh", "advfirewall", "firewall", "set", "rule", f"name={name}", "new", "enable=no"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                return True, f"Rule {name} disabled"
            else:
                error = result.stderr.strip() or result.stdout.strip()
                return False, error
                
        except Exception:
            logging.exception(f"Failed to disable firewall rule: {name}")
            return False, "Failed to disable firewall rule"
    
    def get_firewall_status(self) -> Dict[str, str]:
        """
        Get firewall status.
        
        Returns:
            Dict with firewall status information
        """
        try:
            result = subprocess.run(
                ["netsh", "advfirewall", "show", "allprofiles", "state"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            status = {}
            for line in result.stdout.split('\n'):
                line = line.strip()
                if 'State' in line and ':' in line:
                    status['state'] = line.split(':', 1)[1].strip()
            
            return status
            
        except Exception:
            logging.exception("Failed to get firewall status")
            return {}

