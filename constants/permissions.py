"""
SEBAS Role & Permission System
Hybrid ADMIN+OWNER role supported.
Compatible with intent-based permissions.
"""

import enum
import logging
from typing import Dict


# ---------------------------------------------------
#   ROLE SYSTEM
# ---------------------------------------------------

class Role(enum.Enum):
    STANDARD = 1
    ADMIN = 2
    OWNER = 3             # HIGHEST
    ADMIN_OWNER = 4       # HYBRID ROLE (your personal role)


# ---------------------------------------------------
#   ROLE LEVELS FOR COMPARISON
# ---------------------------------------------------

ROLE_HIERARCHY = {
    Role.STANDARD: 1,
    Role.ADMIN: 2,
    Role.OWNER: 3,
    Role.ADMIN_OWNER: 999  # absolute priority — your throne
}


def role_level(role: Role) -> int:
    return ROLE_HIERARCHY.get(role, 0)


# ---------------------------------------------------
#   OLD INTENT-BASED PERMISSIONS (fully preserved)
# ---------------------------------------------------

_INTENT_PERMISSIONS: Dict[str, Role] = {
    # ======== SYSTEM (Admin-only) ========
    'shutdown_computer': Role.ADMIN,
    'restart_computer': Role.ADMIN,
    'schedule_shutdown': Role.ADMIN,
    'lock_computer': Role.ADMIN,
    'sleep_computer': Role.ADMIN,
    'hibernate_computer': Role.ADMIN,
    'log_off_user': Role.ADMIN,

    # ======== PROCESS MGMT ========
    'kill_process': Role.ADMIN,
    'list_processes': Role.ADMIN,

    # ======== FILE OPERATIONS ========
    'delete_path': Role.ADMIN,
    'create_folder': Role.ADMIN,
    'run_shell_command': Role.ADMIN,

    # ======== INFO QUERIES ========
    'get_cpu_info': Role.STANDARD,
    'get_weather': Role.STANDARD,
    'get_ip_address': Role.STANDARD,
    'run_speed_test': Role.STANDARD,

    # ======== APPLICATION CONTROL ========
    'open_application': Role.STANDARD,
    'open_app_with_context': Role.STANDARD,
    'close_application': Role.STANDARD,
    'list_programs': Role.STANDARD,
    'scan_programs': Role.STANDARD,

    # ======== MEDIA ========
    'set_volume': Role.STANDARD,
    'set_brightness': Role.STANDARD,

    # ======== UTILITIES ========
    'create_note': Role.STANDARD,
    'take_screenshot': Role.STANDARD,
    'web_search': Role.STANDARD,

    # ======== SKILLS ========
    'get_system_performance': Role.STANDARD,
    'get_network_stats': Role.STANDARD,
    'get_disk_io': Role.STANDARD,
    'check_disk_space': Role.STANDARD,

    # ======== ACTIVE DIRECTORY ========
    'ad_create_user': Role.ADMIN,
    'ad_delete_user': Role.ADMIN,
    'ad_modify_user': Role.ADMIN,
    'ad_lookup_user': Role.STANDARD,
    'ad_get_password_policy': Role.STANDARD,
    'ad_get_user_groups': Role.STANDARD,

    # ======== SERVICES ========
    'start_service': Role.ADMIN,
    'stop_service': Role.ADMIN,
    'restart_service': Role.ADMIN,
    'get_service_status': Role.STANDARD,
    'list_services': Role.STANDARD,
    'configure_service': Role.ADMIN,
    'get_service_dependencies': Role.STANDARD,
    'set_service_start_type': Role.ADMIN,

    # ======== PROCESS CONTROL ========
    'set_process_priority': Role.ADMIN,
    'set_cpu_affinity': Role.ADMIN,

    # ======== NETWORK MGMT ========
    'set_ip_config': Role.ADMIN,
    'get_ip_config': Role.STANDARD,
    'flush_dns_cache': Role.ADMIN,
    'register_dns': Role.ADMIN,
    'test_network_connectivity': Role.STANDARD,
    'create_network_share': Role.ADMIN,
    'delete_network_share': Role.ADMIN,
    'list_network_shares': Role.STANDARD,
    'map_network_drive': Role.ADMIN,
    'unmap_network_drive': Role.ADMIN,
    'list_network_drives': Role.STANDARD,
    'create_firewall_rule': Role.ADMIN,
    'delete_firewall_rule': Role.ADMIN,
    'enable_firewall_rule': Role.ADMIN,
    'disable_firewall_rule': Role.ADMIN,
    'list_firewall_rules': Role.STANDARD,
    'get_firewall_status': Role.STANDARD,
    'get_listening_ports': Role.STANDARD,
    'test_port': Role.STANDARD,
    'get_port_statistics': Role.STANDARD,
    'connect_vpn': Role.ADMIN,
    'disconnect_vpn': Role.ADMIN,
    'list_vpn_connections': Role.STANDARD,

    # ======== STORAGE ========
    'copy_recursive': Role.ADMIN,
    'move_recursive': Role.ADMIN,
    'delete_recursive': Role.ADMIN,
    'search_file_content': Role.STANDARD,
    'find_duplicate_files': Role.STANDARD,

    # ======== SECURITY / DEFENDER ========
    'get_defender_status': Role.STANDARD,
    'run_defender_scan': Role.ADMIN,
    'get_defender_threats': Role.STANDARD,
    'remove_defender_threat': Role.ADMIN,
    'get_security_updates': Role.STANDARD,
    'detect_suspicious_processes': Role.STANDARD,
    'terminate_process': Role.ADMIN,
    'get_file_permissions': Role.STANDARD,
    'set_file_permissions': Role.ADMIN,
    'get_audit_policy': Role.STANDARD,
    'set_audit_policy': Role.ADMIN,

    # ======== COMPLIANCE ========
    'log_activity': Role.STANDARD,
    'get_activity_log': Role.STANDARD,
    'get_audit_events': Role.ADMIN,
    'generate_compliance_report': Role.ADMIN,
    'verify_security_policy': Role.ADMIN,

    # ======== AUTOMATION ========
    'create_workflow': Role.ADMIN,
    'execute_workflow': Role.ADMIN,
    'list_workflows': Role.STANDARD,
    'delete_workflow': Role.ADMIN,
    'execute_powershell': Role.ADMIN,
    'execute_batch': Role.ADMIN,
    'execute_python': Role.ADMIN,
    'create_scheduled_task': Role.ADMIN,
    'list_scheduled_tasks': Role.STANDARD,
    'run_scheduled_task': Role.ADMIN,
    'delete_scheduled_task': Role.ADMIN,

    # ======== SYSTEM STATUS ========
    'get_system_status': Role.STANDARD,
    'get_memory_info': Role.STANDARD,
    'get_cpu_info': Role.STANDARD,

    # ======== AI ANALYTICS ========
    'detect_anomalies': Role.STANDARD,
    'predict_disk_failure': Role.STANDARD,
    'predict_memory_leak': Role.STANDARD,
    'get_performance_suggestions': Role.STANDARD,
    'get_troubleshooting_guide': Role.STANDARD,
    'diagnose_issue': Role.STANDARD,

    # ======== NLU EXTENSIONS ========
    'parse_multipart_command': Role.STANDARD,
    'get_context': Role.STANDARD,
    'clear_context': Role.STANDARD,
    'record_correction': Role.STANDARD,
    'resolve_ambiguous_intent': Role.STANDARD,
    'run_compliance_check': Role.ADMIN,
    'check_uac_compliance': Role.ADMIN,
    'check_authentication_compliance': Role.ADMIN,
    'check_network_compliance': Role.ADMIN,
    'check_system_hardening': Role.ADMIN,
}


# ---------------------------------------------------
#   API FUNCTIONS
# ---------------------------------------------------

def get_permission_for_intent(intent_name: str) -> Role:
    return _INTENT_PERMISSIONS.get(intent_name, Role.STANDARD)


def is_authorized(user_role: Role, intent: str) -> bool:
    """
    Unified permission checker.
    OWNER/Admin_Owner bypass all permission checks.
    """
    if user_role in (Role.OWNER, Role.ADMIN_OWNER):
        return True

    required = get_permission_for_intent(intent)
    return role_level(user_role) >= role_level(required)