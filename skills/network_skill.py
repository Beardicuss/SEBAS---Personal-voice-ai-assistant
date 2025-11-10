# -*- coding: utf-8 -*-
"""
Network Management Skill
Phase 2.2: Network administration
"""

from skills.base_skill import BaseSkill
from typing import Dict, Any
import logging


class NetworkSkill(BaseSkill):
    """
    Skill for managing network configuration and operations.
    """
    
    def __init__(self, assistant):
        super().__init__(assistant)
        self.intents = [
            'get_ip_config',
            'set_ip_config',
            'flush_dns_cache',
            'register_dns',
            'test_network_connectivity',
            'list_network_shares',
            'create_network_share',
            'delete_network_share',
            'map_network_drive',
            'unmap_network_drive',
            'list_network_drives',
            'list_firewall_rules',
            'create_firewall_rule',
            'delete_firewall_rule',
            'enable_firewall_rule',
            'disable_firewall_rule',
            'get_firewall_status',
            'get_listening_ports',
            'test_port',
            'get_port_statistics',
            'connect_vpn',
            'disconnect_vpn',
            'list_vpn_connections'
        ]
    
    def can_handle(self, intent: str) -> bool:
        return intent in self.get_intents()
    
    def get_intents(self) -> list:
        return self.intents
    
    def handle(self, intent: str, slots: dict) -> bool:
        if intent == 'get_ip_config':
            return self._handle_get_ip_config(slots)
        elif intent == 'set_ip_config':
            return self._handle_set_ip_config(slots)
        elif intent == 'flush_dns_cache':
            return self._handle_flush_dns_cache()
        elif intent == 'register_dns':
            return self._handle_register_dns()
        elif intent == 'test_network_connectivity':
            return self._handle_test_connectivity(slots)
        elif intent == 'list_network_shares':
            return self._handle_list_network_shares()
        elif intent == 'create_network_share':
            return self._handle_create_network_share(slots)
        elif intent == 'delete_network_share':
            return self._handle_delete_network_share(slots)
        elif intent == 'map_network_drive':
            return self._handle_map_network_drive(slots)
        elif intent == 'unmap_network_drive':
            return self._handle_unmap_network_drive(slots)
        elif intent == 'list_network_drives':
            return self._handle_list_network_drives()
        elif intent == 'list_firewall_rules':
            return self._handle_list_firewall_rules(slots)
        elif intent == 'create_firewall_rule':
            return self._handle_create_firewall_rule(slots)
        elif intent == 'delete_firewall_rule':
            return self._handle_delete_firewall_rule(slots)
        elif intent == 'enable_firewall_rule':
            return self._handle_enable_firewall_rule(slots)
        elif intent == 'disable_firewall_rule':
            return self._handle_disable_firewall_rule(slots)
        elif intent == 'get_firewall_status':
            return self._handle_get_firewall_status()
        elif intent == 'get_listening_ports':
            return self._handle_get_listening_ports()
        elif intent == 'test_port':
            return self._handle_test_port(slots)
        elif intent == 'get_port_statistics':
            return self._handle_get_port_statistics()
        elif intent == 'connect_vpn':
            return self._handle_connect_vpn(slots)
        elif intent == 'disconnect_vpn':
            return self._handle_disconnect_vpn(slots)
        elif intent == 'list_vpn_connections':
            return self._handle_list_vpn_connections()
        return False
    
    def _handle_get_ip_config(self, slots: dict) -> bool:
        """Handle get IP configuration command."""
        try:
            if not hasattr(self.assistant, 'network_manager') or not self.assistant.network_manager:
                self.assistant.speak("Network management is not available")
                return False
            
            interface_name = slots.get('interface_name')
            configs = self.assistant.network_manager.get_ip_config(interface_name)
            
            if configs:
                for config in configs[:3]:  # Limit to first 3
                    name = config.get('name', 'Unknown')
                    ip = config.get('ip_address', 'N/A')
                    self.assistant.speak(f"Interface {name}: IP address {ip}")
            else:
                self.assistant.speak("No network interfaces found")
            
            return True
            
        except Exception:
            logging.exception("Failed to get IP configuration")
            self.assistant.speak("Failed to get IP configuration")
            return False
    
    def _handle_set_ip_config(self, slots: dict) -> bool:
        """Handle set IP configuration command."""
        if not self.assistant.has_permission('set_ip_config'):
            return False
        
        try:
            if not hasattr(self.assistant, 'network_manager') or not self.assistant.network_manager:
                self.assistant.speak("Network management is not available")
                return False
            
            interface_name = slots.get('interface_name')
            config_type_str = slots.get('config_type', 'dhcp')
            
            if not interface_name:
                self.assistant.speak("Please specify an interface name")
                return False
            
            from integrations.network_manager import IPConfigType
            try:
                config_type = IPConfigType(config_type_str.lower())
            except ValueError:
                self.assistant.speak(f"Invalid configuration type: {config_type_str}")
                return False
            
            ip_address = slots.get('ip_address')
            subnet_mask = slots.get('subnet_mask')
            
            success, message = self.assistant.network_manager.set_ip_config(
                interface_name=interface_name,
                config_type=config_type,
                ip_address=ip_address,
                subnet_mask=subnet_mask
            )
            
            if success:
                self.assistant.speak(message)
            else:
                self.assistant.speak(f"Failed to set IP configuration: {message}")
            
            return success
            
        except Exception:
            logging.exception("Failed to set IP configuration")
            self.assistant.speak("Failed to set IP configuration")
            return False
    
    def _handle_flush_dns_cache(self) -> bool:
        """Handle flush DNS cache command."""
        if not self.assistant.has_permission('flush_dns_cache'):
            return False
        
        try:
            if not hasattr(self.assistant, 'network_manager') or not self.assistant.network_manager:
                self.assistant.speak("Network management is not available")
                return False
            
            success, message = self.assistant.network_manager.flush_dns_cache()
            
            if success:
                self.assistant.speak(message)
            else:
                self.assistant.speak(f"Failed to flush DNS cache: {message}")
            
            return success
            
        except Exception:
            logging.exception("Failed to flush DNS cache")
            self.assistant.speak("Failed to flush DNS cache")
            return False
    
    def _handle_register_dns(self) -> bool:
        """Handle register DNS command."""
        if not self.assistant.has_permission('register_dns'):
            return False
        
        try:
            if not hasattr(self.assistant, 'network_manager') or not self.assistant.network_manager:
                self.assistant.speak("Network management is not available")
                return False
            
            success, message = self.assistant.network_manager.register_dns()
            
            if success:
                self.assistant.speak(message)
            else:
                self.assistant.speak(f"Failed to register DNS: {message}")
            
            return success
            
        except Exception:
            logging.exception("Failed to register DNS")
            self.assistant.speak("Failed to register DNS")
            return False
    
    def _handle_test_connectivity(self, slots: dict) -> bool:
        """Handle test network connectivity command."""
        try:
            if not hasattr(self.assistant, 'network_manager') or not self.assistant.network_manager:
                self.assistant.speak("Network management is not available")
                return False
            
            host = slots.get('host')
            if not host:
                self.assistant.speak("Please specify a hostname or IP address")
                return False
            
            port = slots.get('port')
            success, message = self.assistant.network_manager.test_network_connectivity(
                host=host,
                port=int(port) if port else None
            )
            
            self.assistant.speak(message)
            return success
            
        except Exception:
            logging.exception("Failed to test connectivity")
            self.assistant.speak("Failed to test connectivity")
            return False
    
    def _handle_list_network_shares(self) -> bool:
        """Handle list network shares command."""
        try:
            if not hasattr(self.assistant, 'network_manager') or not self.assistant.network_manager:
                self.assistant.speak("Network management is not available")
                return False
            
            shares = self.assistant.network_manager.get_network_shares()
            
            if shares:
                share_names = [s.get('name', 'Unknown') for s in shares[:10]]
                self.assistant.speak(f"Found {len(shares)} network shares: {', '.join(share_names)}")
            else:
                self.assistant.speak("No network shares found")
            
            return True
            
        except Exception:
            logging.exception("Failed to list network shares")
            self.assistant.speak("Failed to list network shares")
            return False
    
    def _handle_create_network_share(self, slots: dict) -> bool:
        """Handle create network share command."""
        if not self.assistant.has_permission('create_network_share'):
            return False
        
        try:
            if not hasattr(self.assistant, 'network_manager') or not self.assistant.network_manager:
                self.assistant.speak("Network management is not available")
                return False
            
            share_name = slots.get('share_name')
            path = slots.get('path')
            
            if not share_name or not path:
                self.assistant.speak("Please specify share name and path")
                return False
            
            success, message = self.assistant.network_manager.create_network_share(
                share_name=share_name,
                path=path,
                description=slots.get('description')
            )
            
            if success:
                self.assistant.speak(message)
            else:
                self.assistant.speak(f"Failed to create share: {message}")
            
            return success
            
        except Exception:
            logging.exception("Failed to create network share")
            self.assistant.speak("Failed to create network share")
            return False
    
    def _handle_delete_network_share(self, slots: dict) -> bool:
        """Handle delete network share command."""
        if not self.assistant.has_permission('delete_network_share'):
            return False
        
        try:
            if not hasattr(self.assistant, 'network_manager') or not self.assistant.network_manager:
                self.assistant.speak("Network management is not available")
                return False
            
            share_name = slots.get('share_name')
            if not share_name:
                self.assistant.speak("Please specify a share name")
                return False
            
            success, message = self.assistant.network_manager.delete_network_share(share_name)
            
            if success:
                self.assistant.speak(message)
            else:
                self.assistant.speak(f"Failed to delete share: {message}")
            
            return success
            
        except Exception:
            logging.exception("Failed to delete network share")
            self.assistant.speak("Failed to delete network share")
            return False
    
    def _handle_map_network_drive(self, slots: dict) -> bool:
        """Handle map network drive command."""
        if not self.assistant.has_permission('map_network_drive'):
            return False
        
        try:
            if not hasattr(self.assistant, 'network_manager') or not self.assistant.network_manager:
                self.assistant.speak("Network management is not available")
                return False
            
            drive_letter = slots.get('drive_letter')
            network_path = slots.get('network_path')
            
            if not drive_letter or not network_path:
                self.assistant.speak("Please specify drive letter and network path")
                return False
            
            success, message = self.assistant.network_manager.map_network_drive(
                drive_letter=drive_letter,
                network_path=network_path,
                persistent=slots.get('persistent', True)
            )
            
            if success:
                self.assistant.speak(message)
            else:
                self.assistant.speak(f"Failed to map drive: {message}")
            
            return success
            
        except Exception:
            logging.exception("Failed to map network drive")
            self.assistant.speak("Failed to map network drive")
            return False
    
    def _handle_unmap_network_drive(self, slots: dict) -> bool:
        """Handle unmap network drive command."""
        if not self.assistant.has_permission('unmap_network_drive'):
            return False
        
        try:
            if not hasattr(self.assistant, 'network_manager') or not self.assistant.network_manager:
                self.assistant.speak("Network management is not available")
                return False
            
            drive_letter = slots.get('drive_letter')
            if not drive_letter:
                self.assistant.speak("Please specify a drive letter")
                return False
            
            success, message = self.assistant.network_manager.unmap_network_drive(drive_letter)
            
            if success:
                self.assistant.speak(message)
            else:
                self.assistant.speak(f"Failed to unmap drive: {message}")
            
            return success
            
        except Exception:
            logging.exception("Failed to unmap network drive")
            self.assistant.speak("Failed to unmap network drive")
            return False
    
    def _handle_list_network_drives(self) -> bool:
        """Handle list network drives command."""
        try:
            if not hasattr(self.assistant, 'network_manager') or not self.assistant.network_manager:
                self.assistant.speak("Network management is not available")
                return False
            
            drives = self.assistant.network_manager.list_network_drives()
            
            if drives:
                drive_list = [f"{d.get('drive')} to {d.get('path')}" for d in drives]
                self.assistant.speak(f"Mapped drives: {', '.join(drive_list)}")
            else:
                self.assistant.speak("No network drives mapped")
            
            return True
            
        except Exception:
            logging.exception("Failed to list network drives")
            self.assistant.speak("Failed to list network drives")
            return False
    
    def _handle_list_firewall_rules(self, slots: dict) -> bool:
        """Handle list firewall rules command."""
        try:
            if not hasattr(self.assistant, 'firewall_manager') or not self.assistant.firewall_manager:
                self.assistant.speak("Firewall management is not available")
                return False
            
            name_filter = slots.get('name_filter')
            rules = self.assistant.firewall_manager.list_firewall_rules(name_filter)
            
            if rules:
                rule_names = [r.get('name', 'Unknown') for r in rules[:10]]
                self.assistant.speak(f"Found {len(rules)} firewall rules: {', '.join(rule_names)}")
            else:
                self.assistant.speak("No firewall rules found")
            
            return True
            
        except Exception:
            logging.exception("Failed to list firewall rules")
            self.assistant.speak("Failed to list firewall rules")
            return False
    
    def _handle_create_firewall_rule(self, slots: dict) -> bool:
        """Handle create firewall rule command."""
        if not self.assistant.has_permission('create_firewall_rule'):
            return False
        
        try:
            if not hasattr(self.assistant, 'firewall_manager') or not self.assistant.firewall_manager:
                self.assistant.speak("Firewall management is not available")
                return False
            
            name = slots.get('name')
            direction_str = slots.get('direction', 'inbound')
            action_str = slots.get('action', 'allow')
            protocol_str = slots.get('protocol', 'tcp')
            
            if not name:
                self.assistant.speak("Please specify a rule name")
                return False
            
            from integrations.firewall_manager import (
                FirewallRuleDirection, FirewallRuleAction, FirewallRuleProtocol
            )
            
            try:
                direction = FirewallRuleDirection(direction_str.lower())
                action = FirewallRuleAction(action_str.lower())
                protocol = FirewallRuleProtocol(protocol_str.lower())
            except ValueError as e:
                self.assistant.speak(f"Invalid parameter: {e}")
                return False
            
            success, message = self.assistant.firewall_manager.create_firewall_rule(
                name=name,
                direction=direction,
                action=action,
                protocol=protocol,
                local_port=slots.get('local_port'),
                remote_port=slots.get('remote_port')
            )
            
            if success:
                self.assistant.speak(message)
            else:
                self.assistant.speak(f"Failed to create firewall rule: {message}")
            
            return success
            
        except Exception:
            logging.exception("Failed to create firewall rule")
            self.assistant.speak("Failed to create firewall rule")
            return False
    
    def _handle_delete_firewall_rule(self, slots: dict) -> bool:
        """Handle delete firewall rule command."""
        if not self.assistant.has_permission('delete_firewall_rule'):
            return False
        
        try:
            if not hasattr(self.assistant, 'firewall_manager') or not self.assistant.firewall_manager:
                self.assistant.speak("Firewall management is not available")
                return False
            
            name = slots.get('name')
            if not name:
                self.assistant.speak("Please specify a rule name")
                return False
            
            success, message = self.assistant.firewall_manager.delete_firewall_rule(name)
            
            if success:
                self.assistant.speak(message)
            else:
                self.assistant.speak(f"Failed to delete firewall rule: {message}")
            
            return success
            
        except Exception:
            logging.exception("Failed to delete firewall rule")
            self.assistant.speak("Failed to delete firewall rule")
            return False
    
    def _handle_enable_firewall_rule(self, slots: dict) -> bool:
        """Handle enable firewall rule command."""
        if not self.assistant.has_permission('enable_firewall_rule'):
            return False
        
        try:
            if not hasattr(self.assistant, 'firewall_manager') or not self.assistant.firewall_manager:
                self.assistant.speak("Firewall management is not available")
                return False
            
            name = slots.get('name')
            if not name:
                self.assistant.speak("Please specify a rule name")
                return False
            
            success, message = self.assistant.firewall_manager.enable_firewall_rule(name)
            self.assistant.speak(message)
            return success
            
        except Exception:
            logging.exception("Failed to enable firewall rule")
            self.assistant.speak("Failed to enable firewall rule")
            return False
    
    def _handle_disable_firewall_rule(self, slots: dict) -> bool:
        """Handle disable firewall rule command."""
        if not self.assistant.has_permission('disable_firewall_rule'):
            return False
        
        try:
            if not hasattr(self.assistant, 'firewall_manager') or not self.assistant.firewall_manager:
                self.assistant.speak("Firewall management is not available")
                return False
            
            name = slots.get('name')
            if not name:
                self.assistant.speak("Please specify a rule name")
                return False
            
            success, message = self.assistant.firewall_manager.disable_firewall_rule(name)
            self.assistant.speak(message)
            return success
            
        except Exception:
            logging.exception("Failed to disable firewall rule")
            self.assistant.speak("Failed to disable firewall rule")
            return False
    
    def _handle_get_firewall_status(self) -> bool:
        """Handle get firewall status command."""
        try:
            if not hasattr(self.assistant, 'firewall_manager') or not self.assistant.firewall_manager:
                self.assistant.speak("Firewall management is not available")
                return False
            
            status = self.assistant.firewall_manager.get_firewall_status()
            
            if status:
                state = status.get('state', 'Unknown')
                self.assistant.speak(f"Firewall status: {state}")
            else:
                self.assistant.speak("Could not get firewall status")
            
            return True
            
        except Exception:
            logging.exception("Failed to get firewall status")
            self.assistant.speak("Failed to get firewall status")
            return False
    
    def _handle_get_listening_ports(self) -> bool:
        """Handle get listening ports command."""
        try:
            if not hasattr(self.assistant, 'port_monitor') or not self.assistant.port_monitor:
                self.assistant.speak("Port monitoring is not available")
                return False
            
            ports = self.assistant.port_monitor.get_listening_ports()
            
            if ports:
                port_list = [f"port {p.get('port')}" for p in ports[:10]]
                self.assistant.speak(f"Listening ports: {', '.join(port_list)}")
            else:
                self.assistant.speak("No listening ports found")
            
            return True
            
        except Exception:
            logging.exception("Failed to get listening ports")
            self.assistant.speak("Failed to get listening ports")
            return False
    
    def _handle_test_port(self, slots: dict) -> bool:
        """Handle test port command."""
        try:
            if not hasattr(self.assistant, 'port_monitor') or not self.assistant.port_monitor:
                self.assistant.speak("Port monitoring is not available")
                return False
            
            host = slots.get('host')
            port = slots.get('port')
            
            if not host or not port:
                self.assistant.speak("Please specify host and port")
                return False
            
            success, message = self.assistant.port_monitor.test_port(host, int(port))
            self.assistant.speak(message)
            return success
            
        except Exception:
            logging.exception("Failed to test port")
            self.assistant.speak("Failed to test port")
            return False
    
    def _handle_get_port_statistics(self) -> bool:
        """Handle get port statistics command."""
        try:
            if not hasattr(self.assistant, 'port_monitor') or not self.assistant.port_monitor:
                self.assistant.speak("Port monitoring is not available")
                return False
            
            stats = self.assistant.port_monitor.get_port_statistics()
            
            if stats:
                self.assistant.speak(
                    f"Port statistics: {stats.get('total_connections', 0)} total connections, "
                    f"{stats.get('listening', 0)} listening, "
                    f"{stats.get('established', 0)} established"
                )
            else:
                self.assistant.speak("Could not get port statistics")
            
            return True
            
        except Exception:
            logging.exception("Failed to get port statistics")
            self.assistant.speak("Failed to get port statistics")
            return False
    
    def _handle_connect_vpn(self, slots: dict) -> bool:
        """Handle connect VPN command."""
        if not self.assistant.has_permission('connect_vpn'):
            return False
        
        try:
            if not hasattr(self.assistant, 'vpn_manager') or not self.assistant.vpn_manager:
                self.assistant.speak("VPN management is not available")
                return False
            
            vpn_name = slots.get('vpn_name')
            if not vpn_name:
                self.assistant.speak("Please specify a VPN name")
                return False
            
            success, message = self.assistant.vpn_manager.connect_vpn(vpn_name)
            
            if success:
                self.assistant.speak(message)
            else:
                self.assistant.speak(f"Failed to connect VPN: {message}")
            
            return success
            
        except Exception:
            logging.exception("Failed to connect VPN")
            self.assistant.speak("Failed to connect VPN")
            return False
    
    def _handle_disconnect_vpn(self, slots: dict) -> bool:
        """Handle disconnect VPN command."""
        if not self.assistant.has_permission('disconnect_vpn'):
            return False
        
        try:
            if not hasattr(self.assistant, 'vpn_manager') or not self.assistant.vpn_manager:
                self.assistant.speak("VPN management is not available")
                return False
            
            vpn_name = slots.get('vpn_name')
            success, message = self.assistant.vpn_manager.disconnect_vpn(vpn_name)
            
            if success:
                self.assistant.speak(message)
            else:
                self.assistant.speak(f"Failed to disconnect VPN: {message}")
            
            return success
            
        except Exception:
            logging.exception("Failed to disconnect VPN")
            self.assistant.speak("Failed to disconnect VPN")
            return False
    
    def _handle_list_vpn_connections(self) -> bool:
        """Handle list VPN connections command."""
        try:
            if not hasattr(self.assistant, 'vpn_manager') or not self.assistant.vpn_manager:
                self.assistant.speak("VPN management is not available")
                return False
            
            vpns = self.assistant.vpn_manager.list_vpn_connections()
            
            if vpns:
                vpn_names = [v.get('name', 'Unknown') for v in vpns]
                self.assistant.speak(f"VPN connections: {', '.join(vpn_names)}")
            else:
                self.assistant.speak("No VPN connections found")
            
            return True
            
        except Exception:
            logging.exception("Failed to list VPN connections")
            self.assistant.speak("Failed to list VPN connections")
            return False
