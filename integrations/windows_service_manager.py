# -*- coding: utf-8 -*-
"""
Windows Service Management
Phase 2.1: Service & Process Control
"""

import logging
import subprocess
import platform
from typing import Optional, Dict, List, Tuple
from enum import Enum


class ServiceState(Enum):
    """Windows service states"""
    STOPPED = "stopped"
    START_PENDING = "start_pending"
    STOP_PENDING = "stop_pending"
    RUNNING = "running"
    CONTINUE_PENDING = "continue_pending"
    PAUSE_PENDING = "pause_pending"
    PAUSED = "paused"
    UNKNOWN = "unknown"


class ServiceStartType(Enum):
    """Service start types"""
    BOOT = "boot"
    SYSTEM = "system"
    AUTO = "auto"
    DEMAND = "demand"
    DISABLED = "disabled"


class WindowsServiceManager:
    """
    Manages Windows Services (start, stop, restart, configure, query).
    """
    
    def __init__(self):
        """Initialize Windows Service Manager."""
        if platform.system() != 'Windows':
            raise RuntimeError("WindowsServiceManager only works on Windows")
        
        self.sc_command = "sc.exe"
    
    def get_service_status(self, service_name: str) -> Optional[Dict[str, str]]:
        """
        Get service status information.
        
        Args:
            service_name: Name of the service
            
        Returns:
            Dict with service information or None
        """
        try:
            result = subprocess.run(
                [self.sc_command, "query", service_name],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode != 0:
                logging.warning(f"Service {service_name} not found or error: {result.stderr}")
                return None
            
            # Parse output
            lines = result.stdout.strip().split('\n')
            info = {}
            
            for line in lines:
                line = line.strip()
                if ':' in line:
                    key, value = line.split(':', 1)
                    key = key.strip()
                    value = value.strip()
                    info[key.lower().replace(' ', '_')] = value
            
            return info
            
        except Exception:
            logging.exception(f"Failed to get status for service: {service_name}")
            return None
    
    def start_service(self, service_name: str, timeout: int = 30) -> Tuple[bool, str]:
        """
        Start a Windows service.
        
        Args:
            service_name: Name of the service
            timeout: Timeout in seconds
            
        Returns:
            Tuple of (success, message)
        """
        try:
            result = subprocess.run(
                [self.sc_command, "start", service_name],
                capture_output=True,
                text=True,
                timeout=timeout
            )
            
            if result.returncode == 0:
                logging.info(f"Service {service_name} started successfully")
                return True, f"Service {service_name} started"
            else:
                error_msg = result.stderr.strip() or result.stdout.strip()
                logging.warning(f"Failed to start service {service_name}: {error_msg}")
                return False, error_msg
                
        except subprocess.TimeoutExpired:
            logging.error(f"Timeout starting service {service_name}")
            return False, "Timeout starting service"
        except Exception:
            logging.exception(f"Failed to start service: {service_name}")
            return False, "Failed to start service"
    
    def stop_service(self, service_name: str, timeout: int = 30) -> Tuple[bool, str]:
        """
        Stop a Windows service.
        
        Args:
            service_name: Name of the service
            timeout: Timeout in seconds
            
        Returns:
            Tuple of (success, message)
        """
        try:
            result = subprocess.run(
                [self.sc_command, "stop", service_name],
                capture_output=True,
                text=True,
                timeout=timeout
            )
            
            if result.returncode == 0:
                logging.info(f"Service {service_name} stopped successfully")
                return True, f"Service {service_name} stopped"
            else:
                error_msg = result.stderr.strip() or result.stdout.strip()
                logging.warning(f"Failed to stop service {service_name}: {error_msg}")
                return False, error_msg
                
        except subprocess.TimeoutExpired:
            logging.error(f"Timeout stopping service {service_name}")
            return False, "Timeout stopping service"
        except Exception:
            logging.exception(f"Failed to stop service: {service_name}")
            return False, "Failed to stop service"
    
    def restart_service(self, service_name: str, timeout: int = 60) -> Tuple[bool, str]:
        """
        Restart a Windows service.
        
        Args:
            service_name: Name of the service
            timeout: Total timeout in seconds
            
        Returns:
            Tuple of (success, message)
        """
        try:
            # Stop first
            success, msg = self.stop_service(service_name, timeout // 2)
            if not success:
                return False, f"Failed to stop service: {msg}"
            
            # Wait a bit
            import time
            time.sleep(2)
            
            # Start
            success, msg = self.start_service(service_name, timeout // 2)
            if not success:
                return False, f"Failed to start service: {msg}"
            
            logging.info(f"Service {service_name} restarted successfully")
            return True, f"Service {service_name} restarted"
            
        except Exception:
            logging.exception(f"Failed to restart service: {service_name}")
            return False, "Failed to restart service"
    
    def set_service_start_type(self, service_name: str, start_type: ServiceStartType) -> Tuple[bool, str]:
        """
        Set service start type.
        
        Args:
            service_name: Name of the service
            start_type: Start type to set
            
        Returns:
            Tuple of (success, message)
        """
        try:
            # Map enum to sc.exe values
            start_type_map = {
                ServiceStartType.BOOT: "boot",
                ServiceStartType.SYSTEM: "system",
                ServiceStartType.AUTO: "auto",
                ServiceStartType.DEMAND: "demand",
                ServiceStartType.DISABLED: "disabled"
            }
            
            sc_start_type = start_type_map.get(start_type, "demand")
            
            result = subprocess.run(
                [self.sc_command, "config", service_name, "start=", sc_start_type],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                logging.info(f"Service {service_name} start type set to {start_type.value}")
                return True, f"Start type set to {start_type.value}"
            else:
                error_msg = result.stderr.strip() or result.stdout.strip()
                return False, error_msg
                
        except Exception:
            logging.exception(f"Failed to set start type for service: {service_name}")
            return False, "Failed to set start type"
    
    def get_service_dependencies(self, service_name: str) -> List[str]:
        """
        Get list of services that this service depends on.
        
        Args:
            service_name: Name of the service
            
        Returns:
            List of dependent service names
        """
        try:
            result = subprocess.run(
                [self.sc_command, "qc", service_name],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode != 0:
                return []
            
            dependencies = []
            in_dependencies = False
            
            for line in result.stdout.split('\n'):
                line = line.strip()
                if 'DEPENDENCIES' in line.upper():
                    in_dependencies = True
                    continue
                
                if in_dependencies:
                    if line and not line.startswith('SERVICE_NAME'):
                        # Extract service name
                        dep_service = line.split(':')[-1].strip()
                        if dep_service:
                            dependencies.append(dep_service)
                    elif line.startswith('SERVICE_NAME'):
                        break
            
            return dependencies
            
        except Exception:
            logging.exception(f"Failed to get dependencies for service: {service_name}")
            return []
    
    def list_services(self, state_filter: Optional[ServiceState] = None) -> List[Dict[str, str]]:
        """
        List all Windows services.
        
        Args:
            state_filter: Optional filter by service state
            
        Returns:
            List of service information dicts
        """
        try:
            result = subprocess.run(
                [self.sc_command, "query", "state=", "all"],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode != 0:
                logging.warning("Failed to list services")
                return []
            
            services = []
            current_service = {}
            
            for line in result.stdout.split('\n'):
                line = line.strip()
                if not line:
                    if current_service:
                        if state_filter is None or current_service.get('state', '').lower() == state_filter.value:
                            services.append(current_service)
                        current_service = {}
                    continue
                
                if 'SERVICE_NAME' in line:
                    if current_service:
                        if state_filter is None or current_service.get('state', '').lower() == state_filter.value:
                            services.append(current_service)
                    current_service = {'name': line.split(':', 1)[1].strip()}
                elif ':' in line:
                    key, value = line.split(':', 1)
                    key = key.strip().lower().replace(' ', '_')
                    value = value.strip()
                    if current_service:
                        current_service[key] = value
            
            # Add last service
            if current_service:
                if state_filter is None or current_service.get('state', '').lower() == state_filter.value:
                    services.append(current_service)
            
            return services
            
        except Exception:
            logging.exception("Failed to list services")
            return []
    
    def configure_service_recovery(self, service_name: str, 
                                   first_failure: str = "restart",
                                   second_failure: str = "restart",
                                   subsequent_failures: str = "restart",
                                   reset_period: int = 86400) -> Tuple[bool, str]:
        """
        Configure service recovery options.
        
        Args:
            service_name: Name of the service
            first_failure: Action for first failure (take_no_action, restart, run_command, reboot)
            second_failure: Action for second failure
            subsequent_failures: Action for subsequent failures
            reset_period: Reset period in seconds (default 24 hours)
            
        Returns:
            Tuple of (success, message)
        """
        try:
            # Use sc.exe failure command
            # Format: sc failure <service> reset= <period> actions= <action>/<delay> <action>/<delay> <action>/<delay>
            
            actions = f"{first_failure}/0 {second_failure}/0 {subsequent_failures}/0"
            
            result = subprocess.run(
                [self.sc_command, "failure", service_name, f"reset={reset_period}", f"actions={actions}"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                logging.info(f"Service {service_name} recovery configured")
                return True, "Recovery options configured"
            else:
                error_msg = result.stderr.strip() or result.stdout.strip()
                return False, error_msg
                
        except Exception:
            logging.exception(f"Failed to configure recovery for service: {service_name}")
            return False, "Failed to configure recovery"

