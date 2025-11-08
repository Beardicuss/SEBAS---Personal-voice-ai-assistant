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

The service logs to D:\sebas_service.log
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

import win32serviceutil
import win32service
import win32event
import servicemanager

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
            # Add other privileged commands here...
            else:
                result = {"status": "error", "message": "Unknown command"}

        except Exception as e:
            logging.error(f"Error handling request: {e}", exc_info=True)
            result = {"status": "error", "message": str(e)}

        return json.dumps(result)

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

        if location == 'registry':
            hive_str, path = source.split('\\', 1)
            hive_map = {str(winreg.HKEY_CURRENT_USER): winreg.HKEY_CURRENT_USER, str(winreg.HKEY_LOCAL_MACHINE): winreg.HKEY_LOCAL_MACHINE}
            hive = hive_map.get(hive_str)
            if not hive: raise ValueError("Invalid registry hive in source")
            
            logging.info(f"Disabling registry startup item: {name} from {source}")
            with winreg.OpenKey(hive, path, 0, winreg.KEY_SET_VALUE) as key:
                winreg.DeleteValue(key, name)
        
        elif location == 'folder':
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