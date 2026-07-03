"""Pulumi component library for managing TrueNAS apps and filesystem resources.

Public API:

    import pulumi_truenas as truenas

    truenas.CatalogApp(...)
    truenas.CustomApp(...)
    truenas.Dataset(...)
    truenas.Directory(...)

Connection settings are supplied per resource (host, transport, credentials).
A first-class ``Provider`` component is introduced in a later phase.
"""

from __future__ import annotations

from pulumi_truenas.provider import Provider
from pulumi_truenas.resources import (
    CatalogApp,
    CatalogAppArgs,
    CustomApp,
    CustomAppArgs,
    Dataset,
    DatasetArgs,
    Directory,
    DirectoryArgs,
)

__all__ = [
    "CatalogApp",
    "CatalogAppArgs",
    "CustomApp",
    "CustomAppArgs",
    "Dataset",
    "DatasetArgs",
    "Directory",
    "DirectoryArgs",
    "Provider",
]

__version__ = "0.1.0"
