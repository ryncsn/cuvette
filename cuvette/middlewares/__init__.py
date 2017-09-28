"""
All needed middlewares are imported here
"""

from .magic import middleware as magic_middleware
from .exception import middleware as exception_middleware

Middlewares = [magic_middleware, exception_middleware]
