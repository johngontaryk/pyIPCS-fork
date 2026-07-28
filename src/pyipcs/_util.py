"""
Internal Utility Functions
"""

import os
from zoautil_py import datasets, zoau_io
from ._tso import tso_cmd
from .allocation import IpcsAllocation
from .exceptions import TsoError

def tso_profile_prefix() -> str:
    """
    Return the TSO profile prefix (high-level qualifier).

    Returns
    -------
    str
        TSO profile prefix, or the USER environment variable if unavailable,
        or ``"TEMP"`` as a last resort.
    """
    return datasets.get_hlq() if datasets.get_hlq() else os.getenv("USER", "TEMP")


def attempt_recall(dsname: str) -> None:
    """
    Use automatic recall to attempt to recall a data set.

    Parameters
    ----------
    dsname : str
        Data set name for dataset you want to recall.

    Returns
    -------
    None
    """
    tso_cmd(
        "TIME",
        allocations=[IpcsAllocation("PYIPCS", dsname)],
    )

def get_dataset(dsname: str) -> datasets.Dataset | None:
    """
    Get specific Dataset object from dataset name.

    Will recall dataset if it exists.

    Parameters
    ----------
    dsname : str

    Returns
    -------
    zoautil_py.datasets.Dataset or None
        Data set object or ``None`` if the data set does not exist.
    """
    if "*" in dsname:
        raise ValueError(f"Data set name {dsname} cannot be a pattern (cannot include '*')")
    
    attempt_recall(dsname)
    dataset_list = datasets.list_datasets(dsname.strip())

    for dataset_obj in dataset_list:
        if dataset_obj.name == dsname.strip():
            return dataset_obj
    
    # If the data set is not found in the list it does not exist
    raise ValueError(f"Data set {dsname} does not exist")

def check_dataset_exists(dsname: str) -> bool:
    """
    Attempt recall and check if data set exists.

    Parameters
    ----------
    dsname : str

    Returns
    -------
    bool

    Raises
    ------
    ValueError
        If data set name is invalid.
    """
    if "*" in dsname:
        raise ValueError(f"Data set name {dsname} cannot be a pattern (cannot include '*')")
    attempt_recall(dsname)
    return datasets.exists(dsname)

def assert_dataset_exists(dsname: str) -> None:
    """
    Attempt recall and throw error if data set does not exist.

    Parameters
    ----------
    dsname : str

    Returns
    -------
    None

    Raises
    ------
    TsoError
        If data set name is invalid or the data set does not exist.
    """
    if "*" in dsname:
        raise ValueError(f"Data set name {dsname} cannot be a pattern (cannot include '*')")
    attempt_recall(dsname)
    if not datasets.exists(dsname):
        raise TsoError(f"Data set {dsname} does not exist")

def get_header_record(dsname: str) -> bytes:
    """
    Get z/OS dump 

    Parameters
    ----------
    dsname : str

    Returns
    -------
    bytes
    """
    pass


