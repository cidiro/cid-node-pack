"""Test configuration for the cid-node-pack test suite.

pytest (9+) treats the repository root as a package because it contains an
``__init__.py``, and imports that file as a bare ``__init__`` module during
test setup (the folder name ``cid-node-pack`` is not a valid module name).
The pack's relative imports cannot resolve in that context. Pre-register a
stub module so the import is a no-op; ComfyUI imports the pack as a proper
package and is unaffected.
"""

import sys
import types

if "__init__" not in sys.modules:
    stub = types.ModuleType("__init__")
    stub.__file__ = str(__file__).replace("conftest.py", "__init__.py")
    sys.modules["__init__"] = stub
