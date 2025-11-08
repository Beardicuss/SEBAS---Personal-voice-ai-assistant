import enum
from typing import Dict

class Role(enum.Enum):
    STANDARD = 1
    ADMIN = 2


# Permission mapping: intent name -> required role
_INTENT_PERMISSIONS: Dict[str, Role] = {
    # System commands - require ADMIN
    'shutdown_computer': Role.ADMIN,
    'restart_computer': Role.ADMIN,
    'schedule_shutdown': Role.ADMIN,
    'lock_computer': Role.ADMIN,
    'sleep_computer': Role.ADMIN,
    'hibernate_computer': Role.ADMIN,
    'log_off_user': Role.ADMIN,
    
    # Process management - require ADMIN
    'kill_process': Role.ADMIN,
    'list_processes': Role.ADMIN,
    
    # File operations - require ADMIN for destructive operations
    'delete_path': Role.ADMIN,
    'create_folder': Role.ADMIN,
    'run_shell_command': Role.ADMIN,
    
    # System info - STANDARD
    'get_cpu_info': Role.STANDARD,
    'get_weather': Role.STANDARD,
    'get_ip_address': Role.STANDARD,
    'run_speed_test': Role.STANDARD,
    
    # Application control - STANDARD
    'open_application': Role.STANDARD,
    'open_app_with_context': Role.STANDARD,
    'close_application': Role.STANDARD,
    'list_programs': Role.STANDARD,
    'scan_programs': Role.STANDARD,
    
    # Media control - STANDARD
    'set_volume': Role.STANDARD,
    'set_brightness': Role.STANDARD,
    
    # Utilities - STANDARD
    'create_note': Role.STANDARD,
    'take_screenshot': Role.STANDARD,
    'web_search': Role.STANDARD,
    
    # Skills - mostly STANDARD
    'get_system_performance': Role.STANDARD,
    'get_network_stats': Role.STANDARD,
    'get_disk_io': Role.STANDARD,
    'check_disk_space': Role.STANDARD,
    
    # Phase 2.1: AD operations
    'ad_create_user': Role.ADMIN,
    'ad_delete_user': Role.ADMIN,
    'ad_modify_user': Role.ADMIN,
    'ad_lookup_user': Role.STANDARD,
    'ad_get_password_policy': Role.STANDARD,
    'ad_get_user_groups': Role.STANDARD,
    
    # Phase 2.1: Service management
    'start_service': Role.ADMIN,
    'stop_service': Role.ADMIN,
    'restart_service': Role.ADMIN,
    'get_service_status': Role.STANDARD,
    'list_services': Role.STANDARD,
    'configure_service': Role.ADMIN,
    'get_service_dependencies': Role.STANDARD,
    'set_service_start_type': Role.ADMIN,
    
    # Phase 2.1: Process management
    'set_process_priority': Role.ADMIN,
    'set_cpu_affinity': Role.ADMIN,
    
    # Phase 2.2: Network management
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
    
    # Phase 3.1: Advanced file operations
    'copy_recursive': Role.ADMIN,
    'move_recursive': Role.ADMIN,
    'delete_recursive': Role.ADMIN,
    'search_file_content': Role.STANDARD,
    'find_duplicate_files': Role.STANDARD,
    
    # Phase 3.2: Storage management
    'list_disk_partitions': Role.STANDARD,
    'get_disk_info': Role.STANDARD,
    'get_volume_info': Role.STANDARD,
    'get_storage_spaces_status': Role.STANDARD,
    'get_bitlocker_status': Role.STANDARD,
    'enable_bitlocker': Role.ADMIN,
    'disable_bitlocker': Role.ADMIN,
    'get_disk_usage': Role.STANDARD,
    
    # Phase 4.1: Security management
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
    
    # Phase 4.2: Compliance management
    'log_activity': Role.STANDARD,
    'get_activity_log': Role.STANDARD,
    'get_audit_events': Role.STANDARD,
    'generate_compliance_report': Role.ADMIN,
    'verify_security_policy': Role.STANDARD,
    
    # Phase 5.1: Automation
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
    
    # System status queries
    'get_system_status': Role.STANDARD,
    'get_memory_info': Role.STANDARD,
    'get_cpu_info': Role.STANDARD,
    
    # Phase 6.1: AI Analytics
    'detect_anomalies': Role.STANDARD,
    'predict_disk_failure': Role.STANDARD,
    'predict_memory_leak': Role.STANDARD,
    'get_performance_suggestions': Role.STANDARD,
    'get_troubleshooting_guide': Role.STANDARD,
    'diagnose_issue': Role.STANDARD,
    
    # Phase 6.2: Enhanced NLU
    'parse_multipart_command': Role.STANDARD,
    'get_context': Role.STANDARD,
    'clear_context': Role.STANDARD,
    'record_correction': Role.STANDARD,
    'resolve_ambiguous_intent': Role.STANDARD,
}


def get_permission_for_intent(intent_name: str) -> Role:
    """
    Get the required role for an intent.
    
    Args:
        intent_name: Name of the intent
        
    Returns:
        Required Role (defaults to STANDARD if not specified)
    """
    return _INTENT_PERMISSIONS.get(intent_name, Role.STANDARD)
