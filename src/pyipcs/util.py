"""
Public Utility Functions
"""

from pyipcs.exceptions import TsoError
from zoautil_py import datasets, zoau_io, exceptions
from ._execs import IPCSVERS, IPCSRUN, IPCSSRC, IPCSEVAL
from ._util import get_dataset, check_dataset_exists, tso_profile_prefix
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
    dsname = tso_profile_prefix()
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
            f"{dsname}(IPCSSRC)",
            content=IPCSSRC
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

def is_dump(dsname: str) -> bool:
    """
    Determine whether a data set exists and is a z/OS dump data set.
    
    Parameters
    ----------
    dsname : str

    Returns
    -------
    bool
        ``True`` if data set exists and is a dump data set. ``False`` otherwise.
    """
    # Check if the data set exists and perform checks
    dump_dataset_obj = get_dataset(dsname)
    if dump_dataset_obj is None:
        return False
    if int(dump_dataset_obj.record_length) != 4160:
        return False
    if int(dump_dataset_obj.block_size) % int(dump_dataset_obj.record_length) != 0:
        return False
    # Check if first record starts with DR2
    if not zoau_io.RecordIO(f"//'{dsname}'").readrecord().hex().upper().startswith("C4D9F2"):
        return False
    return True
