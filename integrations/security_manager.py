# -*- coding: utf-8 -*-
"""
Security Administration
Phase 4.1: Threat Management and Access Control
"""

import logging
import subprocess
import platform
import psutil
from typing import Optional, Dict, List, Tuple
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
    
    def get_defender_status(self) -> Dict[str, str]:
        """
        Get Windows Defender status.
        
        Returns:
            Dict with Defender status information
        """
        try:
            # Use PowerShell to get Defender status
            ps_cmd = """
            $defender = Get-MpComputerStatus
            @{
                'AntivirusEnabled' = $defender.AntivirusEnabled
                'RealTimeProtectionEnabled' = $defender.RealTimeProtectionEnabled
                'AntispywareEnabled' = $defender.AntispywareEnabled
                'FirewallEnabled' = $defender.FirewallEnabled
                'IsUpToDate' = $defender.IsUpToDate
                'LastQuickScan' = $defender.QuickScanStartTime
                'LastFullScan' = $defender.FullScanStartTime
            } | ConvertTo-Json
            """
            
            result = subprocess.run(
                ["powershell", "-Command", ps_cmd],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                try:
                    import json
                    return json.loads(result.stdout)
                except:
                    pass
            
            return {}
            
        except Exception:
            logging.exception("Failed to get Defender status")
            return {}
    
    def run_defender_scan(self, scan_type: str = "quick") -> Tuple[bool, str]:
        """
        Run Windows Defender scan.
        
        Args:
            scan_type: Type of scan ('quick', 'full', 'custom')
            
        Returns:
            Tuple of (success, message)
        """
        try:
            # Use PowerShell to start scan
            ps_cmd = f"Start-MpScan -ScanType {scan_type}"
            
            result = subprocess.run(
                ["powershell", "-Command", ps_cmd],
                capture_output=True,
                text=True,
                timeout=300  # 5 minutes timeout
            )
            
            if result.returncode == 0:
                return True, f"Defender {scan_type} scan started"
            else:
                error = result.stderr.strip() or result.stdout.strip()
                return False, error
                
        except subprocess.TimeoutExpired:
            return False, "Scan timeout"
        except Exception:
            logging.exception("Failed to run Defender scan")
            return False, "Failed to start scan"
    
    def get_defender_threats(self) -> List[Dict[str, str]]:
        """
        Get detected threats from Windows Defender.
        
        Returns:
            List of threat information dicts
        """
        try:
            ps_cmd = """
            Get-MpThreatDetection | Select-Object ThreatName, InitialDetectionTime, 
            Resources, ThreatID, Severity | ConvertTo-Json
            """
            
            result = subprocess.run(
                ["powershell", "-Command", ps_cmd],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                try:
                    import json
                    data = json.loads(result.stdout)
                    if isinstance(data, list):
                        return data
                    elif isinstance(data, dict):
                        return [data]
                except:
                    pass
            
            return []
            
        except Exception:
            logging.exception("Failed to get Defender threats")
            return []
    
    def remove_defender_threat(self, threat_id: Optional[str] = None) -> Tuple[bool, str]:
        """
        Remove/quarantine a threat.
        
        Args:
            threat_id: Optional specific threat ID, or remove all threats
            
        Returns:
            Tuple of (success, message)
        """
        try:
            if threat_id:
                ps_cmd = f"Remove-MpThreat -ThreatID {threat_id} -Force"
            else:
                ps_cmd = "Get-MpThreatDetection | Remove-MpThreat -Force"
            
            result = subprocess.run(
                ["powershell", "-Command", ps_cmd],
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode == 0:
                return True, "Threat removed successfully"
            else:
                error = result.stderr.strip() or result.stdout.strip()
                return False, error
                
        except Exception:
            logging.exception("Failed to remove Defender threat")
            return False, "Failed to remove threat"
    
    def get_security_updates(self) -> List[Dict[str, str]]:
        """
        Get available security updates.
        
        Returns:
            List of update information dicts
        """
        try:
            # Use PowerShell to get Windows Updates
            ps_cmd = """
            Get-WindowsUpdate -MicrosoftUpdate | Select-Object Title, 
            IsDownloaded, IsInstalled, Size | ConvertTo-Json
            """
            
            result = subprocess.run(
                ["powershell", "-Command", ps_cmd],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                try:
                    import json
                    data = json.loads(result.stdout)
                    if isinstance(data, list):
                        return data
                    elif isinstance(data, dict):
                        return [data]
                except:
                    pass
            
            # Fallback: Use wmic
            result = subprocess.run(
                ["wmic", "qfe", "list", "brief", "/format:list"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            updates = []
            current_update = {}
            
            for line in result.stdout.split('\n'):
                line = line.strip()
                if not line:
                    if current_update:
                        updates.append(current_update)
                        current_update = {}
                    continue
                
                if '=' in line:
                    key, value = line.split('=', 1)
                    current_update[key.strip().lower()] = value.strip()
            
            if current_update:
                updates.append(current_update)
            
            return updates
            
        except Exception:
            logging.exception("Failed to get security updates")
            return []
    
    def detect_suspicious_processes(self) -> List[Dict[str, any]]:
        """
        Detect potentially suspicious processes.
        
        Returns:
            List of suspicious process information dicts
        """
        suspicious = []
        
        try:
            # Common suspicious patterns
            suspicious_names = [
                'cmd.exe', 'powershell.exe', 'wscript.exe', 'cscript.exe',
                'mshta.exe', 'rundll32.exe', 'regsvr32.exe'
            ]
            
            suspicious_paths = [
                'temp', 'appdata\\local\\temp', 'downloads'
            ]
            
            for proc in psutil.process_iter(['pid', 'name', 'exe', 'username', 'cmdline', 'cpu_percent', 'memory_percent']):
                try:
                    pinfo = proc.info
                    process_name = pinfo.get('name', '').lower()
                    process_path = (pinfo.get('exe') or '').lower()
                    cmdline = ' '.join(pinfo.get('cmdline', []) or [])
                    
                    suspicion_reasons = []
                    threat_level = ThreatLevel.LOW
                    
                    # Check for suspicious name
                    if process_name in suspicious_names:
                        suspicion_reasons.append(f"Suspicious process name: {process_name}")
                        threat_level = ThreatLevel.MEDIUM
                    
                    # Check for suspicious path
                    if any(susp_path in process_path for susp_path in suspicious_paths):
                        suspicion_reasons.append(f"Running from suspicious location: {process_path}")
                        threat_level = ThreatLevel.MEDIUM
                    
                    # Check for high CPU usage
                    if pinfo.get('cpu_percent', 0) > 80:
                        suspicion_reasons.append(f"High CPU usage: {pinfo['cpu_percent']:.1f}%")
                        threat_level = ThreatLevel.HIGH if threat_level == ThreatLevel.MEDIUM else threat_level
                    
                    # Check for high memory usage
                    if pinfo.get('memory_percent', 0) > 20:
                        suspicion_reasons.append(f"High memory usage: {pinfo['memory_percent']:.1f}%")
                    
                    # Check for obfuscated command line
                    if cmdline and len(cmdline) > 200:
                        suspicion_reasons.append("Long/obfuscated command line")
                        threat_level = ThreatLevel.MEDIUM
                    
                    if suspicion_reasons:
                        suspicious.append({
                            'pid': pinfo.get('pid'),
                            'name': pinfo.get('name'),
                            'path': pinfo.get('exe'),
                            'username': pinfo.get('username'),
                            'cmdline': cmdline,
                            'cpu_percent': pinfo.get('cpu_percent', 0),
                            'memory_percent': pinfo.get('memory_percent', 0),
                            'suspicion_reasons': suspicion_reasons,
                            'threat_level': threat_level.value
                        })
                        
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            return suspicious
            
        except Exception:
            logging.exception("Failed to detect suspicious processes")
            return []
    
    def terminate_process(self, pid: int, force: bool = False) -> Tuple[bool, str]:
        """
        Terminate a process.
        
        Args:
            pid: Process ID
            force: Force termination
            
        Returns:
            Tuple of (success, message)
        """
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
            logging.exception(f"Failed to terminate process {pid}")
            return False, "Failed to terminate process"
    
    def get_file_permissions(self, path: str) -> Dict[str, str]:
        """
        Get file/folder permissions using ICACLS.
        
        Args:
            path: File or folder path
            
        Returns:
            Dict with permission information
        """
        try:
            result = subprocess.run(
                ["icacls", path],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            permissions = {
                'path': path,
                'permissions': result.stdout.strip() if result.returncode == 0 else '',
                'status': 'ok' if result.returncode == 0 else 'error'
            }
            
            return permissions
            
        except Exception:
            logging.exception(f"Failed to get permissions for {path}")
            return {'path': path, 'permissions': '', 'status': 'error'}
    
    def set_file_permissions(self, path: str, user: str, permissions: str,
                            recursive: bool = False) -> Tuple[bool, str]:
        """
        Set file/folder permissions using ICACLS.
        
        Args:
            path: File or folder path
            user: User or group name
            permissions: Permission string (e.g., 'F' for full, 'R' for read, 'W' for write)
            recursive: Apply recursively to subdirectories
            
        Returns:
            Tuple of (success, message)
        """
        try:
            cmd = ["icacls", path, "/grant", f"{user}:{permissions}"]
            if recursive:
                cmd.append("/T")
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                return True, f"Permissions set for {user} on {path}"
            else:
                error = result.stderr.strip() or result.stdout.strip()
                return False, error
                
        except Exception:
            logging.exception(f"Failed to set permissions for {path}")
            return False, "Failed to set permissions"
    
    def get_audit_policy(self) -> Dict[str, str]:
        """
        Get audit policy configuration.
        
        Returns:
            Dict with audit policy information
        """
        try:
            result = subprocess.run(
                ["auditpol", "/get", "/category:*"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            policy = {
                'raw_output': result.stdout.strip() if result.returncode == 0 else '',
                'status': 'ok' if result.returncode == 0 else 'error'
            }
            
            return policy
            
        except Exception:
            logging.exception("Failed to get audit policy")
            return {'status': 'error', 'raw_output': ''}
    
    def set_audit_policy(self, category: str, subcategory: str, 
                        success: bool = True, failure: bool = True) -> Tuple[bool, str]:
        """
        Set audit policy for a category.
        
        Args:
            category: Audit category
            subcategory: Audit subcategory
            success: Audit successful attempts
            failure: Audit failed attempts
            
        Returns:
            Tuple of (success, message)
        """
        try:
            settings = []
            if success:
                settings.append("Success")
            if failure:
                settings.append("Failure")
            
            if not settings:
                return False, "At least one of success or failure must be enabled"
            
            setting_str = ':'.join(settings)
            
            result = subprocess.run(
                ["auditpol", "/set", f"/category:{category}", f"/subcategory:{subcategory}", f"/{setting_str.lower()}:enable"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                return True, f"Audit policy set for {category}/{subcategory}"
            else:
                error = result.stderr.strip() or result.stdout.strip()
                return False, error
                
        except Exception:
            logging.exception("Failed to set audit policy")
            return False, "Failed to set audit policy"

