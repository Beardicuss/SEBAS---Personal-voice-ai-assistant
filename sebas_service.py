# -*- coding: utf-8 -*-
"""
SEBAS Windows Service for Privileged Operations.

This service runs in the background with SYSTEM privileges to execute
tasks that require elevation. It listens on a local socket for commands
from the main SEBAS application.

To install/manage the service from an ADMINISTRATOR command prompt:
> python sebas_service.py install
> python sebas_service.py start
> python sebas_service.py stop
> python sebas_service.py remove

The service logs to D:\\sebas_service.log
"""
import socket
import json
import logging
import subprocess
import threading
import os
import shutil
import ctypes
import winreg
import psutil
import win32evtlog  # For audit events
import win32evtlogutil  # For formatting event messages
import win32serviceutil
import win32service
import win32event
import servicemanager
from datetime import datetime
from typing import Dict, Any  # Added to resolve undefined type hints

HOST = '127.0.0.1'
PORT = 5001  # Port for the service to listen on

import logging.handlers
SERVICE_LOG_PATH = os.environ.get('SEBAS_SERVICE_LOG', r'D:\\sebas_service.log')
try:
    _svc_max_mb = int(float(os.environ.get('SEBAS_SERVICE_LOG_MAX_MB', '10')))
    _svc_backups = int(os.environ.get('SEBAS_SERVICE_LOG_BACKUPS', '5'))
except Exception:
    _svc_max_mb = 10
    _svc_backups = 5

_root = logging.getLogger()
try:
    _svc_level = os.environ.get('SEBAS_SERVICE_LOG_LEVEL', 'INFO').upper()
    _level = getattr(logging, _svc_level, logging.INFO)
except Exception:
    _level = logging.INFO
