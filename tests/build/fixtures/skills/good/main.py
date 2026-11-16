# Fixture skill entrypoint: stdlib imports only.
import json
import importlib.util
from pathlib import Path


def ping():
    print(json.dumps({"ok": True}))


ping()
