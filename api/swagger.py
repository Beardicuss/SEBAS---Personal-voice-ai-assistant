# -*- coding: utf-8 -*-
"""
OpenAPI/Swagger Documentation
Phase 1.3.6: API Documentation
"""

from sebas.flask import Blueprint, jsonify
from typing import Dict, Any


def create_swagger_spec() -> Dict[str, Any]:
    """
    Generate OpenAPI/Swagger specification for SEBAS API.
    
    Returns:
        OpenAPI specification dictionary
    """
    spec = {
        "openapi": "3.0.0",
        "info": {
            "title": "SEBAS API",
            "description": "SEBAS Personal Voice AI Assistant API",
            "version": "1.0.0",
            "contact": {
                "name": "SEBAS Development Team"
            }
        },
        "servers": [
            {
                "url": "http://127.0.0.1:5001",
                "description": "Development server"
            }
        ],
        "paths": {
            "/api/v1/health": {
                "get": {
                    "summary": "Health check",
                    "description": "Check API health status",
                    "responses": {
                        "200": {
                            "description": "Service is healthy",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "status": {"type": "string", "example": "ok"},
                                            "service": {"type": "string", "example": "sebas-api"},
                                            "version": {"type": "string", "example": "1.0"}
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            },
            "/api/v1/status": {
                "get": {
                    "summary": "Get system status",
                    "description": "Get current system status and authentication info",
                    "security": [{"ApiKeyAuth": []}, {"BearerAuth": []}],
                    "responses": {
                        "200": {
                            "description": "Status information",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "version": {"type": "string"},
                                            "status": {"type": "string"},
                                            "authenticated": {"type": "boolean"},
                                            "role": {"type": "string"}
                                        }
                                    }
                                }
                            }
                        },
                        "401": {"description": "Unauthorized"}
                    }
                }
            },
            "/api/v1/commands": {
                "post": {
                    "summary": "Execute a command",
                    "description": "Execute a voice command through SEBAS",
                    "security": [{"ApiKeyAuth": []}, {"BearerAuth": []}],
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "required": ["command"],
                                    "properties": {
                                        "command": {
                                            "type": "string",
                                            "description": "Command to execute",
                                            "example": "open notepad"
                                        }
                                    }
                                }
                            }
                        }
                    },
                    "responses": {
                        "200": {
                            "description": "Command executed successfully",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "status": {"type": "string", "example": "success"},
                                            "message": {"type": "string"},
                                            "command": {"type": "string"}
                                        }
                                    }
                                }
                            }
                        },
                        "400": {"description": "Bad request"},
                        "401": {"description": "Unauthorized"},
                        "500": {"description": "Internal server error"}
                    }
                }
            },
            "/api/v1/system": {
                "get": {
                    "summary": "Get system information",
                    "description": "Get system resource information",
                    "security": [{"ApiKeyAuth": []}, {"BearerAuth": []}],
                    "responses": {
                        "200": {
                            "description": "System information",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "platform": {"type": "string"},
                                            "cpu_count": {"type": "integer"},
                                            "cpu_percent": {"type": "number"},
                                            "memory": {
                                                "type": "object",
                                                "properties": {
                                                    "total": {"type": "integer"},
                                                    "available": {"type": "integer"},
                                                    "percent": {"type": "number"}
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                        },
                        "401": {"description": "Unauthorized"}
                    }
                }
            },
            "/api/v1/auth/keys": {
                "post": {
                    "summary": "Create API key",
                    "description": "Generate a new API key (Admin only)",
                    "security": [{"ApiKeyAuth": []}, {"BearerAuth": []}],
                    "requestBody": {
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "role": {
                                            "type": "string",
                                            "enum": ["STANDARD", "ADMIN"],
                                            "default": "STANDARD"
                                        }
                                    }
                                }
                            }
                        }
                    },
                    "responses": {
                        "201": {
                            "description": "API key created",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "status": {"type": "string"},
                                            "api_key": {"type": "string"},
                                            "role": {"type": "string"}
                                        }
                                    }
                                }
                            }
                        },
                        "403": {"description": "Forbidden - Admin role required"}
                    }
                }
            },
            "/api/v1/auth/token": {
                "post": {
                    "summary": "Generate JWT token",
                    "description": "Generate a JWT token for authentication",
                    "security": [{"ApiKeyAuth": []}, {"BearerAuth": []}],
                    "responses": {
                        "200": {
                            "description": "Token generated",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "token": {"type": "string"},
                                            "type": {"type": "string", "example": "Bearer"},
                                            "expires_in": {"type": "integer"}
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        },
        "components": {
            "securitySchemes": {
                "ApiKeyAuth": {
                    "type": "apiKey",
                    "in": "header",
                    "name": "X-API-Key"
                },
                "BearerAuth": {
                    "type": "http",
                    "scheme": "bearer",
                    "bearerFormat": "JWT"
                }
            }
        }
    }
    
    return spec


def register_swagger_routes(app):
    """
    Register Swagger/OpenAPI documentation routes.
    
    Args:
        app: Flask application
    """
    @app.route('/api/docs', methods=['GET'])
    def swagger_ui():
        """Swagger UI page."""
        return """
<!DOCTYPE html>
<html>
<head>
    <title>SEBAS API Documentation</title>
    <link rel="stylesheet" type="text/css" href="https://unpkg.com/swagger-ui-dist@3.25.0/swagger-ui.css" />
</head>
<body>
    <div id="swagger-ui"></div>
    <script src="https://unpkg.com/swagger-ui-dist@3.25.0/swagger-ui-bundle.js"></script>
    <script>
        window.onload = function() {
            SwaggerUIBundle({
                url: "/api/swagger.json",
                dom_id: '#swagger-ui'
            });
        };
    </script>
</body>
</html>
        """
    
    @app.route('/api/swagger.json', methods=['GET'])
    def swagger_json():
        """OpenAPI specification JSON."""
        return jsonify(create_swagger_spec())
    
    @app.route('/api/openapi.json', methods=['GET'])
    def openapi_json():
        """OpenAPI specification JSON (alias)."""
        return swagger_json()
