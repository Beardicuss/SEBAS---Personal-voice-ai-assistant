# -*- coding: utf-8 -*-
"""
Network Administration
Phase 2.2: Advanced Network Management (Hardened)
"""

import logging
import subprocess
import platform
import socket
import shlex
from typing import Optional, Dict, List, Tuple, Any
from sebas.enum import Enum


class IPConfigType(Enum):
    DHCP = "dhcp"
    STATIC = "static"


class NetworkManager:
    """Manages Windows network configuration."""

    def __init__(self):
        if platform.system() != "Windows":
            raise RuntimeError("NetworkManager only works on Windows")

    # ----------------------------------------------------------------
    # IP CONFIG
    # ----------------------------------------------------------------
    def get_ip_config(self, interface_name: Optional[str] = None) -> List[Dict[str, Any]]:
        """Parse `ipconfig /all` output."""
        try:
            result = subprocess.run(["ipconfig", "/all"], capture_output=True, text=True, timeout=10)
            if result.returncode != 0:
                logging.warning("Failed to get IP configuration")
                return []

            interfaces = []
            current: Dict[str, Any] = {}
            for line in result.stdout.splitlines():
                line = line.strip()
                if not line:
                    continue

                # Adapter section start
                if "adapter" in line.lower() and ":" in line:
                    if current:
                        interfaces.append(current)
                    name = line.split(":", 1)[0].replace("adapter", "").strip()
                    current = {"name": name}

                elif "IPv4 Address" in line or "IP Address" in line:
                    current["ip_address"] = line.split(":", 1)[1].split("(")[0].strip()
                elif "Subnet Mask" in line:
                    current["subnet_mask"] = line.split(":", 1)[1].strip()
                elif "Default Gateway" in line:
                    gw = line.split(":", 1)[1].strip()
                    if gw:
                        current["default_gateway"] = gw
                elif "DNS Servers" in line or "DNS Server" in line:
                    dns = line.split(":", 1)[1].strip() if ":" in line else ""
                    if dns:
                        dns_list = current.get("dns_servers", [])
                        dns_list.append(dns)
                        current["dns_servers"] = dns_list
                else:
                    # Handle subsequent DNS lines (without colon)
                    if line and line.replace(".", "").isdigit():
                        dns_list = current.get("dns_servers", [])
                        dns_list.append(line)
                        current["dns_servers"] = dns_list

            if current:
                interfaces.append(current)

            if interface_name:
                interfaces = [i for i in interfaces if interface_name.lower() in i.get("name", "").lower()]
            return interfaces

        except Exception:
            logging.exception("get_ip_config failed")
            return []

    # ----------------------------------------------------------------
    # CONFIGURATION
    # ----------------------------------------------------------------
    def set_ip_config(self, interface_name: str, config_type: IPConfigType,
                      ip_address: Optional[str] = None,
                      subnet_mask: Optional[str] = None,
                      default_gateway: Optional[str] = None,
                      dns_servers: Optional[List[str]] = None) -> Tuple[bool, str]:
        """Set interface to DHCP or static."""
        try:
            name = shlex.quote(interface_name)

            if config_type == IPConfigType.DHCP:
                for cmd in (
                    ["netsh", "interface", "ipv4", "set", "address", f"name={name}", "source=dhcp"],
                    ["netsh", "interface", "ipv4", "set", "dns", f"name={name}", "source=dhcp"]
                ):
                    subprocess.run(cmd, capture_output=True, text=True, timeout=10)
                return True, f"{interface_name} set to DHCP"

            elif config_type == IPConfigType.STATIC:
                if not ip_address or not subnet_mask:
                    return False, "IP address and subnet mask required"
                cmd = ["netsh", "interface", "ipv4", "set", "address",
                       f"name={name}", "static", ip_address, subnet_mask]
                if default_gateway:
                    cmd.append(default_gateway)
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
                if result.returncode != 0:
                    return False, result.stderr.strip() or result.stdout.strip()

                if dns_servers:
                    for i, dns in enumerate(dns_servers):
                        action = "set" if i == 0 else "add"
                        cmd = ["netsh", "interface", "ipv4", action, "dns",
                               f"name={name}", dns, f"index={i+1}"]
                        subprocess.run(cmd, capture_output=True, text=True, timeout=10)
                return True, f"{interface_name} set to static {ip_address}"
            return False, "Invalid configuration type"
        except Exception:
            logging.exception("set_ip_config failed")
            return False, "Failed to set IP configuration"

    # ----------------------------------------------------------------
    # DNS MANAGEMENT
    # ----------------------------------------------------------------
    def flush_dns_cache(self) -> Tuple[bool, str]:
        return self._simple_cmd(["ipconfig", "/flushdns"], "DNS cache flushed")

    def register_dns(self) -> Tuple[bool, str]:
        return self._simple_cmd(["ipconfig", "/registerdns"], "DNS registration started")

    # ----------------------------------------------------------------
    # CONNECTIVITY
    # ----------------------------------------------------------------
    def test_network_connectivity(self, host: str, port: Optional[int] = None) -> Tuple[bool, str]:
        """Ping or TCP test."""
        try:
            if port:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.settimeout(5)
                    result = s.connect_ex((host, port))
                    if result == 0:
                        return True, f"Connected to {host}:{port}"
                    return False, f"Connection to {host}:{port} failed"
            else:
                result = subprocess.run(["ping", "-n", "1", "-w", "1000", host],
                                        capture_output=True, text=True, timeout=5)
                if result.returncode == 0:
                    return True, f"Ping to {host} successful"
                return False, f"Ping to {host} failed"
        except Exception:
            logging.exception("Connectivity test failed")
            return False, f"Error testing {host}"

    # ----------------------------------------------------------------
    # SHARES
    # ----------------------------------------------------------------
    def get_network_shares(self) -> List[Dict[str, str]]:
        """Parse 'net share' output."""
        try:
            result = subprocess.run(["net", "share"], capture_output=True, text=True, timeout=10)
            if result.returncode != 0:
                return []
            lines = [l.strip() for l in result.stdout.splitlines() if l.strip()]
            shares = []
            for line in lines:
                if line.startswith("Share name") or line.startswith("---") or line.lower().startswith("the command"):
                    continue
                parts = line.split(maxsplit=1)
                if len(parts) == 2:
                    shares.append({"name": parts[0], "path": parts[1]})
            return shares
        except Exception:
            logging.exception("get_network_shares failed")
            return []

    def create_network_share(self, share_name: str, path: str, description: Optional[str] = None) -> Tuple[bool, str]:
        """Create share."""
        try:
            name, path = shlex.quote(share_name), shlex.quote(path)
            cmd = ["net", "share", f"{name}={path}"]
            if description:
                cmd.append(f"/remark:{description}")
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                return True, f"Share {share_name} created"
            return False, result.stderr.strip() or result.stdout.strip()
        except Exception:
            logging.exception("create_network_share failed")
            return False, "Failed to create share"

    def delete_network_share(self, share_name: str) -> Tuple[bool, str]:
        return self._simple_cmd(["net", "share", share_name, "/delete"], f"Share {share_name} deleted")

    # ----------------------------------------------------------------
    # DRIVES
    # ----------------------------------------------------------------
    def map_network_drive(self, drive_letter: str, network_path: str,
                          persistent: bool = True, username: Optional[str] = None,
                          password: Optional[str] = None) -> Tuple[bool, str]:
        """Map network drive."""
        try:
            cmd = ["net", "use", drive_letter, network_path,
                   f"/persistent:{'yes' if persistent else 'no'}"]
            if username:
                cmd += [f"/user:{username}"]
                if password:
                    logging.warning("Password passed on CLI (unsafe)")
                    cmd += [password]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                return True, f"{drive_letter} mapped to {network_path}"
            return False, result.stderr.strip() or result.stdout.strip()
        except Exception:
            logging.exception("map_network_drive failed")
            return False, "Failed to map drive"

    def unmap_network_drive(self, drive_letter: str) -> Tuple[bool, str]:
        return self._simple_cmd(["net", "use", drive_letter, "/delete"], f"{drive_letter} unmapped")

    def list_network_drives(self) -> List[Dict[str, str]]:
        """List mapped drives."""
        try:
            result = subprocess.run(["net", "use"], capture_output=True, text=True, timeout=10)
            if result.returncode != 0:
                return []
            drives = []
            for line in result.stdout.splitlines():
                line = line.strip()
                if line and ":" in line and "\\" in line:
                    parts = line.split()
                    drives.append({
                        "drive": parts[0],
                        "path": parts[1] if len(parts) > 1 else "",
                        "status": parts[-1] if len(parts) > 2 else "Unknown"
                    })
            return drives
        except Exception:
            logging.exception("list_network_drives failed")
            return []

    # ----------------------------------------------------------------
    # Helpers
    # ----------------------------------------------------------------
    def _simple_cmd(self, cmd: List[str], success_msg: str) -> Tuple[bool, str]:
        """Run a simple subprocess and return unified output."""
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                return True, success_msg
            return False, result.stderr.strip() or result.stdout.strip()
        except Exception:
            logging.exception(f"Command failed: {' '.join(cmd)}")
            return False, "Command execution failed"
