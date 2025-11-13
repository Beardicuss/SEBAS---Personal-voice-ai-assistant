# -*- coding: utf-8 -*-
"""
Microsoft Graph OAuth Helper (Device Code Flow)
Handles token caching, refresh, and device flow auth for Microsoft Graph.

Env vars:
  MS_GRAPH_CLIENT_ID   (required)
  MS_GRAPH_TENANT      (optional, default 'common')
  MS_GRAPH_SCOPES      (optional, comma-separated)
"""
import os
import time
import json
import logging
import webbrowser
import requests
from sebas.typing import Dict, Tuple, Optional, List

CACHE_PATH = os.path.join(os.path.expanduser('~'), '.sebas_ms_graph_token.json')


def _now() -> int:
    return int(time.time())


def _load_cache() -> Dict:
    if os.path.isfile(CACHE_PATH):
        try:
            with open(CACHE_PATH, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            logging.exception("[ms_graph_auth] Failed to load cache file")
            return {}
    return {}


def _save_cache(data: Dict) -> None:
    try:
        with open(CACHE_PATH, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        logging.info(f"[ms_graph_auth] Token cache saved at {CACHE_PATH}")
    except Exception:
        logging.exception("[ms_graph_auth] Failed to save token cache")


def _scopes_from_env() -> List[str]:
    val = os.environ.get('MS_GRAPH_SCOPES')
    if val:
        return [s.strip() for s in val.split(',') if s.strip()]
    return ['Calendars.ReadWrite', 'offline_access']


def _tenant_from_env() -> str:
    return os.environ.get('MS_GRAPH_TENANT', 'common')


def _client_id_from_env() -> Optional[str]:
    return os.environ.get('MS_GRAPH_CLIENT_ID')


def _device_code_flow(scopes: List[str]) -> Optional[Dict]:
    """Perform device code flow for user login."""
    client_id = _client_id_from_env()
    if not client_id:
        logging.error("[ms_graph_auth] MS_GRAPH_CLIENT_ID not set")
        return None

    tenant = _tenant_from_env()
    device_url = f'https://login.microsoftonline.com/{tenant}/oauth2/v2.0/devicecode'
    token_url = f'https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token'
    data = {'client_id': client_id, 'scope': ' '.join(scopes)}

    try:
        r = requests.post(device_url, data=data, timeout=15)
        if r.status_code != 200:
            logging.error(f"[ms_graph_auth] Device code request failed: {r.status_code}")
            return None

        info = r.json()
        verification_uri = info.get('verification_uri') or info.get('verification_uri_complete')
        user_code = info.get('user_code')
        device_code = info.get('device_code')
        interval = int(info.get('interval', 5))
        expires_in = int(info.get('expires_in', 900))

        msg = f"Microsoft sign-in: visit {verification_uri} and enter code: {user_code}"
        logging.info(msg)
        try:
            webbrowser.open(verification_uri)
        except Exception:
            pass
        print(msg)  # safe fallback if interactive

        start = _now()
        while _now() - start < expires_in:
            poll = {
                'grant_type': 'urn:ietf:params:oauth:grant-type:device_code',
                'client_id': client_id,
                'device_code': device_code,
            }
            tr = requests.post(token_url, data=poll, timeout=15)
            if tr.status_code == 200:
                logging.info("[ms_graph_auth] Device code flow succeeded")
                return tr.json()

            try:
                err = tr.json()
                if err.get('error') in ('authorization_pending', 'slow_down'):
                    time.sleep(interval)
                    continue
            except Exception:
                pass
            time.sleep(interval)
        logging.warning("[ms_graph_auth] Device code flow expired before completion")
        return None
    except requests.RequestException as e:
        logging.exception("[ms_graph_auth] Network error during device code flow")
        return None
    except Exception:
        logging.exception("[ms_graph_auth] Unexpected error during device code flow")
        return None


def _refresh_token(refresh_token: str, scopes: List[str]) -> Optional[Dict]:
    """Use refresh token to obtain a new access token."""
    client_id = _client_id_from_env()
    if not client_id:
        logging.error("[ms_graph_auth] MS_GRAPH_CLIENT_ID not set for refresh")
        return None

    tenant = _tenant_from_env()
    token_url = f'https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token'
    data = {
        'grant_type': 'refresh_token',
        'client_id': client_id,
        'refresh_token': refresh_token,
        'scope': ' '.join(scopes)
    }

    try:
        r = requests.post(token_url, data=data, timeout=15)
        if r.status_code == 200:
            logging.info("[ms_graph_auth] Token successfully refreshed")
            return r.json()
        logging.warning(f"[ms_graph_auth] Token refresh failed: {r.status_code}")
        return None
    except requests.RequestException as e:
        logging.exception("[ms_graph_auth] Network error during token refresh")
        return None
    except Exception:
        logging.exception("[ms_graph_auth] Unexpected error during token refresh")
        return None


def get_access_token(scopes: Optional[List[str]] = None) -> Tuple[bool, Optional[str]]:
    """Get a valid access token, refreshing or launching device code flow as needed."""
    scopes = scopes or _scopes_from_env()
    cache = _load_cache()

    access_token = cache.get('access_token')
    refresh_token = cache.get('refresh_token')
    expires_at = cache.get('expires_at', 0)

    if access_token and _now() < int(expires_at) - 60:
        return True, access_token

    # Try refresh token first
    if refresh_token:
        res = _refresh_token(refresh_token, scopes)
        if res and res.get('access_token'):
            cache.update({
                'access_token': res.get('access_token'),
                'refresh_token': res.get('refresh_token', refresh_token),
                'expires_at': _now() + int(res.get('expires_in', 3600))
            })
            _save_cache(cache)
            return True, cache['access_token']

    # No valid token — start device flow
    res = _device_code_flow(scopes)
    if res and res.get('access_token'):
        cache.update({
            'access_token': res.get('access_token'),
            'refresh_token': res.get('refresh_token'),
            'expires_at': _now() + int(res.get('expires_in', 3600))
        })
        _save_cache(cache)
        return True, cache['access_token']

    logging.error("[ms_graph_auth] Failed to acquire any valid access token")
    return False, None