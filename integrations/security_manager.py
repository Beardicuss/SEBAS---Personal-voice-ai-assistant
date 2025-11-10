# -*- coding: utf-8 -*-
"""
Security Administration
Phase 4.1: Threat Management and Access Control
"""

import logging
import subprocess
import platform
import psutil
from typing import Optional, Dict, List, Tuple, Any
from enum import Enum
from datetime import datetime


class ThreatLevel(Enum):
    """Threat severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class SecurityManager:
    """
    Manages security operations including Windows Defender, malware detection,
    security patches, and suspicious process detection.
    """

    def __init__(self):
        """Initialize Security Manager."""
        if platform.system() != 'Windows':
            raise RuntimeError("SecurityManager only works on Windows")

    # ---------------- Defender Controls ----------------
    def get_defender_status(self) -> Dict[str, str]:
        """Get Windows Defender status."""
        try:
            ps_cmd = """
            $d = Get-MpComputerStatus
            @{
                'AntivirusEnabled' = $d.AntivirusEnabled
                'RealTimeProtectionEnabled' = $d.RealTimeProtectionEnabled
                'AntispywareEnabled' = $d.AntispywareEnabled
                'FirewallEnabled' = $d.FirewallEnabled
                'IsUpToDate' = $d.IsUpToDate
                'LastQuickScan' = $d.QuickScanStartTime
                'LastFullScan' = $d.FullScanStartTime
            } | ConvertTo-Json
            """
            result = subprocess.run(["powershell", "-Command", ps_cmd],
                                    capture_output=True, text=True, timeout=10)
            out = result.stdout.strip()
            if result.returncode == 0 and out:
                import json
                return json.loads(out)
            return {}
        except Exception:
            logging.exception("[SecurityManager] Failed to get Defender status")
            return {}

    def run_defender_scan(self, scan_type: str = "quick") -> Tuple[bool, str]:
        """Run Windows Defender scan."""
        try:
            ps_cmd = f"Start-MpScan -ScanType {scan_type}"
            result = subprocess.run(["powershell", "-Command", ps_cmd],
                                    capture_output=True, text=True, timeout=300)
            if result.returncode == 0:
                return True, f"Defender {scan_type} scan started"
            error = result.stderr.strip() or result.stdout.strip()
            return False, error
        except subprocess.TimeoutExpired:
            return False, "Scan timeout"
        except Exception:
            logging.exception("[SecurityManager] Failed to run Defender scan")
            return False, "Failed to start scan"

    def get_defender_threats(self) -> List[Dict[str, str]]:
        """Get detected threats from Windows Defender."""
        try:
            ps_cmd = """
            Get-MpThreatDetection | Select-Object ThreatName, InitialDetectionTime,
            Resources, ThreatID, Severity | ConvertTo-Json
            """
            result = subprocess.run(["powershell", "-Command", ps_cmd],
                                    capture_output=True, text=True, timeout=10)
            out = result.stdout.strip()
            if result.returncode == 0 and out:
                import json
                data = json.loads(out)
                if isinstance(data, list):
                    return data
                elif isinstance(data, dict):
                    return [data]
            return []
        except Exception:
            logging.exception("[SecurityManager] Failed to get Defender threats")
            return []

    def remove_defender_threat(self, threat_id: Optional[str] = None) -> Tuple[bool, str]:
        """Remove/quarantine a threat."""
        try:
            ps_cmd = (f"Remove-MpThreat -ThreatID {threat_id} -Force"
                      if threat_id else
                      "Get-MpThreatDetection | Remove-MpThreat -Force")
            result = subprocess.run(["powershell", "-Command", ps_cmd],
                                    capture_output=True, text=True, timeout=60)
            if result.returncode == 0:
                return True, "Threat removed successfully"
            error = result.stderr.strip() or result.stdout.strip()
            return False, error
        except Exception:
            logging.exception("[SecurityManager] Failed to remove Defender threat")
            return False, "Failed to remove threat"

    # ---------------- Windows Update ----------------
    def get_security_updates(self) -> List[Dict[str, str]]:
        """Get available security updates."""
        try:
            ps_cmd = """
            Get-WindowsUpdate -MicrosoftUpdate | Select-Object Title,
            IsDownloaded, IsInstalled, Size | ConvertTo-Json
            """
            result = subprocess.run(["powershell", "-Command", ps_cmd],
                                    capture_output=True, text=True, timeout=30)
            out = result.stdout.strip()
            if result.returncode == 0 and out:
                import json
                data = json.loads(out)
                if isinstance(data, list):
                    return data
                elif isinstance(data, dict):
                    return [data]

            # fallback: wmic
            result = subprocess.run(
                ["wmic", "qfe", "list", "brief", "/format:list"],
                capture_output=True, text=True, timeout=10
            )
            updates = []
            current = {}
            for line in result.stdout.splitlines():
                line = line.strip()
                if not line:
                    if current:
                        updates.append(current)
                        current = {}
                    continue
                if '=' in line:
                    key, value = line.split('=', 1)
                    current[key.strip().lower()] = value.strip()
            if current:
                updates.append(current)
            return updates
        except Exception:
            logging.exception("[SecurityManager] Failed to get security updates")
            return []

    # ---------------- Suspicious Process Detection ----------------
    def detect_suspicious_processes(self) -> List[Dict[str, Any]]:
        """Detect potentially suspicious processes."""
        suspicious = []
        try:
            suspicious_names = [
                'cmd.exe', 'powershell.exe', 'wscript.exe', 'cscript.exe',
                'mshta.exe', 'rundll32.exe', 'regsvr32.exe'
            ]
            suspicious_paths = ['temp', 'appdata\\local\\temp', 'downloads']

            for proc in psutil.process_iter(['pid', 'name', 'exe', 'username',
                                             'cmdline', 'cpu_percent', 'memory_percent']):
                try:
                    info = proc.info
                    name = (info.get('name') or '').lower()
                    path = (info.get('exe') or '').lower()
                    cmd = ' '.join(info.get('cmdline') or [])
                    reasons = []
                    threat = ThreatLevel.LOW

                    if name in suspicious_names:
                        reasons.append(f"Suspicious name: {name}")
                        threat = ThreatLevel.MEDIUM
                    if any(p in path for p in suspicious_paths):
                        reasons.append(f"Suspicious path: {path}")
                        threat = ThreatLevel.MEDIUM
                    if info.get('cpu_percent', 0) > 80:
                        reasons.append(f"High CPU: {info['cpu_percent']:.1f}%")
                        threat = ThreatLevel.HIGH
                    if info.get('memory_percent', 0) > 20:
                        reasons.append(f"High memory: {info['memory_percent']:.1f}%")
                    if cmd and len(cmd) > 200:
                        reasons.append("Long/obfuscated command line")
                        threat = ThreatLevel.MEDIUM

                    if reasons:
                        suspicious.append({
                            'pid': info.get('pid'),
                            'name': info.get('name'),
                            'path': info.get('exe'),
                            'username': info.get('username'),
                            'cmdline': cmd,
                            'cpu_percent': info.get('cpu_percent', 0),
                            'memory_percent': info.get('memory_percent', 0),
                            'reasons': reasons,
                            'threat_level': threat.value
                        })
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            return suspicious
        except Exception:
            logging.exception("[SecurityManager] Failed to detect suspicious processes")
            return []

    def terminate_process(self, pid: int, force: bool = False) -> Tuple[bool, str]:
        """Terminate a process."""
        try:
            proc = psutil.Process(pid)
            proc.terminate()
            if force:
                try:
                    proc.wait(timeout=5)
                except psutil.TimeoutExpired:
                    proc.kill()
            return True, f"Process {pid} terminated"
        except psutil.NoSuchProcess:
            return False, f"Process {pid} not found"
        except psutil.AccessDenied:
            return False, "Access denied. Administrator privileges required."
        except Exception:
            logging.exception(f"[SecurityManager] Failed to terminate {pid}")
            return False, "Failed to terminate process"

    # ---------------- File Permissions ----------------
    def get_file_permissions(self, path: str) -> Dict[str, str]:
        """Get file/folder permissions using ICACLS."""
        try:
            result = subprocess.run(["icacls", path],
                                    capture_output=True, text=True, timeout=10)
            return {
                'path': path,
                'permissions': result.stdout.strip() if result.returncode == 0 else '',
                'status': 'ok' if result.returncode == 0 else 'error'
            }
        except Exception:
            logging.exception(f"[SecurityManager] Failed to get permissions for {path}")
            return {'path': path, 'permissions': '', 'status': 'error'}

    def set_file_permissions(self, path: str, user: str, permissions: str,
                             recursive: bool = False) -> Tuple[bool, str]:
        """Set file/folder permissions using ICACLS."""
        try:
            cmd = ["icacls", path, "/grant", f"{user}:{permissions}"]
            if recursive:
                cmd.append("/T")
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                return True, f"Permissions set for {user} on {path}"
            error = result.stderr.strip() or result.stdout.strip()
            return False, error
        except Exception:
            logging.exception(f"[SecurityManager] Failed to set permissions for {path}")
            return False, "Failed to set permissions"

    # ---------------- Audit Policy ----------------
    def get_audit_policy(self) -> Dict[str, str]:
        """Get audit policy configuration."""
        try:
            result = subprocess.run(["auditpol", "/get", "/category:*"],
                                    capture_output=True, text=True, timeout=10)
            return {
                'raw_output': result.stdout.strip() if result.returncode == 0 else '',
                'status': 'ok' if result.returncode == 0 else 'error'
            }
        except Exception:
            logging.exception("[SecurityManager] Failed to get audit policy")
            return {'status': 'error', 'raw_output': ''}

    def set_audit_policy(self, category: str, subcategory: str,
                         success: bool = True, failure: bool = True) -> Tuple[bool, str]:
        """Set audit policy for a category."""
        try:
            if not (success or failure):
                return False, "At least one of success or failure must be enabled"

            results = []
            if success:
                results.append(
                    subprocess.run(
                        ["auditpol", "/set", f"/subcategory:{subcategory}", "/success:enable"],
                        capture_output=True, text=True, timeout=10
                    )
                )
            if failure:
                results.append(
                    subprocess.run(
                        ["auditpol", "/set", f"/subcategory:{subcategory}", "/failure:enable"],
                        capture_output=True, text=True, timeout=10
                    )
                )

            if all(r.returncode == 0 for r in results):
                return True, f"Audit policy set for {category}/{subcategory}"
            else:
                err = "; ".join((r.stderr or r.stdout).strip() for r in results)
                return False, err or "Unknown error"
        except Exception:
            logging.exception("[SecurityManager] Failed to set audit policy")
            return False, "Failed to set audit policy"
