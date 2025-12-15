#!/usr/bin/env python3
"""
Patch Dynamo nixl_connect/__init__.py to read NIXL_BACKEND environment variable.

Problem:
    Dynamo's nixl_connect creates NIXL agent with default config, which uses UCX backend.
    Even when NIXL_BACKEND=LIBFABRIC is set, the agent ignores it.

Solution:
    Replace the nixl_agent initialization to read NIXL_BACKEND env var and configure
    the agent with the appropriate backend.

Usage:
    python3 patch_nixl_connect.py /path/to/nixl_connect/__init__.py
"""

import sys
import re


def patch_file(filepath: str) -> bool:
    """Patch the nixl_connect __init__.py file."""

    # The old code we're looking for
    old_code = "self._nixl = nixl_api.nixl_agent(self._worker_id)"

    # The new code that reads NIXL_BACKEND env var
    new_code = '''# LIBFABRIC PATCH: Read NIXL_BACKEND env var and configure agent
        import os as _nixl_os
        _nixl_backend = _nixl_os.environ.get('NIXL_BACKEND', 'UCX')
        _backends = [_nixl_backend] if _nixl_backend != 'UCX' else ['UCX']
        logger.info(f"NIXL Connect: Using backend(s): {_backends}")
        _nixl_config = nixl_api.nixl_agent_config(backends=_backends)
        self._nixl = nixl_api.nixl_agent(self._worker_id, _nixl_config)'''

    # Read the file
    with open(filepath, 'r') as f:
        content = f.read()

    # Check if already patched
    if "LIBFABRIC PATCH" in content:
        print(f"File already patched: {filepath}")
        return True

    # Check if the target code exists
    if old_code not in content:
        print(f"ERROR: Could not find target code to patch in {filepath}")
        print(f"Looking for: {old_code}")
        return False

    # Replace the code
    new_content = content.replace(old_code, new_code)

    # Write the patched file
    with open(filepath, 'w') as f:
        f.write(new_content)

    print(f"SUCCESS: Patched {filepath}")
    print(f"Changed:")
    print(f"  {old_code}")
    print(f"To:")
    print(new_code)

    return True


def main():
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <path-to-nixl_connect/__init__.py>")
        sys.exit(1)

    filepath = sys.argv[1]

    if not patch_file(filepath):
        sys.exit(1)


if __name__ == "__main__":
    main()
