"""
SEBAS Permission Manager
Manages role-based permissions and authorization checks.
"""

import logging
from sebas.constants.permissions import (
    Role, 
    is_authorized as check_authorized,
    get_permission_for_intent,
    role_level
)


class PermissionManager:
    """
    Permission manager for SEBAS.
    Provides authorization checking for commands and intents.
    """

    def __init__(self):
        """Initialize the permission manager."""
        logging.info("[PermissionManager] Initialized")

    def is_authorized(self, user_role: Role, intent: str) -> bool:
        """
        Check if a user role is authorized for a specific intent.
        Uses the global is_authorized function from constants.permissions.
        
        Args:
            user_role: The user's Role enum value
            intent: The name of the intent to check
            
        Returns:
            bool: True if authorized, False otherwise
        """
        return check_authorized(user_role, intent)

    def has_permission(self, sebas_instance, intent: str) -> bool:
        """
        Legacy method: Check if SEBAS instance user has permission for intent.
        
        Args:
            sebas_instance: The SEBAS instance with a 'role' or 'user_role' attribute
            intent: The name of the intent to check
            
        Returns:
            bool: True if authorized, False otherwise
        """
        # Try to get user_role first, fallback to role
        user_role = getattr(sebas_instance, "user_role", None)
        if user_role is None:
            user_role = getattr(sebas_instance, "role", Role.STANDARD)
        
        required = self.get_required_role(intent)
        
        # Use role hierarchy comparison
        return role_level(user_role) >= role_level(required)

    def get_required_role(self, intent: str) -> Role:
        """
        Get the minimum required role for an intent.
        
        Args:
            intent: The name of the intent
            
        Returns:
            Role: The minimum required role (defaults to STANDARD)
        """
        return get_permission_for_intent(intent)

    def check_permission(self, user_role: Role, intent_name: str) -> bool:
        """
        Alias for is_authorized for backward compatibility.
        
        Args:
            user_role: The user's Role enum value
            intent_name: The name of the intent to check
            
        Returns:
            bool: True if authorized, False otherwise
        """
        return self.is_authorized(user_role, intent_name)

    def get_role_level(self, role: Role) -> int:
        """
        Get the numeric level of a role for comparison.
        
        Args:
            role: The Role enum value
            
        Returns:
            int: The numeric level of the role
        """
        return role_level(role)

    def validate_role(self, role_name: str) -> Role:
        """
        Validate and convert a role name string to a Role enum.
        
        Args:
            role_name: String name of the role (e.g., "ADMIN_OWNER")
            
        Returns:
            Role: The corresponding Role enum value
            
        Raises:
            ValueError: If the role name is invalid
        """
        try:
            return Role[role_name.upper().strip()]
        except KeyError:
            raise ValueError(f"Invalid role name: {role_name}")