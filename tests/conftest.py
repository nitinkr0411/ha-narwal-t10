"""Make the standalone narwal_client package importable in tests."""

import pathlib
import sys

_COMPONENT = pathlib.Path(__file__).resolve().parents[1] / "custom_components" / "narwal_t10"
sys.path.insert(0, str(_COMPONENT))
