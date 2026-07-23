"""
Public Utility Functions
"""

import os
from pyipcs.exceptions import TsoError
from zoautil_py import datasets, exceptions
from ._execs import IPCSVERS, IPCSRUN, IPCSEVAL
from ._util import check_dataset_exists
from ._version import __version__


def default_driver_dsname() -> str:
    """
    Return the default pyIPCS driver data set name.

    The name is derived as <TSO_profile_prefix>.PYIPCS.V<pyIPCS_version>.

    Returns
    -------
    str
        Default driver data set name.
    """
    # Start with TSO prefix:
    dsname = datasets.get_hlq() if datasets.get_hlq() else os.getenv("USER", "TEMP")
    # Add .PYIPCS.V<pyIPCS_version>:
    dsname += ".PYIPCS.V"
    dsname += "".join(part.zfill(2) for part in __version__.split("."))
    return dsname


def create_driver(dsname: str) -> None:
    """
    Create pyIPCS driver data set.

    Parameters
    ----------
    dsname : str
        Name of the pyIPCS driver data set to create and populate.

    Returns
    -------
    None
    """
    if check_dataset_exists(dsname):
        raise ValueError(f"Data set {dsname} already exists")
    try:
        datasets.create(dsname, dataset_type="PDSE")
        datasets.write(
            f"{dsname}(IPCSVERS)",
            content=IPCSVERS
        )
        datasets.write(
            f"{dsname}(IPCSRUN)",
            content=IPCSRUN
        )
        datasets.write(
            f"{dsname}(IPCSEVAL)",
            content=IPCSEVAL
        )
    except exceptions.DatasetWriteException as e:
        datasets.delete(dsname)
        raise TsoError(
            "Failed to create pyIPCS driver data set {dsname}"
        ) from e