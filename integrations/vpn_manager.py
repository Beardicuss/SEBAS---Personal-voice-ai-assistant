"""
VPN Connection Management (Hardened)
Phase 2.2: Windows-only implementation.
"""

import logging
import subprocess
import platform
import json
import shlex
from sebas.typing import Optional, Dict, List, Tuple
from sebas.enum import Enum


class VPNConnectionState(Enum):
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    DISCONNECTING = "disconnecting"
    UNKNOWN = "unknown"


class VPNManager:
    """Manages Windows VPN connections via PowerShell or rasdial."""

    def __init__(self):
        if platform.system() != "Windows":
            raise RuntimeError("VPNManager only works on Windows")

    # --------------------------------------------------------------
    # LIST CONNECTIONS
    # --------------------------------------------------------------
    def list_vpn_connections(self) -> List[Dict[str, str]]:
        """List all configured VPN connections using PowerShell or rasphone fallback."""
        try:
            ps_cmd = (
                "Get-VpnConnection | "
                "Select-Object Name, ServerAddress, ConnectionStatus | "
                "ConvertTo-Json -Compress"
            )
            result = subprocess.run(
                ["powershell", "-Command", ps_cmd],
                capture_output=True,
                text=True,
                timeout=10
            )

            vpns: List[Dict[str, str]] = []
            if result.returncode == 0 and result.stdout.strip():
                try:
                    data = json.loads(result.stdout)
                    if isinstance(data, dict):
                        data = [data]
                    for vpn in data:
                        vpns.append({
                            "name": vpn.get("Name", ""),
                            "server": vpn.get("ServerAddress", ""),
                            "status": vpn.get("ConnectionStatus", "Unknown"),
                        })
                    return vpns
                except json.JSONDecodeError:
                    pass  # Fallback to rasphone below

            # ---- Fallback (legacy) ----
            result = subprocess.run(
                ["rasphone", "-l"],
                capture_output=True,
                text=True,
                timeout=10
            )
            lines = [l.strip() for l in result.stdout.splitlines() if l.strip()]
            for line in lines:
                if not line.lower().startswith("rasphone"):
                    vpns.append({"name": line, "server": "", "status": "Unknown"})
            return vpns

        except Exception:
            logging.exception("list_vpn_connections failed")
            return []

    # --------------------------------------------------------------
    # CONNECT / DISCONNECT
    # --------------------------------------------------------------
    def connect_vpn(self, vpn_name: str,
                    username: Optional[str] = None,
                    password: Optional[str] = None) -> Tuple[bool, str]:
        """Connect to a VPN connection. Optional credentials supported."""
        try:
            name = shlex.quote(vpn_name)
            cmd = ["rasdial", name]
            if username and password:
                cmd.extend([username, password])

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

            if result.returncode == 0:
                logging.info(f"VPN '{vpn_name}' connected.")
                return True, f"VPN '{vpn_name}' connected successfully."
            else:
                err = result.stderr.strip() or result.stdout.strip()
                return False, err or "Failed to connect VPN."

        except subprocess.TimeoutExpired:
            return False, "VPN connection timed out."
        except Exception:
            logging.exception("connect_vpn failed")
            return False, f"Failed to connect to VPN '{vpn_name}'."

    def disconnect_vpn(self, vpn_name: Optional[str] = None) -> Tuple[bool, str]:
        """Disconnect one or all VPN connections."""
        try:
            cmd = ["rasdial"]
            if vpn_name:
                cmd.append(vpn_name)
            cmd.append("/disconnect")

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)

            if result.returncode == 0:
                msg = f"VPN '{vpn_name or 'all'}' disconnected successfully."
                logging.info(msg)
                return True, msg
            else:
                err = result.stderr.strip() or result.stdout.strip()
                return False, err or "Failed to disconnect VPN."

        except Exception:
            logging.exception("disconnect_vpn failed")
            return False, f"Failed to disconnect VPN '{vpn_name or 'all'}'."

    # --------------------------------------------------------------
    # STATUS
    # --------------------------------------------------------------
    def get_vpn_status(self, vpn_name: str) -> Optional[VPNConnectionState]:
        """Return VPN status if known."""
        try:
            vpns = self.list_vpn_connections()
            for vpn in vpns:
                if vpn.get("name", "").lower() == vpn_name.lower():
                    status = vpn.get("status", "").lower()
                    if "connected" in status:
                        return VPNConnectionState.CONNECTED
                    if "disconnected" in status:
                        return VPNConnectionState.DISCONNECTED
                    if "connecting" in status:
                        return VPNConnectionState.CONNECTING
                    if "disconnecting" in status:
                        return VPNConnectionState.DISCONNECTING
                    return VPNConnectionState.UNKNOWN
            return None
        except Exception:
            logging.exception("get_vpn_status failed")
            return None