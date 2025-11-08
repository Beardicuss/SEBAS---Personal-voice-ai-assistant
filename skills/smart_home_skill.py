# -*- coding: utf-8 -*-
"""
Smart Home Skill - Handles smart home device control and automation
"""

from skills.base_skill import BaseSkill
from integrations.smart_home import HomeAssistantClient
from typing import Dict, List, Any, Optional
import re
import threading


class SmartHomeSkill(BaseSkill):
    """
    Skill for handling smart home commands and integrations.
    """

    def __init__(self, assistant_ref):
        super().__init__(assistant_ref)
        self.client = HomeAssistantClient()
        self.entities = {}  # Cache discovered entities
        self.automations = []  # Active automation triggers
        self._load_entities()
        self._start_websocket()
        self.confirmation_required = True  # For security commands

    def get_intents(self) -> List[str]:
        return [
            'smarthome_toggle',
            'smarthome_set_light',
            'smarthome_set_climate',
            'smarthome_activate_scene',
            'smarthome_create_scene',
            'smarthome_query_status',
            'smarthome_query_temperature',
            'smarthome_control_multiple',
            'smarthome_control_lock',
            'smarthome_control_media'
        ]

    def can_handle(self, intent: str) -> bool:
        return intent in self.get_intents()

    def handle(self, intent: str, slots: Dict[str, Any]) -> bool:
        try:
            if not self.client.available():
                self.assistant.speak("Smart home integration is not configured. Please set HA_BASE_URL and HA_TOKEN environment variables.")
                return False

            if intent == 'smarthome_toggle':
                return self._handle_toggle(slots)
            elif intent == 'smarthome_set_light':
                return self._handle_set_light(slots)
            elif intent == 'smarthome_set_climate':
                return self._handle_set_climate(slots)
            elif intent == 'smarthome_activate_scene':
                return self._handle_activate_scene(slots)
            elif intent == 'smarthome_create_scene':
                return self._handle_create_scene(slots)
            elif intent == 'smarthome_query_status':
                return self._handle_query_status(slots)
            elif intent == 'smarthome_query_temperature':
                return self._handle_query_temperature(slots)
            elif intent == 'smarthome_control_multiple':
                return self._handle_control_multiple(slots)
            elif intent == 'smarthome_control_lock':
                return self._handle_control_lock(slots)
            elif intent == 'smarthome_control_media':
                return self._handle_control_media(slots)
            return False
        except Exception as e:
            self.logger.exception(f"Error handling smart home intent {intent}")
            self.assistant.speak("An error occurred while controlling smart home devices")
            return False

    def _load_entities(self):
        """Load and cache entities from Home Assistant."""
        entities = self.client.get_entities()
        self.entities = {e['entity_id']: e for e in entities}
        self.logger.info(f"Loaded {len(self.entities)} smart home entities")

    def _start_websocket(self):
        """Start WebSocket connection for real-time updates."""
        def on_state_change(entity):
            # Handle proactive suggestions based on state changes
            if entity['entity_id'].startswith('binary_sensor.motion'):
                self._handle_motion_detected(entity)
            elif entity['entity_id'].startswith('sensor.temperature'):
                self._handle_temperature_change(entity)

        self.client.add_listener(on_state_change)
        threading.Thread(target=self.client.connect_websocket, daemon=True).start()

    def _resolve_entity(self, device_name: str) -> Optional[str]:
        """Resolve device name to entity ID."""
        device_lower = device_name.lower().replace(' ', '_')
        # Try exact match first
        for eid in self.entities:
            if device_lower in eid.lower():
                return eid
        # Try fuzzy match on friendly names
        for eid, entity in self.entities.items():
            friendly_name = entity.get('attributes', {}).get('friendly_name', '').lower()
            if device_lower in friendly_name:
                return eid
        return None

    def _handle_toggle(self, slots: Dict[str, Any]) -> bool:
        device = slots.get('device', '')
        state = slots.get('state', '').lower() == 'on'
        entity_id = self._resolve_entity(device)
        if not entity_id:
            self.assistant.speak(f"Could not find device {device}")
            return False

        if entity_id.startswith('switch.'):
            success = self.client.set_switch(entity_id, state)
        elif entity_id.startswith('light.'):
            success = self.client.set_light(entity_id, state)
        else:
            self.assistant.speak(f"Device {device} doesn't support on/off control")
            return False

        if success:
            self.assistant.speak(f"Turned {device} {'on' if state else 'off'}")
            return True
        else:
            self.assistant.speak(f"Failed to control {device}")
            return False

    def _handle_set_light(self, slots: Dict[str, Any]) -> bool:
        device = slots.get('device', '')
        brightness = int(slots.get('brightness', 100))
        entity_id = self._resolve_entity(device)
        if not entity_id or not entity_id.startswith('light.'):
            self.assistant.speak(f"Could not find light {device}")
            return False

        brightness_pct = min(255, max(0, int((brightness / 100) * 255)))
        success = self.client.set_light(entity_id, True, brightness=brightness_pct)
        if success:
            self.assistant.speak(f"Set {device} brightness to {brightness}%")
            return True
        else:
            self.assistant.speak(f"Failed to set {device} brightness")
            return False

    def _handle_set_climate(self, slots: Dict[str, Any]) -> bool:
        temperature = float(slots.get('temperature', 20))
        room = slots.get('room', '')
        entity_id = self._resolve_entity(f"{room} thermostat") or self._resolve_entity("thermostat")
        if not entity_id or not entity_id.startswith('climate.'):
            self.assistant.speak(f"Could not find thermostat for {room or 'the room'}")
            return False

        success = self.client.set_climate(entity_id, temperature=temperature)
        if success:
            self.assistant.speak(f"Set temperature to {temperature} degrees")
            return True
        else:
            self.assistant.speak("Failed to set temperature")
            return False

    def _handle_activate_scene(self, slots: Dict[str, Any]) -> bool:
        scene = slots.get('scene', '')
        entity_id = self._resolve_entity(f"scene.{scene}")
        if not entity_id:
            # Try with scene prefix
            entity_id = f"scene.{scene.replace(' ', '_').lower()}"
            if entity_id not in self.entities:
                self.assistant.speak(f"Could not find scene {scene}")
                return False

        success = self.client.activate_scene(entity_id)
        if success:
            self.assistant.speak(f"Activated scene {scene}")
            return True
        else:
            self.assistant.speak(f"Failed to activate scene {scene}")
            return False

    def _handle_create_scene(self, slots: Dict[str, Any]) -> bool:
        name = slots.get('name', '')
        devices = slots.get('devices', '')
        # Parse devices (simplified parsing)
        device_list = [d.strip() for d in devices.split('and')]
        entities = {}
        for device in device_list:
            entity_id = self._resolve_entity(device)
            if entity_id:
                entities[entity_id] = {"state": "on"}

        if not entities:
            self.assistant.speak("Could not identify any devices for the scene")
            return False

        success = self.client.create_scene(name, entities)
        if success:
            self.assistant.speak(f"Created scene {name} with {len(entities)} devices")
            return True
        else:
            self.assistant.speak(f"Failed to create scene {name}")
            return False

    def _handle_query_status(self, slots: Dict[str, Any]) -> bool:
        device = slots.get('device', '')
        entity_id = self._resolve_entity(device)
        if not entity_id:
            self.assistant.speak(f"Could not find device {device}")
            return False

        status = self.client.query_status(entity_id)
        if status:
            self.assistant.speak(status)
            return True
        else:
            self.assistant.speak(f"Could not get status for {device}")
            return False

    def _handle_query_temperature(self, slots: Dict[str, Any]) -> bool:
        room = slots.get('room', '')
        entity_id = self._resolve_entity(f"{room} temperature")
        if not entity_id:
            entity_id = self._resolve_entity("temperature")
        if not entity_id or not entity_id.startswith('sensor.'):
            self.assistant.speak(f"Could not find temperature sensor for {room}")
            return False

        state = self.client.get_entity_state(entity_id)
        if state:
            temp = state.get('state')
            unit = state.get('attributes', {}).get('unit_of_measurement', '°C')
            self.assistant.speak(f"The temperature in {room or 'the room'} is {temp} {unit}")
            return True
        else:
            self.assistant.speak(f"Could not get temperature for {room}")
            return False

    def _handle_control_multiple(self, slots: Dict[str, Any]) -> bool:
        brightness = slots.get('brightness')
        state = slots.get('state', '').lower() == 'on'

        # Find all lights
        light_entities = [eid for eid in self.entities if eid.startswith('light.')]
        if not light_entities:
            self.assistant.speak("No lights found")
            return False

        if brightness:
            brightness_pct = min(255, max(0, int((int(brightness) / 100) * 255)))
            success = self.client.control_multiple(light_entities, "turn_on", brightness=brightness_pct)
            action = f"set brightness to {brightness}%"
        else:
            success = self.client.control_multiple(light_entities, "turn_on" if state else "turn_off")
            action = f"turned {'on' if state else 'off'}"

        if success:
            self.assistant.speak(f"All lights {action}")
            return True
        else:
            self.assistant.speak("Failed to control lights")
            return False

    def _handle_control_lock(self, slots: Dict[str, Any]) -> bool:
        device = slots.get('device', '')
        action = slots.get('action', '')
        lock = action == 'lock'

        # Always require confirmation for security-related commands
        if not self.assistant.confirm_action(f"Are you sure you want to {action} {device}? This is a security action."):
            self.assistant.speak("Action cancelled.")
            return True  # User cancelled, but this is not a failure

        entity_id = self._resolve_entity(device)
        if not entity_id or not entity_id.startswith('lock.'):
            self.assistant.speak(f"Could not find lock {device}")
            return False

        success = self.client.set_lock(entity_id, lock)
        if success:
            self.assistant.speak(f"{action.capitalize()}ed {device}")
            return True
        else:
            self.assistant.speak(f"Failed to {action} {device}")
            return False

    def _handle_control_media(self, slots: Dict[str, Any]) -> bool:
        device = slots.get('device', '')
        action = slots.get('action', '')
        direction = slots.get('direction', '')
        volume = slots.get('volume')

        if direction:
            action = f"volume_{direction}"
        elif volume:
            action = "set_volume"
            volume = int(volume)

        entity_id = self._resolve_entity(device)
        if not entity_id or not entity_id.startswith('media_player.'):
            self.assistant.speak(f"Could not find media player {device}")
            return False

        success = self.client.control_media_player(entity_id, action, volume_level=volume if volume else None)
        if success:
            if volume:
                self.assistant.speak(f"Set {device} volume to {volume}")
            else:
                self.assistant.speak(f"{action.replace('_', ' ').capitalize()} on {device}")
            return True
        else:
            self.assistant.speak(f"Failed to control {device}")
            return False

    def _handle_motion_detected(self, entity):
        """Proactive suggestion for motion detection."""
        if entity.get('state') == 'on':
            room = entity.get('attributes', {}).get('friendly_name', 'unknown room')
            self.assistant.speak(f"Motion detected in {room}. Would you like me to turn on the lights?", proactive=True)

    def _handle_temperature_change(self, entity):
        """Proactive suggestion for temperature changes."""
        try:
            temp = float(entity.get('state', 0))
            if temp > 25:
                self.assistant.speak("It's getting warm. Would you like me to adjust the thermostat?", proactive=True)
            elif temp < 18:
                self.assistant.speak("It's getting cool. Would you like me to adjust the thermostat?", proactive=True)
        except (ValueError, TypeError):
            pass

    def add_automation_trigger(self, trigger: Dict[str, Any]):
        """Add automation trigger (for future expansion)."""
        self.automations.append(trigger)

    def get_description(self) -> str:
        return "Smart Home Skill - Controls smart home devices, scenes, and provides status updates"