_root.setLevel(_level)
_root.handlers.clear()
_h = logging.handlers.RotatingFileHandler(
    SERVICE_LOG_PATH,
    maxBytes=_svc_max_mb * 1024 * 1024,
    backupCount=_svc_backups,
    encoding='utf-8'
)
_fmt = logging.Formatter('%(asctime)s %(levelname)-8s %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
_h.setFormatter(_fmt)
_root.addHandler(_h)


class SebasService(win32serviceutil.ServiceFramework):
    _svc_name_ = "SebasPrivilegedService"
    _svc_display_name_ = "SEBAS Privileged Operations Service"
    _svc_description_ = "Handles background system administration tasks for the SEBAS assistant."

    def __init__(self, args):
        win32serviceutil.ServiceFramework.__init__(self, args)
        self.hWaitStop = win32event.CreateEvent(None, 0, 0, None)
        try:
            _sock_timeout = float(os.environ.get('SEBAS_SERVICE_SOCKET_TIMEOUT', '60'))
        except Exception:
            _sock_timeout = 60.0
        socket.setdefaulttimeout(_sock_timeout)
        self.stop_requested = False
        self.server_socket = None

    def SvcStop(self):
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        win32event.SetEvent(self.hWaitStop)
        self.stop_requested = True
        # Close the socket to unblock the accept() call
        if self.server_socket:
            self.server_socket.close()

    def SvcDoRun(self):
        servicemanager.LogMsg(servicemanager.EVENTLOG_INFORMATION_TYPE,
                              servicemanager.PYS_SERVICE_STARTED,
                              (self._svc_name_, ''))
        self.main()

    def main(self):
        logging.info("Service starting...")
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            self.server_socket.bind((HOST, PORT))
            self.server_socket.listen(1)
            logging.info(f"Listening on {HOST}:{PORT}")

            while not self.stop_requested:
                try:
                    conn, addr = self.server_socket.accept()
                    with conn:
                        logging.info(f"Connected by {addr}")
                        data = conn.recv(4096)
                        if not data:
                            continue
                        response = self.handle_request(data)
                        conn.sendall(response.encode('utf-8'))
                except socket.error as e:
                    if self.stop_requested:
                        logging.info("Socket closed for service stop.")
                        break
                    logging.error(f"Socket error: {e}")
                    # Avoid busy-looping on repeated errors
                    threading.Event().wait(5)
                except Exception as e:
                    logging.error(f"Error in connection loop: {e}", exc_info=True)

        except Exception as e:
            logging.error(f"Service main loop failed: {e}", exc_info=True)
        finally:
            if self.server_socket:
                self.server_socket.close()
            logging.info("Service stopped.")

    def handle_request(self, data):
        try:
            request = json.loads(data.decode('utf-8'))
            command = request.get('command')
            params = request.get('params', {})
            logging.info(f"Received command: {command} with params: {params}")

            # --- Command Dispatcher ---
            # Only explicitly allowed commands can be run.
            if command == 'shutdown':
                subprocess.run(["shutdown", "/s", "/t", str(params.get('delay', 1))], check=False)
                result = {"status": "ok", "message": "Shutdown initiated."}
            elif command == 'restart':
                subprocess.run(["shutdown", "/r", "/t", str(params.get('delay', 1))], check=False)
                result = {"status": "ok", "message": "Restart initiated."}
            elif command == 'run_shell':
                shell_cmd = params.get('cmd')
                # IMPORTANT: Add validation here for safety
                if not self._is_safe_shell_command(shell_cmd):
                    raise ValueError("Disallowed shell command")
                output = subprocess.run(shell_cmd, shell=True, capture_output=True, text=True, timeout=30)
                result = {"status": "ok", "stdout": output.stdout, "stderr": output.stderr}
            elif command == 'delete_path':
                path = params.get('path')
                if os.path.isdir(path):
                    shutil.rmtree(path)
                elif os.path.isfile(path):
                    os.remove(path)
                result = {"status": "ok", "message": f"Path '{path}' deleted."}
            elif command == 'lock_workstation':
                ctypes.windll.user32.LockWorkStation()
                result = {"status": "ok", "message": "Workstation locked."}
            elif command == 'clean_temp_files':
                deleted_files, deleted_bytes = self._clean_temp_folders()
                result = {
                    "status": "ok",
                    "message": f"Deleted {deleted_files} files, freeing {deleted_bytes / (1024*1024):.2f} MB."
                }
            elif command == 'get_startup_items':
                items = self._get_startup_items()
                result = {"status": "ok", "items": items}
            elif command == 'disable_startup_item':
                item = params.get('item')
                if not item: raise ValueError("No startup item provided")
                self._disable_startup_item(item)
                result = {"status": "ok", "message": f"Disabled startup item {item.get('name')}"}
            elif command == 'get_audit_events':
                result = self._get_audit_events(params)
            elif command == 'verify_security_policy':
                result = self._verify_security_policy()
            # Add other privileged commands here...
            else:
                result = {"status": "error", "message": "Unknown command"}

        except Exception as e:
            logging.error(f"Error handling request: {e}", exc_info=True)
            result = {"status": "error", "message": str(e)}

        return json.dumps(result)

    def _get_audit_events(self, params: Dict[str, Any]) -> Dict[str, Any]:
        try:
            hand = win32evtlog.OpenEventLog(None, 'Security')
            flags = win32evtlog.EVENTLOG_BACKWARDS_READ | win32evtlog.EVENTLOG_SEQUENTIAL_READ
            events = []
            offset = 0
            limit = params.get('limit', 50)
            start_date_str = params.get('start_date')
            start_date = datetime.fromisoformat(start_date_str) if start_date_str else None
            event_type = params.get('event_type')  # String for EventID match
            category = params.get('category')  # Filter on EventCategory
            severity = params.get('severity')  # Not directly supported; approximate with EventType

            total_read = 0
            while True:
                evts = win32evtlog.ReadEventLog(hand, flags, offset, 1024 * 64)  # Buffer size
                if not evts:
                    break
                for evt in evts:
                    total_read += 1
                    # Explicit format string added to satisfy Pylance (matches expected output for strptime)
                    time_str = evt.TimeGenerated.Format('%m/%d/%y %H:%M:%S')
                    evt_time = datetime.strptime(time_str, '%m/%d/%y %H:%M:%S')
                    if start_date and evt_time < start_date:
                        continue
                    if event_type and str(evt.EventID) != event_type:
                        continue
                    if category and str(evt.EventCategory) != category:
                        continue
                    # Severity approximation (EventType: 1=Error, 2=Warning, 4=Info, 8=Success Audit, 16=Failure Audit)
                    if severity:
                        evt_type_map = {1: 'error', 2: 'warning', 4: 'info', 8: 'success', 16: 'failure'}
                        if evt_type_map.get(evt.EventType, 'unknown') != severity.lower():
                            continue

                    event_dict = {
                        'EventID': evt.EventID,
                        'TimeGenerated': evt_time.isoformat(),
                        'SourceName': evt.SourceName,
                        'EventCategory': evt.EventCategory,
                        'StringInserts': list(evt.StringInserts) if evt.StringInserts else [],
                        'Message': win32evtlogutil.SafeFormatMessage(evt, 'Security')
                    }
                    events.append(event_dict)
                    if len(events) >= limit:
                        break
                if len(events) >= limit:
                    break
                offset = total_read
            win32evtlog.CloseEventLog(hand)
            return {"status": "ok", "events": events}
        except Exception as e:
            logging.error(f"Failed to get audit events: {e}", exc_info=True)
            return {"status": "error", "message": str(e)}

    def _verify_security_policy(self) -> Dict[str, Any]:
        try:
            results = {
                'compliance_status': 'Compliant',
                'passed': 0,
                'failed': 0,
                'warnings': 0,
                'details': []
            }
            # Example checks (expand as per roadmap; reuse from prior phases)
            checks = [
                ('UAC enabled', self._check_uac_enabled()),
                ('Admin approval mode', self._check_admin_approval_mode()),
                ('Credential Guard enabled', self._check_credential_guard()),
                ('Firewall enabled', self._check_firewall_enabled()),
                ('Secure Boot enabled', self._check_secure_boot())
            ]
            for name, passed in checks:
                if passed:
                    results['passed'] += 1
                else:
                    results['failed'] += 1
                    results['compliance_status'] = 'Non-Compliant'
                results['details'].append({'name': name, 'passed': passed})
            return {"status": "ok", "results": results}
        except Exception as e:
            logging.error(f"Failed to verify security policy: {e}", exc_info=True)
            return {"status": "error", "message": str(e)}

    # Helper methods for policy checks (implement as needed; placeholders from prior)
    def _check_uac_enabled(self):
        try:
            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\System")
            value, _ = winreg.QueryValueEx(key, "EnableLUA")
            winreg.CloseKey(key)
            return value == 1
        except:
            return False

    def _check_admin_approval_mode(self):
        try:
            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\System")
            value, _ = winreg.QueryValueEx(key, "FilterAdministratorToken")
            winreg.CloseKey(key)
            return value == 1
        except:
            return False

    def _check_credential_guard(self):
        try:
            output = subprocess.run(["powershell", "-Command", "Get-ItemProperty -Path 'HKLM:\\SYSTEM\\CurrentControlSet\\Control\\LSA' -Name 'LsaCfgFlags'"], capture_output=True, text=True)
            return 'LsaCfgFlags : 1' in output.stdout or 'LsaCfgFlags : 2' in output.stdout
        except:
            return False

    def _check_firewall_enabled(self):
        try:
            output = subprocess.run(["powershell", "-Command", "Get-NetFirewallProfile | Select Name, Enabled"], capture_output=True, text=True)
            return all('Enabled : True' in line for line in output.stdout.splitlines() if 'Enabled' in line)
        except:
            return False

    def _check_secure_boot(self):
        try:
            output = subprocess.run(["powershell", "-Command", "Confirm-SecureBootUEFI"], capture_output=True, text=True)
            return 'True' in output.stdout
        except:
            return False

    def _clean_temp_folders(self):
        """Deletes files from common temporary folders."""
        folders = [
            os.environ.get('TEMP'),
            os.environ.get('TMP'),
            'C:\\Windows\\Temp'
        ]
        # Use a set to handle unique folders if TEMP and TMP are the same
        unique_folders = {f for f in folders if f and os.path.isdir(f)}
        
        deleted_files_count = 0
        deleted_bytes_count = 0

        for folder in unique_folders:
            logging.info(f"Cleaning folder: {folder}")
            for root, dirs, files in os.walk(folder):
                for name in files + dirs:
                    path = os.path.join(root, name)
                    try:
                        if os.path.isfile(path) or os.path.islink(path):
                            file_size = os.path.getsize(path)
                            os.unlink(path)
                            deleted_files_count += 1
                            deleted_bytes_count += file_size
                        elif os.path.isdir(path):
                            # Only remove empty subdirectories for safety
                            if not os.listdir(path):
                                shutil.rmtree(path)
                    except Exception as e:
                        logging.warning(f"Could not delete {path}: {e}")
        return deleted_files_count, deleted_bytes_count

    def _get_startup_items(self):
        """Gathers startup items from registry and startup folders."""
        items = []
        
        # Registry Run keys
        reg_paths = [
            (winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run"),
            (winreg.HKEY_LOCAL_MACHINE, r"Software\Microsoft\Windows\CurrentVersion\Run"),
            (winreg.HKEY_LOCAL_MACHINE, r"Software\WOW6432Node\Microsoft\Windows\CurrentVersion\Run"),
        ]
        for hive, path in reg_paths:
            try:
                with winreg.OpenKey(hive, path) as key:
                    i = 0
                    while True:
                        try:
                            name, value, _ = winreg.EnumValue(key, i)
                            items.append({"name": name, "command": value, "location": "registry", "source": f"{hive}\\{path}"})
                            i += 1
                        except OSError:
                            break
            except FileNotFoundError:
                continue
            except Exception as e:
                logging.error(f"Failed to read registry startup items from {path}: {e}")

        # Startup folders
        startup_folders = [
            os.path.join(os.environ['APPDATA'], r'Microsoft\Windows\Start Menu\Programs\Startup'),
            os.path.join(os.environ['ProgramData'], r'Microsoft\Windows\Start Menu\Programs\Startup')
        ]
        for folder in startup_folders:
            if not os.path.isdir(folder): continue
            for filename in os.listdir(folder):
                full_path = os.path.join(folder, filename)
                if os.path.isfile(full_path):
                    items.append({"name": os.path.splitext(filename)[0], "command": full_path, "location": "folder", "source": full_path})

        return items

    def _disable_startup_item(self, item: dict):
        """Disables a startup item by deleting registry key or moving file."""
        location = item.get('location')
        name = item.get('name')
        source = item.get('source')

        if not name:
            raise ValueError("No name provided for startup item")

        if location == 'registry':
            if not source:
                raise ValueError("No source provided for registry startup item")
            hive_str, path = source.split('\\', 1)
            hive_map = {str(winreg.HKEY_CURRENT_USER): winreg.HKEY_CURRENT_USER, str(winreg.HKEY_LOCAL_MACHINE): winreg.HKEY_LOCAL_MACHINE}
            hive = hive_map.get(hive_str)
            if not hive: raise ValueError("Invalid registry hive in source")
            
            logging.info(f"Disabling registry startup item: {name} from {source}")
            with winreg.OpenKey(hive, path, 0, winreg.KEY_SET_VALUE) as key:
                winreg.DeleteValue(key, name)
        
        elif location == 'folder':
            if not source:
                raise ValueError("No source provided for folder startup item")
            logging.info(f"Disabling folder startup item: {name} from {source}")
            disabled_folder = os.path.join(os.path.dirname(source), "Startup (Disabled)")
            os.makedirs(disabled_folder, exist_ok=True)
            shutil.move(source, os.path.join(disabled_folder, os.path.basename(source)))

    def _is_safe_shell_command(self, cmd: str) -> bool:
        """A basic safety check for shell commands."""
        if not cmd:
            return False
        
        cmd_lower = cmd.lower().strip()
        
        # Deny list for extremely dangerous commands and patterns
        deny_list = [
            "format", "diskpart", "fdisk", "bcdedit", "cipher /w",
            "del ", "rd ", "rmdir ",
            "powershell remove-item",
            "reg delete",
        ]
        if any(denied in cmd_lower for denied in deny_list):
            logging.warning(f"Blocked dangerous shell command: {cmd}")
            return False
        return True


if __name__ == '__main__':
    win32serviceutil.HandleCommandLine(SebasService)