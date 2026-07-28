"""
IpcsDump Object
"""

from .exceptions import TsoError
from .util import is_dump

class IpcsDump:
    """
    z/OS dump data set.

    Attributes
    ----------
    dsname : str
        Dump data set name.
    """

    def __init__(self, dsname: str) -> None:
        """
        Constructor for :class:`pyipcs.IpcsDump` Object.

        Parameters
        ----------
        dsname : str
            Dump data set name.
        """
        if not is_dump(dsname):
            raise TsoError(f"Data set {dsname} does not exist or is not a z/OS dump data set.")
        self._dsname = dsname

    @property
    def dsname(self) -> str:
        return self._dsname

