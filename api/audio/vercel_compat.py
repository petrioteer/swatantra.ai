"""
Vercel compatibility module to handle asyncio issues in the Vercel environment.

This module provides compatibility functions to deal with the 'async' keyword issue
that may occur in certain versions of Python on Vercel.
"""
import sys
import os
import functools
import asyncio

# Detect if we're running in a Vercel environment
IN_VERCEL = 'VERCEL' in os.environ or 'AWS_REGION' in os.environ

# Patch asyncio if needed
def ensure_future_compat(coro_or_future):
    """
    Compatibility wrapper for asyncio.ensure_future that works in different Python versions
    and environments. This addresses the issue with 'async' being a reserved keyword.
    """
    try:
        # Try the standard way first
        return asyncio.ensure_future(coro_or_future)
    except (SyntaxError, AttributeError):
        # Fall back to create_task if available (modern Python)
        loop = asyncio.get_event_loop()
        return loop.create_task(coro_or_future)

# Create a compatible task creation function
def create_task_compat(coro):
    """
    Compatibility wrapper for creating tasks that works in different Python versions
    and environments.
    """
    try:
        # Try the standard way first
        return asyncio.create_task(coro)
    except (SyntaxError, AttributeError):
        # Fall back to ensure_future
        loop = asyncio.get_event_loop()
        return loop.create_task(coro)

# Patch run method in base class to use the compatible functions
def patch_asyncio_methods():
    """
    Monkey patch asyncio methods that might use 'async' as a function name
    to use our compatible versions instead.
    """
    if not hasattr(asyncio, 'ensure_future_original') and hasattr(asyncio, 'ensure_future'):
        asyncio.ensure_future_original = asyncio.ensure_future
        asyncio.ensure_future = ensure_future_compat
    
    # Add compat functions to the module
    asyncio.create_task_compat = create_task_compat

# Apply patches if we're in the Vercel environment
if IN_VERCEL:
    patch_asyncio_methods()