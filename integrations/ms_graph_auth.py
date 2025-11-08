# -*- coding: utf-8 -*-
"""
Microsoft Graph OAuth Helper (Device Code Flow)

- Uses public client Device Code Flow; no secret required.
- Caches token and refresh token in ~/.sebas_ms_graph_token.json
-
Env:
  MS_GRAPH_CLIENT_ID   (required)
  MS_GRAPH_TENANT      (optional, default 'common')
  MS_GRAPH_SCOPES      (optional, comma-separated; default Calendars.ReadWrite, offline_access)
"""

import os
import time
import json
import webbrowser
from typing import Dict, Tuple, Optional, List
import requests


CACHE_PATH = os.path.join(os.path.expanduser('~'), '.sebas_ms_graph_token.json')


def _now() -> int:
	return int(time.time())


def _load_cache() -> Dict:
	if os.path.isfile(CACHE_PATH):
		try:
			with open(CACHE_PATH, 'r', encoding='utf-8') as f:
				return json.load(f)
		except Exception:
			return {}
	return {}


def _save_cache(data: Dict) -> None:
	try:
		with open(CACHE_PATH, 'w', encoding='utf-8') as f:
			json.dump(data, f, ensure_ascii=False, indent=2)
	except Exception:
		pass


def _scopes_from_env() -> List[str]:
	val = os.environ.get('MS_GRAPH_SCOPES')
	if val:
		return [s.strip() for s in val.split(',') if s.strip()]
	# Minimum for calendar write + refresh
	return ['Calendars.ReadWrite', 'offline_access']


def _tenant_from_env() -> str:
	return os.environ.get('MS_GRAPH_TENANT', 'common')


def _client_id_from_env() -> Optional[str]:
	return os.environ.get('MS_GRAPH_CLIENT_ID')


def _device_code_flow(scopes: List[str]) -> Optional[Dict]:
	client_id = _client_id_from_env()
	if not client_id:
		return None
	tenant = _tenant_from_env()
	device_url = f'https://login.microsoftonline.com/{tenant}/oauth2/v2.0/devicecode'
	token_url = f'https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token'
	data = {
		'client_id': client_id,
		'scope': ' '.join(scopes)
	}
	r = requests.post(device_url, data=data, timeout=15)
	if r.status_code != 200:
		return None
	info = r.json()
	verification_uri = info.get('verification_uri') or info.get('verification_uri_complete')
	user_code = info.get('user_code')
	device_code = info.get('device_code')
	interval = int(info.get('interval', 5))
	expires_in = int(info.get('expires_in', 900))
	# Prompt user
	try:
		if verification_uri:
			webbrowser.open(verification_uri)
	except Exception:
		pass
	print(f"Microsoft sign-in: Go to {verification_uri} and enter code: {user_code}")

	# Poll token endpoint
	start = _now()
	while _now() - start < expires_in:
		poll = {
			'grant_type': 'urn:ietf:params:oauth:grant-type:device_code',
			'client_id': client_id,
			'device_code': device_code,
		}
		tr = requests.post(token_url, data=poll, timeout=15)
		if tr.status_code == 200:
			return tr.json()
			
		try:
			err = tr.json()
			if err.get('error') in ('authorization_pending', 'slow_down'):
				time.sleep(interval)
				continue
		except Exception:
			pass
		time.sleep(interval)
	return None


def _refresh_token(refresh_token: str, scopes: List[str]) -> Optional[Dict]:
	client_id = _client_id_from_env()
	if not client_id:
		return None
	tenant = _tenant_from_env()
	token_url = f'https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token'
	data = {
		'grant_type': 'refresh_token',
		'client_id': client_id,
		'refresh_token': refresh_token,
		'scope': ' '.join(scopes)
	}
	r = requests.post(token_url, data=data, timeout=15)
	if r.status_code == 200:
		return r.json()
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

	# Try refresh
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

	# Start device code flow
	res = _device_code_flow(scopes)
	if res and res.get('access_token'):
		cache.update({
			'access_token': res.get('access_token'),
			'refresh_token': res.get('refresh_token'),
			'expires_at': _now() + int(res.get('expires_in', 3600))
		})
		_save_cache(cache)
		return True, cache['access_token']

	return False, None


