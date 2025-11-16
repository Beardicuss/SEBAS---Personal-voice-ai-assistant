from ..constants.permissions import Role, _INTENT_PERMISSIONS as INTENT_PERMISSIONS


class PermissionManager:

    def get_required_role(self, intent: str) -> Role:
        return INTENT_PERMISSIONS.get(intent, Role.STANDARD)

    def has_permission(self, sebas_instance, intent: str) -> bool:
        required = self.get_required_role(intent)
        user_role = getattr(sebas_instance, "role", Role.STANDARD)

        # Нормируем на int (ADMIN=2 > STANDARD=1)
        return user_role.value >= required.value
