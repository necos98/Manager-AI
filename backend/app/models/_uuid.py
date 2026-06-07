"""Shared UUID generation for model default values."""
import uuid


def new_uuid() -> str:
    return str(uuid.uuid4())
