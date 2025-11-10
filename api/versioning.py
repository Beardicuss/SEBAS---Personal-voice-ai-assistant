# -*- coding: utf-8 -*-
"""
API Versioning Support
"""

from enum import Enum
from typing import Optional
from flask import request


class APIVersion(Enum):
    """API version enumeration"""
    V1 = "v1"
    V2 = "v2"
    LATEST = "v1"  # Default to v1 for now


def get_api_version() -> APIVersion:
    """
    Extract API version from request.
    Checks Accept header, URL path, or query parameter.
    
    Returns:
        APIVersion enum value
    """
    # Check URL path (e.g., /api/v1/status)
    path = request.path if request else ""
    if "/v1/" in path:
        return APIVersion.V1
    if "/v2/" in path:
        return APIVersion.V2
    
    # Check Accept header (e.g., application/vnd.sebas.v1+json)
    accept = request.headers.get("Accept", "") if request else ""
    if "vnd.sebas.v2" in accept:
        return APIVersion.V2
    if "vnd.sebas.v1" in accept:
        return APIVersion.V1
    
    # Check query parameter (e.g., ?version=v1)
    version_param = request.args.get("version", "") if request else ""
    if version_param:
        try:
            return APIVersion(version_param.lower())
        except ValueError:
            pass
    
    # Default to latest
    return APIVersion.LATEST


def version_route(version: APIVersion):
    """
    Decorator to mark a route as belonging to a specific API version.
    
    Args:
        version: API version for this route
    """
    def decorator(func):
        func._api_version = version
        return func
    return decorator