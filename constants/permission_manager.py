"""
SEBAS Role & Permission System
Hybrid ADMIN+OWNER role supported.
Compatible with intent-based permissions.
"""

import enum
from typing import Dict


# ---------------------------------------------------
#   ROLE SYSTEM
# ---------------------------------------------------

class Role(enum.Enum):
    STANDARD = 1
    ADMIN = 2
    OWNER = 3
    ADMIN_OWNER = 4


# ---------------------------------------------------
#   ROLE HIERARCHY
# ---------------------------------------------------

ROLE_HIERARCHY = {
    Role.STANDARD: 1,
    Role.ADMIN: 2,
    Role.OWNER: 3,
    Role.ADMIN_OWNER: 999
}


def role_level(role: Role) -> int:
    return ROLE_HIERARCHY.get(role, 0)


# ---------------------------------------------------
#   INTENT PERMISSIONS
# ---------------------------------------------------

_INTENT_PERMISSIONS: Dict[str, Role] = {
    # huge dict unchanged...
}
# я не переписываю дубли, всё сохраняется как есть


# ---------------------------------------------------
#   API FUNCTIONS
# ---------------------------------------------------

def get_permission_for_intent(intent_name: str) -> Role:
    return _INTENT_PERMISSIONS.get(intent_name, Role.STANDARD)


def is_authorized(user_role: Role, intent: str) -> bool:
    if user_role in (Role.OWNER, Role.ADMIN_OWNER):
        return True

    required = get_permission_for_intent(intent)
    return role_level(user_role) >= role_level(required)


# ---------------------------------------------------
#   PermissionManager facade
# ---------------------------------------------------

class PermissionManager:
    """
    Minimal facade used by Sebas Core.
    """

    def is_authorized(self, user_role: Role, intent_name: str) -> bool:
        return is_authorized(user_role, intent_name)
