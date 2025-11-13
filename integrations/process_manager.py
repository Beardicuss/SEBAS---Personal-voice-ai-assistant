import logging
import platform
import subprocess
import psutil
import ctypes
from sebas.typing import Optional, Dict, List, Tuple
from sebas.enum import Enum

WINDOWS_AVAILABLE = platform.system() == "Windows"

# Windows-specific imports



class ProcessPriority(Enum):
    """Windows process priority classes"""
    IDLE = "idle"  # IDLE_PRIORITY_CLASS
    BELOW_NORMAL = "below_normal"  # BELOW_NORMAL_PRIORITY_CLASS
    NORMAL = "normal"  # NORMAL_PRIORITY_CLASS
    ABOVE_NORMAL = "above_normal"  # ABOVE_NORMAL_PRIORITY_CLASS
    HIGH = "high"  # HIGH_PRIORITY_CLASS
    REALTIME = "realtime"  # REALTIME_PRIORITY_CLASS


class ProcessManager:
    """
    Manages process priority and CPU affinity.
    """
    
    def __init__(self):
        """Initialize Process Manager."""
        if platform.system() != 'Windows' and not WINDOWS_AVAILABLE:
            logging.warning("Process priority management may be limited on non-Windows systems")
    
    def set_process_priority(self, process_id: int, priority: ProcessPriority) -> Tuple[bool, str]:
        """
        Set process priority.
        
        Args:
            process_id: Process ID
            priority: Priority level
            
        Returns:
            Tuple of (success, message)
        """
        try:
            process = psutil.Process(process_id)
            
            # Map enum to psutil priority constants
            priority_map = {
                ProcessPriority.IDLE: psutil.IDLE_PRIORITY_CLASS,
                ProcessPriority.BELOW_NORMAL: psutil.BELOW_NORMAL_PRIORITY_CLASS,
                ProcessPriority.NORMAL: psutil.NORMAL_PRIORITY_CLASS,
                ProcessPriority.ABOVE_NORMAL: psutil.ABOVE_NORMAL_PRIORITY_CLASS,
                ProcessPriority.HIGH: psutil.HIGH_PRIORITY_CLASS,
                ProcessPriority.REALTIME: psutil.REALTIME_PRIORITY_CLASS
            }
            
            psutil_priority = priority_map.get(priority, psutil.NORMAL_PRIORITY_CLASS)
            process.nice(psutil_priority)
            
            logging.info(f"Process {process_id} priority set to {priority.value}")
            return True, f"Priority set to {priority.value}"
            
        except psutil.NoSuchProcess:
            return False, f"Process {process_id} not found"
        except psutil.AccessDenied:
            return False, "Access denied. Administrator privileges required."
        except Exception:
            logging.exception(f"Failed to set priority for process {process_id}")
            return False, "Failed to set process priority"
    
    def get_process_priority(self, process_id: int) -> Optional[ProcessPriority]:
        """
        Get current process priority.
        
        Args:
            process_id: Process ID
            
        Returns:
            ProcessPriority enum or None
        """
        try:
            process = psutil.Process(process_id)
            nice = process.nice()
            
            # Map psutil priority to enum
            if nice == psutil.IDLE_PRIORITY_CLASS:
                return ProcessPriority.IDLE
            elif nice == psutil.BELOW_NORMAL_PRIORITY_CLASS:
                return ProcessPriority.BELOW_NORMAL
            elif nice == psutil.NORMAL_PRIORITY_CLASS:
                return ProcessPriority.NORMAL
            elif nice == psutil.ABOVE_NORMAL_PRIORITY_CLASS:
                return ProcessPriority.ABOVE_NORMAL
            elif nice == psutil.HIGH_PRIORITY_CLASS:
                return ProcessPriority.HIGH
            elif nice == psutil.REALTIME_PRIORITY_CLASS:
                return ProcessPriority.REALTIME
            else:
                return ProcessPriority.NORMAL
                
        except psutil.NoSuchProcess:
            return None
        except Exception:
            logging.exception(f"Failed to get priority for process {process_id}")
            return None
    
    def set_cpu_affinity(self, process_id: int, cpu_cores: List[int]) -> Tuple[bool, str]:
        """
        Set CPU affinity for a process.
        
        Args:
            process_id: Process ID
            cpu_cores: List of CPU core numbers (0-indexed) to allow
            
        Returns:
            Tuple of (success, message)
        """
        try:
            process = psutil.Process(process_id)
            
            # Validate CPU cores
            cpu_count = psutil.cpu_count()
            if cpu_count is None:
                return False, "Could not determine CPU count"
            if not all(0 <= core < cpu_count for core in cpu_cores):
                return False, f"Invalid CPU core numbers. System has {cpu_count} cores."
            
            # Set affinity
            process.cpu_affinity(cpu_cores)
            
            logging.info(f"Process {process_id} CPU affinity set to cores: {cpu_cores}")
            return True, f"CPU affinity set to cores: {cpu_cores}"
            
        except psutil.NoSuchProcess:
            return False, f"Process {process_id} not found"
        except psutil.AccessDenied:
            return False, "Access denied. Administrator privileges required."
        except Exception:
            logging.exception(f"Failed to set CPU affinity for process {process_id}")
            return False, "Failed to set CPU affinity"
    
    def get_cpu_affinity(self, process_id: int) -> Optional[List[int]]:
        """
        Get current CPU affinity for a process.
        
        Args:
            process_id: Process ID
            
        Returns:
            List of CPU core numbers or None
        """
        try:
            process = psutil.Process(process_id)
            return process.cpu_affinity()
            
        except psutil.NoSuchProcess:
            return None
        except Exception:
            logging.exception(f"Failed to get CPU affinity for process {process_id}")
            return None
    
    def get_process_info(self, process_id: int) -> Optional[Dict]:
        """
        Get detailed process information.
        
        Args:
            process_id: Process ID
            
        Returns:
            Dict with process information or None
        """
        try:
            process = psutil.Process(process_id)
            
            info = {
                'pid': process.pid,
                'name': process.name(),
                'status': process.status(),
                'cpu_percent': process.cpu_percent(interval=0.1),
                'memory_info': {
                    'rss': process.memory_info().rss,
                    'vms': process.memory_info().vms,
                    'percent': process.memory_percent()
                },
                'num_threads': process.num_threads(),
                'priority': self.get_process_priority(process_id),
                'cpu_affinity': self.get_cpu_affinity(process_id),
                'create_time': process.create_time(),
                'cmdline': process.cmdline()
            }
            
            return info
            
        except psutil.NoSuchProcess:
            return None
        except Exception:
            logging.exception(f"Failed to get info for process {process_id}")
            return None