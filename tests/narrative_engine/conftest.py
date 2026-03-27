"""Test configuration — resolve app/ vs app.py conflict."""
import sys
import os

# Ensure the app/ package takes priority over app.py
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root in sys.path:
    sys.path.remove(project_root)

# Remove any cached 'app' module
for key in list(sys.modules.keys()):
    if key == 'app' or key.startswith('app.'):
        del sys.modules[key]
