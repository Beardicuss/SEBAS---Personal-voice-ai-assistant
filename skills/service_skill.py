# -*- coding: utf-8 -*-
"""
Windows Service Management Skill
Phase 2.1: Service control and management
"""

from skills.base_skill import BaseSkill
from typing import Dict, Any
import logging


class ServiceSkill(BaseSkill):
    """
    Skill for managing Windows services.
    """
    
    def __init__(self, assistant):
        super().__init__(assistant)
        self.intents = [
            'start_service',
            'stop_service',
            'restart_service',
            'get_service_status',
            'list_services',
            'set_service_start_type',
            'get_service_dependencies',
            'configure_service_recovery'
        ]
        self.service_manager = None
        self._init_service_manager()
    
    def _init_service_manager(self):
        """Initialize service manager."""
        try:
            from integrations.windows_service_manager import WindowsServiceManager
            self.service_manager = WindowsServiceManager()
        except Exception:
            logging.exception("Failed to initialize service manager")
            self.service_manager = None
    
    def can_handle(self, intent: str) -> bool:
        return intent in self.get_intents()
    
    def get_intents(self) -> list:
        return self.intents
    
    def handle(self, intent: str, slots: dict) -> bool:
        if not self.service_manager:
            self.assistant.speak("Service management is not available")
            return False
        
        if intent == 'start_service':
            return self._handle_start_service(slots)
        elif intent == 'stop_service':
            return self._handle_stop_service(slots)
        elif intent == 'restart_service':
            return self._handle_restart_service(slots)
        elif intent == 'get_service_status':
            return self._handle_get_service_status(slots)
        elif intent == 'list_services':
            return self._handle_list_services(slots)
        elif intent == 'set_service_start_type':
            return self._handle_set_service_start_type(slots)
        elif intent == 'get_service_dependencies':
            return self._handle_get_service_dependencies(slots)
        elif intent == 'configure_service_recovery':
            return self._handle_configure_service_recovery(slots)
        return False
    
    def _handle_start_service(self, slots: dict) -> bool:
        """Handle start service command."""
        if self.service_manager is None:
            self.assistant.speak("Service manager not available")
            return False
        if not self.assistant.has_permission('start_service'):
            return False
        
        try:
            service_name = slots.get('service_name')
            if not service_name:
                self.assistant.speak("Please specify a service name")
                return False
            
            success, message = self.service_manager.start_service(service_name)
            
            if success:
                self.assistant.speak(f"Service {service_name} started successfully")
            else:
                self.assistant.speak(f"Failed to start service: {message}")
            
            return success
            
        except Exception:
            logging.exception("Failed to start service")
            self.assistant.speak("Failed to start service")
            return False
    
    def _handle_stop_service(self, slots: dict) -> bool:
        """Handle stop service command."""
        if self.service_manager is None:
            self.assistant.speak("Service manager not available")
            return False
        if not self.assistant.has_permission('stop_service'):
            return False
        
        try:
            service_name = slots.get('service_name')
            if not service_name:
                self.assistant.speak("Please specify a service name")
                return False
            
            success, message = self.service_manager.stop_service(service_name)
            
            if success:
                self.assistant.speak(f"Service {service_name} stopped successfully")
            else:
                self.assistant.speak(f"Failed to stop service: {message}")
            
            return success
            
        except Exception:
            logging.exception("Failed to stop service")
            self.assistant.speak("Failed to stop service")
            return False
    
    def _handle_restart_service(self, slots: dict) -> bool:
        """Handle restart service command."""
        if self.service_manager is None:
            self.assistant.speak("Service manager not available")
            return False
        if not self.assistant.has_permission('restart_service'):
            return False
        
        try:
            service_name = slots.get('service_name')
            if not service_name:
                self.assistant.speak("Please specify a service name")
                return False
            
            success, message = self.service_manager.restart_service(service_name)
            
            if success:
                self.assistant.speak(f"Service {service_name} restarted successfully")
            else:
                self.assistant.speak(f"Failed to restart service: {message}")
            
            return success
            
        except Exception:
            logging.exception("Failed to restart service")
            self.assistant.speak("Failed to restart service")
            return False
    
    def _handle_get_service_status(self, slots: dict) -> bool:
        """Handle get service status command."""
        if self.service_manager is None:
            self.assistant.speak("Service manager not available")
            return False
        try:
            service_name = slots.get('service_name')
            if not service_name:
                self.assistant.speak("Please specify a service name")
                return False
            
            status = self.service_manager.get_service_status(service_name)
            
            if status:
                state = status.get('state', 'Unknown')
                self.assistant.speak(f"Service {service_name} is {state}")
            else:
                self.assistant.speak(f"Service {service_name} not found")
            
            return status is not None
            
        except Exception:
            logging.exception("Failed to get service status")
            self.assistant.speak("Failed to get service status")
            return False
    
    def _handle_list_services(self, slots: dict) -> bool:
        """Handle list services command."""
        if self.service_manager is None:
            self.assistant.speak("Service manager not available")
            return False
        try:
            state_filter = slots.get('state')  # e.g., 'running', 'stopped'
            
            from integrations.windows_service_manager import ServiceState
            state_enum = None
            if state_filter:
                try:
                    state_enum = ServiceState(state_filter.lower())
                except ValueError:
                    pass
            
            services = self.service_manager.list_services(state_filter=state_enum)
            
            if services:
                count = len(services)
                names = [s.get('name', 'Unknown') for s in services[:10]]
                self.assistant.speak(f"Found {count} services. Some examples: {', '.join(names)}")
            else:
                self.assistant.speak("No services found")
            
            return True
            
        except Exception:
            logging.exception("Failed to list services")
            self.assistant.speak("Failed to list services")
            return False
    
    def _handle_set_service_start_type(self, slots: dict) -> bool:
        """Handle set service start type command."""
        if self.service_manager is None:
            self.assistant.speak("Service manager not available")
            return False
        if not self.assistant.has_permission('configure_service'):
            return False
        
        try:
            service_name = slots.get('service_name')
            start_type_str = slots.get('start_type', 'auto')
            
            if not service_name:
                self.assistant.speak("Please specify a service name")
                return False
            
            from integrations.windows_service_manager import ServiceStartType
            try:
                start_type = ServiceStartType(start_type_str.lower())
            except ValueError:
                self.assistant.speak(f"Invalid start type: {start_type_str}")
                return False
            
            success, message = self.service_manager.set_service_start_type(service_name, start_type)
            
            if success:
                self.assistant.speak(f"Service {service_name} start type set to {start_type.value}")
            else:
                self.assistant.speak(f"Failed to set start type: {message}")
            
            return success
            
        except Exception:
            logging.exception("Failed to set service start type")
            self.assistant.speak("Failed to set service start type")
            return False
    
    def _handle_get_service_dependencies(self, slots: dict) -> bool:
        """Handle get service dependencies command."""
        if self.service_manager is None:
            self.assistant.speak("Service manager not available")
            return False
        try:
            service_name = slots.get('service_name')
            if not service_name:
                self.assistant.speak("Please specify a service name")
                return False
            
            dependencies = self.service_manager.get_service_dependencies(service_name)
            
            if dependencies:
                deps_text = ", ".join(dependencies)
                self.assistant.speak(f"Service {service_name} depends on: {deps_text}")
            else:
                self.assistant.speak(f"Service {service_name} has no dependencies")
            
            return True
            
        except Exception:
            logging.exception("Failed to get service dependencies")
            self.assistant.speak("Failed to get service dependencies")
            return False
    
    def _handle_configure_service_recovery(self, slots: dict) -> bool:
        """Handle configure service recovery command."""
        if self.service_manager is None:
            self.assistant.speak("Service manager not available")
            return False
        if not self.assistant.has_permission('configure_service'):
            return False
        
        try:
            service_name = slots.get('service_name')
            if not service_name:
                self.assistant.speak("Please specify a service name")
                return False
            
            action = slots.get('action', 'restart')
            
            success, message = self.service_manager.configure_service_recovery(
                service_name,
                first_failure=action,
                second_failure=action,
                subsequent_failures=action
            )
            
            if success:
                self.assistant.speak(f"Service {service_name} recovery configured")
            else:
                self.assistant.speak(f"Failed to configure recovery: {message}")
            
            return success
            
        except Exception:
            logging.exception("Failed to configure service recovery")
            self.assistant.speak("Failed to configure service recovery")
            return False