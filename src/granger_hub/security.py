"""
Granger Hub Security Middleware
Provides authentication, rate limiting, and security utilities.
"""

import time
import hashlib
import secrets
from typing import Dict, Any, Optional, Callable
from functools import wraps
from collections import defaultdict
from datetime import datetime, timedelta
import threading


class TokenValidator:
    """Validates authentication tokens for inter-module communication."""

    def __init__(self):
        self.valid_tokens = set()
        self._lock = threading.Lock()

    def generate_token(self, module_name: str) -> str:
        """Generate a secure token for a module."""
        token = f"granger_{module_name}_{secrets.token_urlsafe(32)}"
        with self._lock:
            self.valid_tokens.add(token)
        return token

    def validate_token(self, token: str) -> bool:
        """Validate an authentication token."""
        if not token or not isinstance(token, str):
            return False

        # Check if token follows expected format
        if not token.startswith("granger_"):
            return False

        with self._lock:
            return token in self.valid_tokens

    def revoke_token(self, token: str):
        """Revoke a token."""
        with self._lock:
            self.valid_tokens.discard(token)


class RateLimiter:
    """Implements rate limiting for API endpoints."""

    def __init__(self, max_requests: int = 100, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests = defaultdict(list)
        self._lock = threading.Lock()

    def is_allowed(self, identifier: str) -> bool:
        """Check if request is allowed under rate limit."""
        now = time.time()
        with self._lock:
            # Clean old entries
            self.requests[identifier] = [
                req_time for req_time in self.requests[identifier]
                if now - req_time < self.window_seconds
            ]
            
            # Check rate limit
            if len(self.requests[identifier]) >= self.max_requests:
                return False
            
            # Record new request
            self.requests[identifier].append(now)
            return True


class SQLProtection:
    """Provides SQL injection protection utilities."""
    
    DANGEROUS_PATTERNS = [
        "union", "select", "insert", "update", "delete", "drop",
        "exec", "execute", "script", "--", "/*", "*/", "xp_", "sp_"
    ]
    
    @classmethod
    def sanitize(cls, value: str) -> str:
        """Sanitize input to prevent SQL injection."""
        if not isinstance(value, str):
            return str(value)
            
        # Convert to lowercase for checking
        lower_value = value.lower()
        
        # Check for dangerous patterns
        for pattern in cls.DANGEROUS_PATTERNS:
            if pattern in lower_value:
                # Remove the pattern
                value = value.replace(pattern, "")
                value = value.replace(pattern.upper(), "")
                value = value.replace(pattern.capitalize(), "")
        
        # Remove special characters
        value = value.replace("'", "''")  # Escape single quotes
        value = value.replace('"', '""')  # Escape double quotes
        value = value.replace("\\", "\\\\")  # Escape backslashes
        
        return value


def secure_endpoint(func: Callable) -> Callable:
    """Decorator that applies security measures to an endpoint."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        # Add security headers to response if possible
        result = func(*args, **kwargs)
        
        if isinstance(result, dict) and "_headers" not in result:
            result["_headers"] = {
                "X-Content-Type-Options": "nosniff",
                "X-Frame-Options": "DENY",
                "X-XSS-Protection": "1; mode=block",
                "Strict-Transport-Security": "max-age=31536000; includeSubDomains"
            }
        
        return result
    return wrapper


def require_auth(validator: Optional[TokenValidator] = None) -> Callable:
    """Decorator that requires authentication."""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Try to get token from kwargs or first arg
            token = kwargs.get("auth_token")
            if not token and args and isinstance(args[0], dict):
                token = args[0].get("auth_token")
            
            # Use provided validator or global one
            token_validator_instance = validator or token_validator
            
            if not token or not token_validator_instance.validate_token(token):
                raise PermissionError("Invalid or missing authentication token")
            
            return func(*args, **kwargs)
        return wrapper
    return decorator


def rate_limit(limiter: Optional[RateLimiter] = None, identifier_func: Optional[Callable] = None) -> Callable:
    """Decorator that applies rate limiting."""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Get identifier
            if identifier_func:
                identifier = identifier_func(*args, **kwargs)
            else:
                # Default: use first string arg or "default"
                identifier = "default"
                for arg in args:
                    if isinstance(arg, str):
                        identifier = arg
                        break
            
            # Use provided limiter or global one
            rate_limiter_instance = limiter or rate_limiter
            
            if not rate_limiter_instance.is_allowed(identifier):
                raise Exception("Rate limit exceeded")
            
            return func(*args, **kwargs)
        return wrapper
    return decorator


# Create global instances
token_validator = TokenValidator()
rate_limiter = RateLimiter()
sql_protection = SQLProtection()


# Export all public items
__all__ = [
    "TokenValidator",
    "RateLimiter", 
    "SQLProtection",
    "secure_endpoint",
    "require_auth",
    "rate_limit",
    "token_validator",
    "rate_limiter",
    "sql_protection"
]