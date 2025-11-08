# -*- coding: utf-8 -*-
"""
Network Administration
Phase 2.2: Advanced Network Management
"""

import logging
import subprocess
import platform
import socket
from typing import Optional, Dict, List, Tuple
from enum import Enum


class IPConfigType(Enum):
    """IP configuration types"""
    DHCP = "dhcp"
    STATIC = "static"


class NetworkManager:
    """
    Manages network configuration and operations.
    """
    
    def __init__(self):
        """Initialize Network Manager."""
        if platform.system() != 'Windows':
            raise RuntimeError("NetworkManager only works on Windows")
    
    def get_ip_config(self, interface_name: Optional[str] = None) -> List[Dict[str, str]]:
        """
        Get IP configuration for network interfaces.
        
        Args:
            interface_name: Optional interface name to filter
            
        Returns:
            List of interface configuration dicts
        """
        try:
            cmd = ["ipconfig", "/all"]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            
            if result.returncode != 0:
                logging.warning("Failed to get IP configuration")
                return []
            
            interfaces = []
            current_interface = {}
            
            for line in result.stdout.split('\n'):
                line = line.strip()
                
                if not line:
                    continue
                
                # Detect interface name
                if 'adapter' in line.lower() and ':' in line:
                    if current_interface:
                        interfaces.append(current_interface)
                    interface_name_found = line.split(':', 1)[1].strip()
                    current_interface = {'name': interface_name_found}
                
                # Parse IP address
                elif 'IPv4 Address' in line or 'IP Address' in line:
                    if ':' in line:
                        ip = line.split(':', 1)[1].strip().split('(')[0].strip()
                        current_interface['ip_address'] = ip
                
                # Parse subnet mask
                elif 'Subnet Mask' in line:
                    if ':' in line:
                        mask = line.split(':', 1)[1].strip()
                        current_interface['subnet_mask'] = mask
                
                # Parse default gateway
                elif 'Default Gateway' in line:
                    if ':' in line:
                        gateway = line.split(':', 1)[1].strip()
                        if gateway and gateway != '':
                            current_interface['default_gateway'] = gateway
                
                # Parse DNS servers
                elif 'DNS Servers' in line or 'DNS Server' in line:
                    if ':' in line:
                        dns = line.split(':', 1)[1].strip()
                        if 'dns_servers' not in current_interface:
                            current_interface['dns_servers'] = []
                        if dns:
                            current_interface['dns_servers'].append(dns)
            
            # Add last interface
            if current_interface:
                interfaces.append(current_interface)
            
            # Filter by interface name if specified
            if interface_name:
                interfaces = [i for i in interfaces if interface_name.lower() in i.get('name', '').lower()]
            
            return interfaces
            
        except Exception:
            logging.exception("Failed to get IP configuration")
            return []
    
    def set_ip_config(self, interface_name: str, config_type: IPConfigType,
                     ip_address: Optional[str] = None,
                     subnet_mask: Optional[str] = None,
                     default_gateway: Optional[str] = None,
                     dns_servers: Optional[List[str]] = None) -> Tuple[bool, str]:
        """
        Set IP configuration for a network interface.
        
        Args:
            interface_name: Interface name
            config_type: DHCP or STATIC
            ip_address: IP address (required for STATIC)
            subnet_mask: Subnet mask (required for STATIC)
            default_gateway: Default gateway (optional for STATIC)
            dns_servers: DNS servers list (optional)
            
        Returns:
            Tuple of (success, message)
        """
        try:
            if config_type == IPConfigType.DHCP:
                # Set to DHCP
                cmd = ["netsh", "interface", "ip", "set", "address", 
                      f"name={interface_name}", "source=dhcp"]
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
                
                if result.returncode != 0:
                    return False, result.stderr.strip() or result.stdout.strip()
                
                # Set DNS to DHCP
                cmd = ["netsh", "interface", "ip", "set", "dns", 
                      f"name={interface_name}", "source=dhcp"]
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
                
                logging.info(f"Interface {interface_name} set to DHCP")
                return True, "IP configuration set to DHCP"
            
            elif config_type == IPConfigType.STATIC:
                if not ip_address or not subnet_mask:
                    return False, "IP address and subnet mask required for static configuration"
                
                # Set static IP
                cmd = ["netsh", "interface", "ip", "set", "address",
                      f"name={interface_name}", "static", ip_address, subnet_mask]
                
                if default_gateway:
                    cmd.append(default_gateway)
                
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
                
                if result.returncode != 0:
                    return False, result.stderr.strip() or result.stdout.strip()
                
                # Set DNS servers if provided
                if dns_servers:
                    for i, dns in enumerate(dns_servers):
                        if i == 0:
                            cmd = ["netsh", "interface", "ip", "set", "dns",
                                  f"name={interface_name}", "static", dns]
                        else:
                            cmd = ["netsh", "interface", "ip", "add", "dns",
                                  f"name={interface_name}", dns, "index={}".format(i+1)]
                        
                        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
                        if result.returncode != 0:
                            logging.warning(f"Failed to set DNS server {dns}")
                
                logging.info(f"Interface {interface_name} set to static IP {ip_address}")
                return True, f"IP configuration set to static: {ip_address}"
            
            return False, "Invalid configuration type"
            
        except Exception:
            logging.exception(f"Failed to set IP configuration for {interface_name}")
            return False, "Failed to set IP configuration"
    
    def flush_dns_cache(self) -> Tuple[bool, str]:
        """
        Flush DNS cache.
        
        Returns:
            Tuple of (success, message)
        """
        try:
            result = subprocess.run(
                ["ipconfig", "/flushdns"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                logging.info("DNS cache flushed")
                return True, "DNS cache flushed successfully"
            else:
                error = result.stderr.strip() or result.stdout.strip()
                return False, error
                
        except Exception:
            logging.exception("Failed to flush DNS cache")
            return False, "Failed to flush DNS cache"
    
    def register_dns(self) -> Tuple[bool, str]:
        """
        Register DNS records.
        
        Returns:
            Tuple of (success, message)
        """
        try:
            result = subprocess.run(
                ["ipconfig", "/registerdns"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                logging.info("DNS registration initiated")
                return True, "DNS registration initiated"
            else:
                error = result.stderr.strip() or result.stdout.strip()
                return False, error
                
        except Exception:
            logging.exception("Failed to register DNS")
            return False, "Failed to register DNS"
    
    def test_network_connectivity(self, host: str, port: Optional[int] = None) -> Tuple[bool, str]:
        """
        Test network connectivity to a host.
        
        Args:
            host: Hostname or IP address
            port: Optional port number (defaults to ping if not specified)
            
        Returns:
            Tuple of (success, message)
        """
        try:
            if port:
                # Test TCP connection
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(5)
                result = sock.connect_ex((host, port))
                sock.close()
                
                if result == 0:
                    return True, f"Connection to {host}:{port} successful"
                else:
                    return False, f"Connection to {host}:{port} failed"
            else:
                # Ping test
                result = subprocess.run(
                    ["ping", "-n", "1", "-w", "1000", host],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                
                if result.returncode == 0:
                    return True, f"Ping to {host} successful"
                else:
                    return False, f"Ping to {host} failed"
                    
        except Exception:
            logging.exception(f"Failed to test connectivity to {host}")
            return False, f"Failed to test connectivity to {host}"
    
    def get_network_shares(self) -> List[Dict[str, str]]:
        """
        Get list of network shares.
        
        Returns:
            List of share information dicts
        """
        try:
            result = subprocess.run(
                ["net", "share"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode != 0:
                return []
            
            shares = []
            for line in result.stdout.split('\n'):
                line = line.strip()
                if line and not line.startswith('Share name') and not line.startswith('---'):
                    parts = line.split()
                    if len(parts) >= 2:
                        shares.append({
                            'name': parts[0],
                            'path': ' '.join(parts[1:]) if len(parts) > 1 else ''
                        })
            
            return shares
            
        except Exception:
            logging.exception("Failed to get network shares")
            return []
    
    def create_network_share(self, share_name: str, path: str, 
                            description: Optional[str] = None) -> Tuple[bool, str]:
        """
        Create a network share.
        
        Args:
            share_name: Name of the share
            path: Path to share
            description: Optional description
            
        Returns:
            Tuple of (success, message)
        """
        try:
            cmd = ["net", "share", f"{share_name}={path}"]
            if description:
                cmd.append(f"/remark:{description}")
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                logging.info(f"Network share {share_name} created")
                return True, f"Share {share_name} created successfully"
            else:
                error = result.stderr.strip() or result.stdout.strip()
                return False, error
                
        except Exception:
            logging.exception(f"Failed to create network share {share_name}")
            return False, "Failed to create network share"
    
    def delete_network_share(self, share_name: str) -> Tuple[bool, str]:
        """
        Delete a network share.
        
        Args:
            share_name: Name of the share to delete
            
        Returns:
            Tuple of (success, message)
        """
        try:
            result = subprocess.run(
                ["net", "share", share_name, "/delete"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                logging.info(f"Network share {share_name} deleted")
                return True, f"Share {share_name} deleted successfully"
            else:
                error = result.stderr.strip() or result.stdout.strip()
                return False, error
                
        except Exception:
            logging.exception(f"Failed to delete network share {share_name}")
            return False, "Failed to delete network share"
    
    def map_network_drive(self, drive_letter: str, network_path: str, 
                          persistent: bool = True, username: Optional[str] = None,
                          password: Optional[str] = None) -> Tuple[bool, str]:
        """
        Map a network drive.
        
        Args:
            drive_letter: Drive letter (e.g., 'Z:')
            network_path: Network path (e.g., '\\\\server\\share')
            persistent: Make mapping persistent across reboots
            username: Optional username for authentication
            password: Optional password for authentication
            
        Returns:
            Tuple of (success, message)
        """
        try:
            cmd = ["net", "use", drive_letter, network_path]
            if persistent:
                cmd.append("/persistent:yes")
            else:
                cmd.append("/persistent:no")
            
            if username:
                cmd.append(f"/user:{username}")
                if password:
                    # Note: Password should be passed securely, not in command line
                    # This is a simplified version
                    logging.warning("Password passed in command line - consider using secure method")
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                logging.info(f"Network drive {drive_letter} mapped to {network_path}")
                return True, f"Drive {drive_letter} mapped successfully"
            else:
                error = result.stderr.strip() or result.stdout.strip()
                return False, error
                
        except Exception:
            logging.exception(f"Failed to map network drive {drive_letter}")
            return False, "Failed to map network drive"
    
    def unmap_network_drive(self, drive_letter: str) -> Tuple[bool, str]:
        """
        Unmap a network drive.
        
        Args:
            drive_letter: Drive letter to unmap
            
        Returns:
            Tuple of (success, message)
        """
        try:
            result = subprocess.run(
                ["net", "use", drive_letter, "/delete"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                logging.info(f"Network drive {drive_letter} unmapped")
                return True, f"Drive {drive_letter} unmapped successfully"
            else:
                error = result.stderr.strip() or result.stdout.strip()
                return False, error
                
        except Exception:
            logging.exception(f"Failed to unmap network drive {drive_letter}")
            return False, "Failed to unmap network drive"
    
    def list_network_drives(self) -> List[Dict[str, str]]:
        """
        List mapped network drives.
        
        Returns:
            List of network drive information dicts
        """
        try:
            result = subprocess.run(
                ["net", "use"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode != 0:
                return []
            
            drives = []
            for line in result.stdout.split('\n'):
                line = line.strip()
                if line and 'Remote name' not in line and 'Status' not in line and '---' not in line:
                    parts = line.split()
                    if len(parts) >= 2 and ':' in parts[0]:
                        drives.append({
                            'drive': parts[0],
                            'path': ' '.join(parts[1:-1]) if len(parts) > 2 else parts[1],
                            'status': parts[-1] if len(parts) > 1 else 'Unknown'
                        })
            
            return drives
            
        except Exception:
            logging.exception("Failed to list network drives")
            return []

