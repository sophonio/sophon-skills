"""File-name slugs for exported reports."""

import re


def slugify(text):
    lowered = text.strip().lower().replace(" ", "-")
    return re.sub(r"[^a-z0-9-]", "", lowered)
