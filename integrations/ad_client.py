# -*- coding: utf-8 -*-
"""
Active Directory Integration Client

Phase 2: Active Directory Integration
Provides authentication, user lookup, and group membership checking
for enterprise environments.
"""

import logging
import os
import platform
from typing import Optional, Dict, List, Tuple, Any
from constants.permissions import Role

# Try to import LDAP3 for LDAP operations
try:
    from ldap3 import Server, Connection, ALL, NTLM, SIMPLE, SUBTREE
    LDAP3_AVAILABLE = True
except ImportError:
    LDAP3_AVAILABLE = False
    logging.warning("ldap3 not available. AD integration will be limited to Windows authentication only.")

# Try to import Windows security modules
try:
    import win32security
    import win32api
    import win32con
    WIN32_AVAILABLE = True
except ImportError:
    WIN32_AVAILABLE = False
    logging.warning("pywin32 not available. Windows Integrated Authentication will not work.")


class ADClient:
    """
    Active Directory client for authentication and user management.
    Supports both LDAP-based and Windows Integrated Authentication.
    """
    
    def __init__(self, domain: Optional[str] = None, ldap_server: Optional[str] = None,
                 use_windows_auth: bool = True, bind_user: Optional[str] = None,
                 bind_password: Optional[str] = None):
        """
        Initialize AD client.
        
        Args:
            domain: AD domain name (e.g., 'example.com' or 'EXAMPLE')
            ldap_server: LDAP server address (e.g., 'ldap://dc1.example.com')
            use_windows_auth: Use Windows Integrated Authentication if available
            bind_user: LDAP bind username (optional, for service account)
            bind_password: LDAP bind password (optional)
        """
        self.domain = domain or self._detect_domain()
        self.ldap_server = ldap_server or self._get_ldap_server()
        self.use_windows_auth = use_windows_auth and WIN32_AVAILABLE
        self.bind_user = bind_user
        self.bind_password = bind_password
        self.connection = None
        self._current_user = None
        self._user_groups = None
        
        # Role mapping: AD groups -> SEBAS roles
        # Can be configured via preferences
        self.role_mapping = {
            'Domain Admins': Role.ADMIN,
            'Enterprise Admins': Role.ADMIN,
            'Schema Admins': Role.ADMIN,
            'Administrators': Role.ADMIN,
            # Add more mappings as needed
        }
        
        logging.info(f"ADClient initialized: domain={self.domain}, ldap_server={self.ldap_server}")
    
    def _detect_domain(self) -> Optional[str]:
        """Detect the current Windows domain."""
        if not WIN32_AVAILABLE:
            return None
        
        try:
            # Get current user's domain
            username = win32api.GetUserNameEx(win32con.NameSamCompatible)
            if '\\' in username:
                return username.split('\\')[0]
            
            # Try to get domain from computer name
            computer_name = win32api.GetComputerNameEx(win32con.ComputerNameDnsDomain)
            if computer_name:
                return computer_name
            
            # Fallback: try environment variable
            domain = os.environ.get('USERDOMAIN')
            if domain:
                return domain
        except Exception:
            logging.exception("Failed to detect domain")
        
        return None
    
    def _get_ldap_server(self) -> Optional[str]:
        """Get LDAP server address from domain."""
        if not self.domain:
            return None
        
        # Try to construct LDAP server from domain
        # Common patterns: ldap://dc1.domain.com or ldap://domain.com
        domain_parts = self.domain.lower().split('.')
        if len(domain_parts) >= 2:
            # Try common DC naming
            dc_components = ','.join([f'DC={part}' for part in domain_parts])
            # Try to find DC (this is a heuristic; real implementation should query DNS)
            return f"ldap://{self.domain}"
        
        return None
    
    def connect(self) -> bool:
        """
        Establish connection to Active Directory.
        Returns True if successful.
        """
        if not LDAP3_AVAILABLE:
            logging.warning("LDAP3 not available. Cannot establish LDAP connection.")
            return False
        
        try:
            server = Server(self.ldap_server, get_info=ALL)
            
            if self.use_windows_auth and WIN32_AVAILABLE:
                # Use Windows Integrated Authentication (NTLM)
                try:
                    username = win32api.GetUserNameEx(win32con.NameSamCompatible)
                    self.connection = Connection(server, user=username, authentication=NTLM, auto_bind=True)
                    logging.info(f"Connected to AD using Windows Integrated Auth: {username}")
                    return True
                except Exception:
                    logging.warning("Windows Integrated Auth failed, falling back to simple bind")
            
            # Fallback to simple bind if credentials provided
            if self.bind_user and self.bind_password:
                bind_dn = self.bind_user
                if '\\' not in bind_dn and '@' not in bind_dn and self.domain:
                    bind_dn = f"{self.domain}\\{bind_dn}"
                
                self.connection = Connection(server, user=bind_dn, password=self.bind_password,
                                           authentication=SIMPLE, auto_bind=True)
                logging.info(f"Connected to AD using simple bind: {bind_dn}")
                return True
            
            logging.warning("No authentication method available for LDAP connection")
            return False
            
        except Exception:
            logging.exception("Failed to connect to Active Directory")
            return False
    
    def disconnect(self):
        """Close the LDAP connection."""
        if self.connection:
            try:
                self.connection.unbind()
            except Exception:
                pass
            self.connection = None
    
    def get_current_user(self) -> Optional[Dict[str, str]]:
        """
        Get information about the currently logged-in Windows user.
        Returns dict with user info or None.
        """
        if not WIN32_AVAILABLE:
            return None
        
        try:
            username = win32api.GetUserNameEx(win32con.NameSamCompatible)
            domain_user = username.split('\\') if '\\' in username else (None, username)
            domain, user = domain_user[0] if len(domain_user) > 1 else None, domain_user[-1]
            
            # Get user SID
            try:
                sid = win32security.LookupAccountName(None, username)[0]
                sid_string = win32security.ConvertSidToStringSid(sid)
            except Exception:
                sid_string = None
            
            user_info = {
                'username': user,
                'domain': domain or self.domain,
                'full_name': username,
                'sid': sid_string
            }
            
            self._current_user = user_info
            return user_info
            
        except Exception:
            logging.exception("Failed to get current user info")
            return None
    
    def authenticate_user(self, username: str, password: str) -> bool:
        """
        Authenticate a user against Active Directory.
        
        Args:
            username: Username (can be DOMAIN\\user or user@domain.com)
            password: Password
            
        Returns:
            True if authentication successful
        """
        if not LDAP3_AVAILABLE:
            logging.warning("LDAP3 not available for authentication")
            return False
        
        try:
            # Ensure we have a connection
            if not self.connection:
                if not self.connect():
                    return False
            
            # Format username for LDAP bind
            if '\\' not in username and '@' not in username and self.domain:
                bind_username = f"{self.domain}\\{username}"
            else:
                bind_username = username
            
            # Try to bind with provided credentials
            server = Server(self.ldap_server, get_info=ALL)
            test_conn = Connection(server, user=bind_username, password=password,
                                 authentication=SIMPLE, auto_bind=True)
            test_conn.unbind()
            logging.info(f"Successfully authenticated user: {username}")
            return True
            
        except Exception:
            logging.exception(f"Authentication failed for user: {username}")
            return False
    
    def get_user_groups(self, username: Optional[str] = None) -> List[str]:
        """
        Get list of AD groups for a user.
        
        Args:
            username: Username (optional, uses current user if not provided)
            
        Returns:
            List of group names
        """
        if not WIN32_AVAILABLE:
            return []
        
        try:
            if not username:
                # Get current user's groups
                if self._user_groups is not None:
                    return self._user_groups
                
                user_token = win32security.OpenProcessToken(
                    win32api.GetCurrentProcess(),
                    win32con.TOKEN_QUERY
                )
                
                groups = win32security.GetTokenInformation(
                    user_token,
                    win32security.TokenGroups
                )
                
                group_names = []
                for group in groups:
                    try:
                        account, domain, _ = win32security.LookupAccountSid(None, group[0])
                        # Include domain in group name if not current domain
                        if domain and domain.upper() != (self.domain or '').upper():
                            group_names.append(f"{domain}\\{account}")
                        else:
                            group_names.append(account)
                    except Exception:
                        continue
                
                self._user_groups = group_names
                return group_names
            else:
                # For other users, would need LDAP query
                if not self.connection:
                    if not self.connect():
                        return []
                
                # Search for user in AD
                search_base = self._get_search_base()
                search_filter = f"(&(objectClass=user)(sAMAccountName={username}))"
                
                self.connection.search(search_base, search_filter, attributes=['memberOf'])
                
                if self.connection.entries:
                    groups = []
                    for entry in self.connection.entries:
                        if hasattr(entry, 'memberOf'):
                            for group_dn in entry.memberOf.values:
                                # Extract CN from DN
                                cn = group_dn.split(',')[0].replace('CN=', '')
                                groups.append(cn)
                    return groups
                
                return []
                
        except Exception:
            logging.exception(f"Failed to get groups for user: {username or 'current user'}")
            return []
    
    def get_user_role(self, username: Optional[str] = None) -> Role:
        """
        Determine SEBAS role based on AD group membership.
        
        Args:
            username: Username (optional, uses current user if not provided)
            
        Returns:
            Role enum value
        """
        groups = self.get_user_groups(username)
        
        # Check role mapping
        for group, role in self.role_mapping.items():
            # Check both with and without domain prefix
            if group in groups or any(group in g for g in groups):
                logging.info(f"User {username or 'current'} mapped to role {role.name} via group {group}")
                return role
        
        # Default to STANDARD role
        return Role.STANDARD
    
    def lookup_user(self, username: str) -> Optional[Dict[str, str]]:
        """
        Look up user information in Active Directory.
        
        Args:
            username: Username to look up
            
        Returns:
            Dict with user attributes or None
        """
        if not self.connection:
            if not self.connect():
                return None
        
        try:
            search_base = self._get_search_base()
            search_filter = f"(&(objectClass=user)(sAMAccountName={username}))"
            
            attributes = ['cn', 'displayName', 'mail', 'department', 'title', 'telephoneNumber']
            self.connection.search(search_base, search_filter, attributes=attributes, search_scope=SUBTREE)
            
            if self.connection.entries:
                entry = self.connection.entries[0]
                return {
                    'username': username,
                    'display_name': str(entry.get('displayName', [''])[0]) if hasattr(entry, 'displayName') else '',
                    'email': str(entry.get('mail', [''])[0]) if hasattr(entry, 'mail') else '',
                    'department': str(entry.get('department', [''])[0]) if hasattr(entry, 'department') else '',
                    'title': str(entry.get('title', [''])[0]) if hasattr(entry, 'title') else '',
                    'phone': str(entry.get('telephoneNumber', [''])[0]) if hasattr(entry, 'telephoneNumber') else '',
                }
            
            return None
            
        except Exception:
            logging.exception(f"Failed to lookup user: {username}")
            return None
    
    def _get_search_base(self) -> str:
        """Get LDAP search base from domain."""
        if not self.domain:
            return ""
        
        domain_parts = self.domain.lower().split('.')
        return ','.join([f'DC={part}' for part in domain_parts])
    
    def set_role_mapping(self, group: str, role: Role):
        """Update role mapping for an AD group."""
        self.role_mapping[group] = role
        logging.info(f"Updated role mapping: {group} -> {role.name}")
    
    # Phase 2.1: User Account Management
    def create_user(self, username: str, password: str, display_name: Optional[str] = None,
                    email: Optional[str] = None, department: Optional[str] = None) -> Tuple[bool, str]:
        """
        Create a new user account in Active Directory.
        
        Args:
            username: Username (sAMAccountName)
            password: Initial password
            display_name: Display name (optional)
            email: Email address (optional)
            department: Department (optional)
            
        Returns:
            Tuple of (success, message)
        """
        if not LDAP3_AVAILABLE or not self.connection:
            if not self.connect():
                return False, "Cannot connect to Active Directory"
        
        try:
            search_base = self._get_search_base()
            user_dn = f"CN={display_name or username},CN=Users,{search_base}"
            
            # Create user object
            attributes = {
                'objectClass': ['top', 'person', 'organizationalPerson', 'user'],
                'sAMAccountName': username,
                'userPrincipalName': f"{username}@{self.domain}",
                'displayName': display_name or username,
                'userAccountControl': '512'  # Normal account
            }
            
            if email:
                attributes['mail'] = email
            if department:
                attributes['department'] = department
            
            # Add user
            self.connection.add(user_dn, attributes=attributes)
            
            if self.connection.result['result'] == 0:
                # Set password
                self.connection.extend.microsoft.modify_password(
                    user_dn,
                    new_password=password
                )
                
                # Enable account
                self.connection.modify(user_dn, {'userAccountControl': [('MODIFY_REPLACE', 512)]})
                
                logging.info(f"User {username} created successfully")
                return True, f"User {username} created successfully"
            else:
                error = self.connection.result.get('description', 'Unknown error')
                return False, f"Failed to create user: {error}"
                
        except Exception:
            logging.exception(f"Failed to create user: {username}")
            return False, "Failed to create user"
    
    def delete_user(self, username: str) -> Tuple[bool, str]:
        """
        Delete a user account from Active Directory.
        
        Args:
            username: Username to delete
            
        Returns:
            Tuple of (success, message)
        """
        if not LDAP3_AVAILABLE or not self.connection:
            if not self.connect():
                return False, "Cannot connect to Active Directory"
        
        try:
            # Find user DN
            search_base = self._get_search_base()
            search_filter = f"(&(objectClass=user)(sAMAccountName={username}))"
            
            self.connection.search(search_base, search_filter, attributes=['dn'])
            
            if not self.connection.entries:
                return False, f"User {username} not found"
            
            user_dn = str(self.connection.entries[0].entry_dn)
            
            # Delete user
            self.connection.delete(user_dn)
            
            if self.connection.result['result'] == 0:
                logging.info(f"User {username} deleted successfully")
                return True, f"User {username} deleted successfully"
            else:
                error = self.connection.result.get('description', 'Unknown error')
                return False, f"Failed to delete user: {error}"
                
        except Exception:
            logging.exception(f"Failed to delete user: {username}")
            return False, "Failed to delete user"
    
    def modify_user(self, username: str, attributes: Dict[str, str]) -> Tuple[bool, str]:
        """
        Modify user attributes.
        
        Args:
            username: Username to modify
            attributes: Dict of attributes to modify (e.g., {'displayName': 'New Name', 'mail': 'new@email.com'})
            
        Returns:
            Tuple of (success, message)
        """
        if not LDAP3_AVAILABLE or not self.connection:
            if not self.connect():
                return False, "Cannot connect to Active Directory"
        
        try:
            # Find user DN
            search_base = self._get_search_base()
            search_filter = f"(&(objectClass=user)(sAMAccountName={username}))"
            
            self.connection.search(search_base, search_filter, attributes=['dn'])
            
            if not self.connection.entries:
                return False, f"User {username} not found"
            
            user_dn = str(self.connection.entries[0].entry_dn)
            
            # Modify attributes
            changes = {}
            for key, value in attributes.items():
                changes[key] = [('MODIFY_REPLACE', value)]
            
            self.connection.modify(user_dn, changes)
            
            if self.connection.result['result'] == 0:
                logging.info(f"User {username} modified successfully")
                return True, f"User {username} modified successfully"
            else:
                error = self.connection.result.get('description', 'Unknown error')
                return False, f"Failed to modify user: {error}"
                
        except Exception:
            logging.exception(f"Failed to modify user: {username}")
            return False, "Failed to modify user"
    
    def get_password_policy(self) -> Optional[Dict[str, Any]]:
        """
        Get domain password policy.
        
        Returns:
            Dict with password policy information or None
        """
        if not LDAP3_AVAILABLE or not self.connection:
            if not self.connect():
                return None
        
        try:
            search_base = self._get_search_base()
            search_filter = "(&(objectClass=domainDNS)(objectClass=domain))"
            
            attributes = [
                'minPwdLength', 'maxPwdAge', 'minPwdAge', 'lockoutThreshold',
                'lockoutDuration', 'pwdHistoryLength', 'pwdProperties'
            ]
            
            self.connection.search(search_base, search_filter, attributes=attributes, search_scope=SUBTREE)
            
            if self.connection.entries:
                entry = self.connection.entries[0]
                policy = {}
                
                for attr in attributes:
                    if hasattr(entry, attr):
                        value = entry[attr].value if hasattr(entry[attr], 'value') else entry[attr]
                        policy[attr] = value
                
                return policy
            
            return None
            
        except Exception:
            logging.exception("Failed to get password policy")
            return None
    
    def available(self) -> bool:
        """Check if AD integration is available."""
        return (WIN32_AVAILABLE or LDAP3_AVAILABLE) and (self.domain is not None or self.ldap_server is not None)
