# Fixture: a third-party import.
import json
import requests

print(json.dumps({"ok": requests is not None}))
