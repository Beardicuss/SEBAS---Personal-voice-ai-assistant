# -*- coding: utf-8 -*-
"""
Smart Home Skill - Stage 2 Mk.II
Handles smart home device control via Home Assistant, MQTT, or REST APIs
"""

import logging
from sebas.skills.base_skill import BaseSkill
from sebas.typing import Dict, Any, List, Optional
import requests
import json


class SmartHomeSkill(BaseSkill):
    """
    Skill for controlling smart home devices.
    Supports Home Assistant, MQTT, and generic REST APIs.
    """
    
    def __init__(self, assistant_ref):
        super().__init__(assistant_ref)
        
        # Configuration (can be moved to preferences later)
        self.home_assistant_url = None
        self.home_assistant_token = None
        self.devices = {}
        
        self._load_config()
    
    def _load_config(self):
        """Load smart home configuration from preferences"""
        try:
            import os
            self.home_assistant_url = os.environ.get('SEBAS_HA_URL')
            self.home_assistant_token = os.environ.get('SEBAS_HA_TOKEN')
            
            if self.home_assistant_url:
                logging.info(f"[SmartHome] Home Assistant configured: {self.home_assistant_url}")
            else:
                logging.warning("[SmartHome] No Home Assistant URL configured")
        except Exception:
            logging.exception("[SmartHome] Failed to load configuration")
    
    def get_intents(self) -> List[str]:
        return [
            'turn_on_device',
            'turn_off_device',
            'toggle_device',
            'set_brightness',
            'set_thermostat',
            'lock_door',
            'unlock_door',
            'get_device_status',
            'list_devices',
            'create_scene',
            'activate_scene',
        ]
    
    def can_handle(self, intent: str) -> bool:
        return intent in self.get_intents()
    
    def handle(self, intent: str, slots: Dict[str, Any]) -> bool:
        """Handle smart home intents"""
        
        if not self.home_assistant_url:
            self.assistant.speak("Smart home is not configured. Please set SEBAS_HA_URL environment variable.")
            return False
        
        try:
            if intent == 'turn_on_device':
                return self._turn_on_device(slots)
            elif intent == 'turn_off_device':
                return self._turn_off_device(slots)
            elif intent == 'toggle_device':
                return self._toggle_device(slots)
            elif intent == 'set_brightness':
                return self._set_brightness(slots)
            elif intent == 'set_thermostat':
                return self._set_thermostat(slots)
            elif intent == 'lock_door':
                return self._lock_door(slots)
            elif intent == 'unlock_door':
                return self._unlock_door(slots)
            elif intent == 'get_device_status':
                return self._get_device_status(slots)
            elif intent == 'list_devices':
                return self._list_devices()
            elif intent == 'activate_scene':
                return self._activate_scene(slots)
            
            return False
            
        except Exception:
            logging.exception(f"[SmartHome] Error handling intent: {intent}")
            self.assistant.speak("Smart home command failed")
            return False
    
    def _call_ha_service(self, domain: str, service: str, entity_id: str, **kwargs) -> bool:
        """Call Home Assistant service"""
        try:
            url = f"{self.home_assistant_url}/api/services/{domain}/{service}"
            headers = {
                'Authorization': f'Bearer {self.home_assistant_token}',
                'Content-Type': 'application/json'
            }
            
            data = {'entity_id': entity_id}
            data.update(kwargs)
            
            response = requests.post(url, headers=headers, json=data, timeout=5)
            return response.status_code == 200
            
        except Exception:
            logging.exception("[SmartHome] Home Assistant API call failed")
            return False
    
    def _turn_on_device(self, slots: Dict[str, Any]) -> bool:
        """Turn on a device"""
        device = slots.get('device', '').lower()
        
        if not device:
            self.assistant.speak("Please specify which device to turn on")
            return False
        
        # Map common names to entity IDs (this should be configurable)
        entity_id = self._resolve_device_name(device)
        
        if self._call_ha_service('homeassistant', 'turn_on', entity_id):
            self.assistant.speak(f"Turning on {device}")
            return True
        else:
            self.assistant.speak(f"Failed to turn on {device}")
            return False
    
    def _turn_off_device(self, slots: Dict[str, Any]) -> bool:
        """Turn off a device"""
        device = slots.get('device', '').lower()
        
        if not device:
            self.assistant.speak("Please specify which device to turn off")
            return False
        
        entity_id = self._resolve_device_name(device)
        
        if self._call_ha_service('homeassistant', 'turn_off', entity_id):
            self.assistant.speak(f"Turning off {device}")
            return True
        else:
            self.assistant.speak(f"Failed to turn off {device}")
            return False
    
    def _toggle_device(self, slots: Dict[str, Any]) -> bool:
        """Toggle a device on/off"""
        device = slots.get('device', '').lower()
        
        if not device:
            self.assistant.speak("Please specify which device to toggle")
            return False
        
        entity_id = self._resolve_device_name(device)
        
        if self._call_ha_service('homeassistant', 'toggle', entity_id):
            self.assistant.speak(f"Toggling {device}")
            return True
        else:
            self.assistant.speak(f"Failed to toggle {device}")
            return False
    
    def _set_brightness(self, slots: Dict[str, Any]) -> bool:
        """Set brightness of a light"""
        device = slots.get('device', 'lights').lower()
        brightness = slots.get('brightness', 50)
        
        try:
            brightness = int(brightness)
            brightness = max(0, min(100, brightness))
        except ValueError:
            self.assistant.speak("Invalid brightness value")
            return False
        
        entity_id = self._resolve_device_name(device)
        brightness_byte = int(brightness * 2.55)  # Convert 0-100 to 0-255
        
        if self._call_ha_service('light', 'turn_on', entity_id, brightness=brightness_byte):
            self.assistant.speak(f"Setting {device} brightness to {brightness} percent")
            return True
        else:
            self.assistant.speak(f"Failed to set brightness")
            return False
    
    def _set_thermostat(self, slots: Dict[str, Any]) -> bool:
        """Set thermostat temperature"""
        temperature = slots.get('temperature')
        
        if not temperature:
            self.assistant.speak("Please specify target temperature")
            return False
        
        try:
            temp = float(temperature)
        except ValueError:
            self.assistant.speak("Invalid temperature value")
            return False
        
        entity_id = 'climate.thermostat'  # Should be configurable
        
        if self._call_ha_service('climate', 'set_temperature', entity_id, temperature=temp):
            self.assistant.speak(f"Setting thermostat to {temp} degrees")
            return True
        else:
            self.assistant.speak("Failed to set thermostat")
            return False
    
    def _lock_door(self, slots: Dict[str, Any]) -> bool:
        """Lock a door"""
        door = slots.get('door', 'front door')
        entity_id = self._resolve_device_name(door)
        
        if self._call_ha_service('lock', 'lock', entity_id):
            self.assistant.speak(f"Locking {door}")
            return True
        else:
            self.assistant.speak(f"Failed to lock {door}")
            return False
    
    def _unlock_door(self, slots: Dict[str, Any]) -> bool:
        """Unlock a door"""
        door = slots.get('door', 'front door')
        entity_id = self._resolve_device_name(door)
        
        # Security check
        if not self.assistant.has_permission('unlock_door'):
            self.assistant.speak("You don't have permission to unlock doors")
            return False
        
        if self._call_ha_service('lock', 'unlock', entity_id):
            self.assistant.speak(f"Unlocking {door}")
            return True
        else:
            self.assistant.speak(f"Failed to unlock {door}")
            return False
    
    def _get_device_status(self, slots: Dict[str, Any]) -> bool:
        """Get status of a device"""
        device = slots.get('device', '').lower()
        
        if not device:
            self.assistant.speak("Please specify which device")
            return False
        
        try:
            entity_id = self._resolve_device_name(device)
            url = f"{self.home_assistant_url}/api/states/{entity_id}"
            headers = {'Authorization': f'Bearer {self.home_assistant_token}'}
            
            response = requests.get(url, headers=headers, timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                state = data.get('state', 'unknown')
                self.assistant.speak(f"{device} is {state}")
                return True
            else:
                self.assistant.speak(f"Could not get status of {device}")
                return False
                
        except Exception:
            logging.exception("[SmartHome] Failed to get device status")
            self.assistant.speak("Failed to get device status")
            return False
    
    def _list_devices(self) -> bool:
        """List available devices"""
        try:
            url = f"{self.home_assistant_url}/api/states"
            headers = {'Authorization': f'Bearer {self.home_assistant_token}'}
            
            response = requests.get(url, headers=headers, timeout=5)
            
            if response.status_code == 200:
                devices = response.json()
                device_list = [d['entity_id'] for d in devices[:10]]  # First 10
                self.assistant.speak(f"Available devices: {', '.join(device_list)}")
                return True
            else:
                self.assistant.speak("Could not list devices")
                return False
                
        except Exception:
            logging.exception("[SmartHome] Failed to list devices")
            self.assistant.speak("Failed to list devices")
            return False
    
    def _activate_scene(self, slots: Dict[str, Any]) -> bool:
        """Activate a scene"""
        scene = slots.get('scene', '').lower()
        
        if not scene:
            self.assistant.speak("Please specify which scene to activate")
            return False
        
        entity_id = f"scene.{scene.replace(' ', '_')}"
        
        if self._call_ha_service('scene', 'turn_on', entity_id):
            self.assistant.speak(f"Activating {scene} scene")
            return True
        else:
            self.assistant.speak(f"Failed to activate {scene} scene")
            return False
    
    def _resolve_device_name(self, device_name: str) -> str:
        """
        Resolve friendly device name to entity ID.
        This should be configurable via preferences.
        """
        # Default mappings (should be loaded from config)
        mappings = {
            'lights': 'light.living_room',
            'living room lights': 'light.living_room',
            'bedroom lights': 'light.bedroom',
            'front door': 'lock.front_door',
            'thermostat': 'climate.thermostat',
        }
        
        return mappings.get(device_name, f"light.{device_name.replace(' ', '_')}")