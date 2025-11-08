# -*- coding: utf-8 -*-
"""
Active Directory Management Skill
Phase 2.1: AD user account management
"""

from skills.base_skill import BaseSkill
from typing import Dict, Any
import logging


class ADSkill(BaseSkill):
    """
    Skill for managing Active Directory users and groups.
    """
    
    def __init__(self, assistant):
        super().__init__(assistant)
        self.intents = [
            'ad_create_user',
            'ad_delete_user',
            'ad_modify_user',
            'ad_lookup_user',
            'ad_get_password_policy',
            'ad_get_user_groups'
        ]
    
    def can_handle(self, intent: str) -> bool:
        return intent in self.get_intents()
    
    def get_intents(self) -> list:
        return self.intents
    
    def handle(self, intent: str, slots: dict) -> bool:
        if intent == 'ad_create_user':
            return self._handle_create_user(slots)
        elif intent == 'ad_delete_user':
            return self._handle_delete_user(slots)
        elif intent == 'ad_modify_user':
            return self._handle_modify_user(slots)
        elif intent == 'ad_lookup_user':
            return self._handle_lookup_user(slots)
        elif intent == 'ad_get_password_policy':
            return self._handle_get_password_policy()
        elif intent == 'ad_get_user_groups':
            return self._handle_get_user_groups(slots)
        return False
    
    def _handle_create_user(self, slots: dict) -> bool:
        """Handle create user command."""
        if not self.assistant.has_permission('ad_create_user'):
            return False
        
        try:
            username = slots.get('username')
            if not username:
                self.assistant.speak("Please specify a username")
                return False
            
            # Get password (might need to prompt)
            password = slots.get('password') or 'TempPassword123!'
            display_name = slots.get('display_name') or username
            email = slots.get('email')
            department = slots.get('department')
            
            if not hasattr(self.assistant, 'ad_client') or not self.assistant.ad_client:
                self.assistant.speak("Active Directory integration is not available")
                return False
            
            success, message = self.assistant.ad_client.create_user(
                username=username,
                password=password,
                display_name=display_name,
                email=email,
                department=department
            )
            
            if success:
                self.assistant.speak(f"User {username} created successfully")
            else:
                self.assistant.speak(f"Failed to create user: {message}")
            
            return success
            
        except Exception:
            logging.exception("Failed to create AD user")
            self.assistant.speak("Failed to create user")
            return False
    
    def _handle_delete_user(self, slots: dict) -> bool:
        """Handle delete user command."""
        if not self.assistant.has_permission('ad_delete_user'):
            return False
        
        try:
            username = slots.get('username')
            if not username:
                self.assistant.speak("Please specify a username")
                return False
            
            if not self.assistant.confirm_action(f"Are you sure you want to delete user {username}?"):
                return False
            
            if not hasattr(self.assistant, 'ad_client') or not self.assistant.ad_client:
                self.assistant.speak("Active Directory integration is not available")
                return False
            
            success, message = self.assistant.ad_client.delete_user(username)
            
            if success:
                self.assistant.speak(f"User {username} deleted successfully")
            else:
                self.assistant.speak(f"Failed to delete user: {message}")
            
            return success
            
        except Exception:
            logging.exception("Failed to delete AD user")
            self.assistant.speak("Failed to delete user")
            return False
    
    def _handle_modify_user(self, slots: dict) -> bool:
        """Handle modify user command."""
        if not self.assistant.has_permission('ad_modify_user'):
            return False
        
        try:
            username = slots.get('username')
            if not username:
                self.assistant.speak("Please specify a username")
                return False
            
            # Build attributes dict
            attributes = {}
            if slots.get('display_name'):
                attributes['displayName'] = slots['display_name']
            if slots.get('email'):
                attributes['mail'] = slots['email']
            if slots.get('department'):
                attributes['department'] = slots['department']
            
            if not attributes:
                self.assistant.speak("Please specify attributes to modify")
                return False
            
            if not hasattr(self.assistant, 'ad_client') or not self.assistant.ad_client:
                self.assistant.speak("Active Directory integration is not available")
                return False
            
            success, message = self.assistant.ad_client.modify_user(username, attributes)
            
            if success:
                self.assistant.speak(f"User {username} modified successfully")
            else:
                self.assistant.speak(f"Failed to modify user: {message}")
            
            return success
            
        except Exception:
            logging.exception("Failed to modify AD user")
            self.assistant.speak("Failed to modify user")
            return False
    
    def _handle_lookup_user(self, slots: dict) -> bool:
        """Handle lookup user command."""
        try:
            username = slots.get('username')
            if not username:
                self.assistant.speak("Please specify a username")
                return False
            
            if not hasattr(self.assistant, 'ad_client') or not self.assistant.ad_client:
                self.assistant.speak("Active Directory integration is not available")
                return False
            
            user_info = self.assistant.ad_client.lookup_user(username)
            
            if user_info:
                info_text = f"User {username}: "
                if user_info.get('display_name'):
                    info_text += f"Name: {user_info['display_name']}, "
                if user_info.get('email'):
                    info_text += f"Email: {user_info['email']}, "
                if user_info.get('department'):
                    info_text += f"Department: {user_info['department']}"
                self.assistant.speak(info_text)
            else:
                self.assistant.speak(f"User {username} not found")
            
            return user_info is not None
            
        except Exception:
            logging.exception("Failed to lookup AD user")
            self.assistant.speak("Failed to lookup user")
            return False
    
    def _handle_get_password_policy(self) -> bool:
        """Handle get password policy command."""
        try:
            if not hasattr(self.assistant, 'ad_client') or not self.assistant.ad_client:
                self.assistant.speak("Active Directory integration is not available")
                return False
            
            policy = self.assistant.ad_client.get_password_policy()
            
            if policy:
                self.assistant.speak(f"Password policy: Minimum length {policy.get('minPwdLength', 'N/A')}")
            else:
                self.assistant.speak("Could not retrieve password policy")
            
            return policy is not None
            
        except Exception:
            logging.exception("Failed to get password policy")
            self.assistant.speak("Failed to get password policy")
            return False
    
    def _handle_get_user_groups(self, slots: dict) -> bool:
        """Handle get user groups command."""
        try:
            username = slots.get('username')
            
            if not hasattr(self.assistant, 'ad_client') or not self.assistant.ad_client:
                self.assistant.speak("Active Directory integration is not available")
                return False
            
            groups = self.assistant.ad_client.get_user_groups(username)
            
            if groups:
                groups_text = ", ".join(groups[:10])  # Limit to first 10
                if len(groups) > 10:
                    groups_text += f" and {len(groups) - 10} more"
                self.assistant.speak(f"User {username or 'current user'} is in groups: {groups_text}")
            else:
                self.assistant.speak(f"No groups found for user {username or 'current user'}")
            
            return True
            
        except Exception:
            logging.exception("Failed to get user groups")
            self.assistant.speak("Failed to get user groups")
            return False

