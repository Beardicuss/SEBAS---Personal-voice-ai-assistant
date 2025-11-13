# -*- coding: utf-8 -*-
"""
Active Directory Integration Client
Phase 2: Active Directory Integration
"""

import logging
import os
import platform
from sebas.typing import Optional, Dict, List, Tuple, Any
from sebas.constants.permissions import Role

# Try to import LDAP3 for LDAP operations
try:
    from sebas.ldap3 import Server, Connection, ALL, NTLM, SIMPLE, SUBTREE
    LDAP3_AVAILABLE = True
except ImportError:
    LDAP3_AVAILABLE = False
    logging.warning("ldap3 not available. AD integration will be limited.")

# Try to import Windows security modules
try:
    import win32security
    import win32api
    import win32con
    WIN32_AVAILABLE = True
except ImportError:
    WIN32_AVAILABLE = False
    logging.warning("pywin32 not available. Windows Integrated Auth disabled.")


class ADClient:
    """
    Active Directory client for authentication and user management.
    Supports both LDAP-based and Windows Integrated Authentication.
    """

    def __init__(self, domain: Optional[str] = None, ldap_server: Optional[str] = None,
                 use_windows_auth: bool = True, bind_user: Optional[str] = None,
                 bind_password: Optional[str] = None):
        self.domain = domain or self._detect_domain()
        self.ldap_server = ldap_server or self._get_ldap_server()
        self.use_windows_auth = use_windows_auth and WIN32_AVAILABLE
        self.bind_user = bind_user
        self.bind_password = bind_password
        self.connection = None
        self._current_user = None
        self._user_groups = None

        self.role_mapping = {
            'Domain Admins': Role.ADMIN,
            'Enterprise Admins': Role.ADMIN,
            'Schema Admins': Role.ADMIN,
            'Administrators': Role.ADMIN,
        }

        logging.info(f"ADClient initialized: domain={self.domain}, ldap_server={self.ldap_server}")

    # -------- Utility and connection handling -------- #

    def _detect_domain(self) -> Optional[str]:
        """Detect current Windows domain."""
        if not WIN32_AVAILABLE:
            return None
        try:
            username = win32api.GetUserNameEx(win32con.NameSamCompatible)
            if '\\' in username:
                return username.split('\\')[0]
            computer_name = win32api.GetComputerNameEx(win32con.ComputerNameDnsDomain)
            if computer_name:
                return computer_name
            return os.environ.get('USERDOMAIN')
        except Exception:
            logging.exception("Failed to detect domain")
            return None

    def _get_ldap_server(self) -> Optional[str]:
        """Construct LDAP server from domain name."""
        if not self.domain:
            return None
        try:
            return f"ldap://{self.domain}"
        except Exception:
            return None

    def connect(self) -> bool:
        """Connect to Active Directory via LDAP or Windows Auth."""
        if not LDAP3_AVAILABLE:
            logging.warning("LDAP3 not available.")
            return False
        try:
            server = Server(str(self.ldap_server), get_info=ALL)
            if self.use_windows_auth and WIN32_AVAILABLE:
                username = win32api.GetUserNameEx(win32con.NameSamCompatible)
                self.connection = Connection(server, user=username, authentication=NTLM, auto_bind=True)
                logging.info(f"Connected via Windows Auth: {username}")
                return True
            if self.bind_user and self.bind_password:
                bind_dn = self.bind_user
                if '\\' not in bind_dn and '@' not in bind_dn and self.domain:
                    bind_dn = f"{self.domain}\\{bind_dn}"
                self.connection = Connection(server, user=bind_dn, password=self.bind_password,
                                             authentication=SIMPLE, auto_bind=True)
                logging.info(f"Connected via simple bind: {bind_dn}")
                return True
            logging.warning("No authentication method available for LDAP connection")
            return False
        except Exception:
            logging.exception("Failed to connect to Active Directory")
            return False

    def disconnect(self):
        """Close LDAP connection."""
        try:
            if self.connection:
                self.connection.unbind()
        except Exception:
            pass
        finally:
            self.connection = None

    # -------- User management and authentication -------- #

    def get_current_user(self) -> Optional[Dict[str, str]]:
        """Get current logged-in user (Windows)."""
        if not WIN32_AVAILABLE:
            return None
        try:
            username = win32api.GetUserNameEx(win32con.NameSamCompatible)
            domain, user = username.split('\\') if '\\' in username else (self.domain, username)
            sid = None
            try:
                sid_obj = win32security.LookupAccountName(None, username)[0]
                sid = win32security.ConvertSidToStringSid(sid_obj)
            except Exception:
                pass
            self._current_user = {'username': user, 'domain': domain, 'full_name': username, 'sid': sid}
            return self._current_user
        except Exception:
            logging.exception("Failed to get current user info")
            return None

    def authenticate_user(self, username: str, password: str) -> bool:
        """Authenticate user credentials."""
        if not LDAP3_AVAILABLE:
            return False
        try:
            server = Server(str(self.ldap_server), get_info=ALL)
            bind_username = username
            if '\\' not in username and '@' not in username and self.domain:
                bind_username = f"{self.domain}\\{username}"
            test_conn = Connection(server, user=bind_username, password=password,
                                   authentication=SIMPLE, auto_bind=True)
            test_conn.unbind()
            logging.info(f"Authenticated: {username}")
            return True
        except Exception:
            logging.exception(f"Authentication failed for user: {username}")
            return False

        # -------- Additional helper methods for SEBAS integration -------- #

    def available(self) -> bool:
        """Check whether Active Directory integration is functional."""
        # Simple heuristic: either LDAP or Windows API must be working
        return WIN32_AVAILABLE or LDAP3_AVAILABLE

    def get_user_groups(self) -> List[str]:
        """Return cached or dummy user group list."""
        if self._user_groups:
            return self._user_groups
        try:
            # Placeholder group detection
            groups = ["Users"]
            user = self.get_current_user()
            if user and "Admin" in user.get("username", ""):
                groups.append("Administrators")

            self._user_groups = groups
            return groups
        except Exception:
            logging.exception("Failed to get user groups")
            return ["Users"]

    def get_user_role(self) -> Role:
        """Return user role based on mapped groups."""
        groups = self.get_user_groups()
        for group, role in self.role_mapping.items():
            if group in groups:
                return role
        return Role.STANDARD

    def set_role_mapping(self, group_name: str, role: Role):
        """Assign a specific role mapping to a domain group."""
        try:
            self.role_mapping[group_name] = role
            logging.info(f"Role mapping set: {group_name} -> {role}")
        except Exception:
            logging.exception("Failed to set role mapping")

    def lookup_user(self, username: str) -> Optional[Dict[str, Any]]:
        """Look up a user in AD (placeholder or LDAP search)."""
        if not username:
            return None
        try:
            if LDAP3_AVAILABLE and self.connection:
                self.connection.search(
                    search_base=f"DC={self.domain},DC=local" if self.domain else "",
                    search_filter=f"(sAMAccountName={username})",
                    search_scope=SUBTREE,
                    attributes=["sAMAccountName", "mail", "displayName"]
                )
                if self.connection.entries:
                    entry = self.connection.entries[0]
                    return {
                        "username": str(entry.sAMAccountName),
                        "email": str(entry.mail) if hasattr(entry, "mail") else None,
                        "display_name": str(entry.displayName) if hasattr(entry, "displayName") else None
                    }
            # fallback dummy data
            return {"username": username, "email": f"{username}@{self.domain or 'local'}"}
        except Exception:
            logging.exception(f"Failed to lookup user: {username}")
            return None
