"""
Storage Management Skill
Phase 3.2: Storage administration
"""

from sebas.skills.base_skill import BaseSkill
from sebas.typing import Dict, Any
import logging
from sebas.integrations.storage_manager import StorageManager

class StorageSkill(BaseSkill):
    """
    Skill for managing storage operations.
    """
    
    def __init__(self, assistant):
        super().__init__(assistant)
        self.intents = [
            'list_disk_partitions',
            'get_disk_info',
            'get_volume_info',
            'get_storage_spaces_status',
            'get_bitlocker_status',
            'enable_bitlocker',
            'disable_bitlocker',
            'get_disk_usage'
        ]
        self.storage_manager = None
        self._init_storage_manager()
    
    def _init_storage_manager(self):
        """Initialize storage manager."""
        try:
            from sebas.integrations.storage_manager import StorageManager
            self.storage_manager = StorageManager()
        except Exception:
            logging.exception("Failed to initialize storage manager")
            self.storage_manager = None
    
    def can_handle(self, intent: str) -> bool:
        return intent in self.get_intents()
    
    def get_intents(self) -> list:
        return self.intents
    
    def handle(self, intent: str, slots: dict) -> bool:
        if not self.storage_manager:
            self.assistant.speak("Storage management is not available")
            return False
        
        if intent == 'list_disk_partitions':
            return self._handle_list_disk_partitions()
        elif intent == 'get_disk_info':
            return self._handle_get_disk_info()
        elif intent == 'get_volume_info':
            return self._handle_get_volume_info()
        elif intent == 'get_storage_spaces_status':
            return self._handle_get_storage_spaces_status()
        elif intent == 'get_bitlocker_status':
            return self._handle_get_bitlocker_status(slots)
        elif intent == 'enable_bitlocker':
            return self._handle_enable_bitlocker(slots)
        elif intent == 'disable_bitlocker':
            return self._handle_disable_bitlocker(slots)
        elif intent == 'get_disk_usage':
            return self._handle_get_disk_usage(slots)
        return False
    
    def _handle_list_disk_partitions(self) -> bool:
        """Handle list disk partitions command."""
        if self.storage_manager is None:
            self.assistant.speak("Storage manager not available")
            return False
        try:
            partitions = self.storage_manager.list_disk_partitions()
            
            if partitions:
                count = len(partitions)
                self.assistant.speak(f"Found {count} disk partitions")
            else:
                self.assistant.speak("No partitions found")
            
            return True
            
        except Exception:
            logging.exception("Failed to list disk partitions")
            self.assistant.speak("Failed to list disk partitions")
            return False
    
    def _handle_get_disk_info(self) -> bool:
        """Handle get disk info command."""
        if self.storage_manager is None:
            self.assistant.speak("Storage manager not available")
            return False
        try:
            disks = self.storage_manager.get_disk_info()
            
            if disks:
                count = len(disks)
                self.assistant.speak(f"Found {count} disk drives")
            else:
                self.assistant.speak("No disk information available")
            
            return True
            
        except Exception:
            logging.exception("Failed to get disk info")
            self.assistant.speak("Failed to get disk information")
            return False
    
    def _handle_get_volume_info(self) -> bool:
        """Handle get volume info command."""
        if self.storage_manager is None:
            self.assistant.speak("Storage manager not available")
            return False
        try:
            volumes = self.storage_manager.get_volume_info()
            
            if volumes:
                volume_list = []
                for vol in volumes[:5]:  # Limit to first 5
                    device_id = vol.get('deviceid', 'Unknown')
                    size = vol.get('size', 'Unknown')
                    free_space = vol.get('freespace', 'Unknown')
                    volume_list.append(f"{device_id}: {free_space} free of {size}")
                
                self.assistant.speak(f"Volumes: {', '.join(volume_list)}")
            else:
                self.assistant.speak("No volume information available")
            
            return True
            
        except Exception:
            logging.exception("Failed to get volume info")
            self.assistant.speak("Failed to get volume information")
            return False
    
    def _handle_get_storage_spaces_status(self) -> bool:
        """Handle get Storage Spaces status command."""
        if self.storage_manager is None:
            self.assistant.speak("Storage manager not available")
            return False
        try:
            pools = self.storage_manager.get_storage_spaces_status()
            
            if pools:
                count = len(pools)
                self.assistant.speak(f"Found {count} Storage Spaces pools")
            else:
                self.assistant.speak("No Storage Spaces pools found")
            
            return True
            
        except Exception:
            logging.exception("Failed to get Storage Spaces status")
            self.assistant.speak("Failed to get Storage Spaces status")
            return False
    
    def _handle_get_bitlocker_status(self, slots: dict) -> bool:
        """Handle get BitLocker status command."""
        if self.storage_manager is None:
            self.assistant.speak("Storage manager not available")
            return False
        try:
            drive_letter = slots.get('drive_letter')
            status_list = self.storage_manager.get_bitlocker_status(drive_letter)
            
            if status_list:
                for status in status_list:
                    volume = status.get('volume', 'Unknown')
                    protection_status = status.get('protection_status', 'Unknown')
                    self.assistant.speak(f"Drive {volume}: BitLocker status {protection_status}")
            else:
                self.assistant.speak("No BitLocker information available")
            
            return True
            
        except Exception:
            logging.exception("Failed to get BitLocker status")
            self.assistant.speak("Failed to get BitLocker status")
            return False
    
    def _handle_enable_bitlocker(self, slots: dict) -> bool:
        """Handle enable BitLocker command."""
        if self.storage_manager is None:
            self.assistant.speak("Storage manager not available")
            return False
        if not self.assistant.has_permission('enable_bitlocker'):
            return False
        
        try:
            drive_letter = slots.get('drive_letter', 'C:')
            
            if not self.assistant.confirm_action(f"Enable BitLocker encryption on drive {drive_letter}? This may take a long time."):
                return False
            
            success, message = self.storage_manager.enable_bitlocker(drive_letter)
            
            if success:
                self.assistant.speak(message)
            else:
                self.assistant.speak(f"Failed to enable BitLocker: {message}")
            
            return success
            
        except Exception:
            logging.exception("Failed to enable BitLocker")
            self.assistant.speak("Failed to enable BitLocker")
            return False
    
    def _handle_disable_bitlocker(self, slots: dict) -> bool:
        """Handle disable BitLocker command."""
        if self.storage_manager is None:
            self.assistant.speak("Storage manager not available")
            return False
        if not self.assistant.has_permission('disable_bitlocker'):
            return False
        
        try:
            drive_letter = slots.get('drive_letter', 'C:')
            
            if not self.assistant.confirm_action(f"Disable BitLocker encryption on drive {drive_letter}? This may take a long time."):
                return False
            
            success, message = self.storage_manager.disable_bitlocker(drive_letter)
            
            if success:
                self.assistant.speak(message)
            else:
                self.assistant.speak(f"Failed to disable BitLocker: {message}")
            
            return success
            
        except Exception:
            logging.exception("Failed to disable BitLocker")
            self.assistant.speak("Failed to disable BitLocker")
            return False
    
    def _handle_get_disk_usage(self, slots: dict) -> bool:
        """Handle get disk usage command."""
        if self.storage_manager is None:
            self.assistant.speak("Storage manager not available")
            return False
        try:
            path = slots.get('path')
            usage = self.storage_manager.get_disk_usage(path)
            
            if usage:
                if isinstance(usage, dict) and 'path' in usage:
                    # Single path
                    total_gb = usage['total'] / (1024**3)
                    used_gb = usage['used'] / (1024**3)
                    free_gb = usage['free'] / (1024**3)
                    percent = usage['percent']
                    self.assistant.speak(
                        f"Disk usage for {usage['path']}: {used_gb:.1f} GB used of {total_gb:.1f} GB "
                        f"({percent:.1f}%), {free_gb:.1f} GB free"
                    )
                else:
                    # Multiple drives
                    count = len(usage)
                    self.assistant.speak(f"Found {count} disk drives")
            else:
                self.assistant.speak("No disk usage information available")
            
            return True
            
        except Exception:
            logging.exception("Failed to get disk usage")
            self.assistant.speak("Failed to get disk usage")
            return False