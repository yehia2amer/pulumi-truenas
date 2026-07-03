"""Pulumi dynamic resources for TrueNAS."""

from pulumi_truenas.resources.catalog_app import CatalogApp, CatalogAppArgs
from pulumi_truenas.resources.custom_app import CustomApp, CustomAppArgs
from pulumi_truenas.resources.dataset import Dataset, DatasetArgs
from pulumi_truenas.resources.directory import Directory, DirectoryArgs

__all__ = [
    "CatalogApp",
    "CatalogAppArgs",
    "CustomApp",
    "CustomAppArgs",
    "Dataset",
    "DatasetArgs",
    "Directory",
    "DirectoryArgs",
]
