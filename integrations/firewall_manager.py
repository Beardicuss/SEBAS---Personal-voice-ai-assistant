# -*- coding: utf-8 -*-
"""
Windows Firewall Management
Phase 2.2: Firewall rule creation and modification (hardened version)
"""

import logging
import subprocess
import platform
import shlex
from typing import Optional, Dict, List, Tuple
from enum import Enum


class FirewallRuleDirection(Enum):
    INBOUND = "in"
    OUTBOUND = "out"


class FirewallRuleAction(Enum):
    ALLOW = "allow"
    BLOCK = "block"


class FirewallRuleProtocol(Enum):
    TCP = "TCP"
    UDP = "UDP"
    ANY = "ANY"


class FirewallManager:
    """Manages Windows Firewall rules using `netsh advfirewall`."""

    def __init__(self):
        if platform.system() != 'Windows':
            raise RuntimeError("FirewallManager only works on Windows")
        self._check_admin_rights()

    def _check_admin_rights(self):
        """Warn if not running with admin privileges."""
        try:
            import ctypes
            if not ctypes.windll.shell32.IsUserAnAdmin():
                logging.warning("[FirewallManager] Not running as Administrator. Commands may fail.")
        except Exception:
            pass

    def _run_netsh(self, args: List[str], timeout: int = 15) -> Tuple[bool, str]:
        """Execute a netsh command safely."""
        try:
            cmd = ["netsh", "advfirewall"] + args
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
            out = (result.stdout or "").strip()
            err = (result.stderr or "").strip()
            msg = err or out
            if result.returncode == 0:
                return True, out
            logging.warning(f"[FirewallManager] netsh failed: {msg}")
            return False, msg
        except subprocess.TimeoutExpired:
            return False, "Command timed out"
        except FileNotFoundError:
            return False, "netsh not found (Windows only)"
        except Exception:
            logging.exception("[FirewallManager] netsh execution failed")
            return False, "Unexpected failure"

    def create_firewall_rule(self, name: str,
                             direction: FirewallRuleDirection,
                             action: FirewallRuleAction,
                             protocol: FirewallRuleProtocol,
                             local_port: Optional[int] = None,
                             remote_port: Optional[int] = None,
                             local_ip: Optional[str] = None,
                             remote_ip: Optional[str] = None,
                             program: Optional[str] = None,
                             enabled: bool = True) -> Tuple[bool, str]:
        """Create a new firewall rule."""
        try:
            name = shlex.quote(name)
            args = [
                "firewall", "add", "rule",
                f"name={name}",
                f"dir={direction.value}",
                f"action={action.value}",
                f"protocol={protocol.value}"
            ]
            if local_port:
                args.append(f"localport={local_port}")
            if remote_port:
                args.append(f"remoteport={remote_port}")
            if local_ip:
                args.append(f"localip={local_ip}")
            if remote_ip:
                args.append(f"remoteip={remote_ip}")
            if program:
                args.append(f"program={program}")
            args.append(f"enable={'yes' if enabled else 'no'}")

            ok, msg = self._run_netsh(args)
            if ok:
                logging.info(f"[FirewallManager] Created rule {name}")
                return True, f"Firewall rule '{name}' created successfully"
            return False, msg
        except Exception:
            logging.exception("[FirewallManager] Failed to create rule")
            return False, "Exception while creating rule"

    def delete_firewall_rule(self, name: str) -> Tuple[bool, str]:
        """Delete a firewall rule."""
        name = shlex.quote(name)
        ok, msg = self._run_netsh(["firewall", "delete", "rule", f"name={name}"])
        if ok:
            logging.info(f"[FirewallManager] Deleted rule {name}")
            return True, f"Firewall rule '{name}' deleted"
        return False, msg

    def list_firewall_rules(self, name_filter: Optional[str] = None) -> Tuple[bool, List[Dict[str, str]]]:
        """List firewall rules (optionally filtered by name)."""
        args = ["firewall", "show", "rule", f"name={name_filter or 'all'}"]
        ok, output = self._run_netsh(args, timeout=30)
        if not ok:
            return False, []

        rules: List[Dict[str, str]] = []
        current_rule: Dict[str, str] = {}

        for line in output.splitlines():
            line = line.strip()
            if not line:
                if current_rule:
                    rules.append(current_rule)
                    current_rule = {}
                continue
            if ':' in line:
                key, value = line.split(':', 1)
                key = key.strip().lower().replace(' ', '_')
                value = value.strip()
                current_rule[key] = value
        if current_rule:
            rules.append(current_rule)
        return True, rules

    def set_firewall_rule_state(self, name: str, enable: bool) -> Tuple[bool, str]:
        """Enable or disable a firewall rule."""
        name = shlex.quote(name)
        state = 'yes' if enable else 'no'
        ok, msg = self._run_netsh(["firewall", "set", "rule", f"name={name}", "new", f"enable={state}"])
        if ok:
            action = "enabled" if enable else "disabled"
            return True, f"Firewall rule '{name}' {action}"
        return False, msg

    def get_firewall_status(self) -> Tuple[bool, Dict[str, str]]:
        """Return overall firewall state for all profiles."""
        ok, output = self._run_netsh(["show", "allprofiles", "state"])
        if not ok:
            return False, {}

        status: Dict[str, str] = {}
        current_profile = None
        for line in output.splitlines():
            line = line.strip()
            if not line:
                continue
            if line.lower().endswith("profile settings:"):
                current_profile = line.split()[0].lower()
            elif ":" in line:
                key, val = line.split(":", 1)
                key, val = key.strip(), val.strip()
                if current_profile and "state" in key.lower():
                    status[current_profile] = val
        return True, status