"""
IpcsSession Object
"""

from collections.abc import Iterable
import copy
from typing import IO, Optional
from .allocation import IpcsAllocation
from ._util import check_dataset_exists, assert_dataset_exists
from ._tso import tso_cmd
from ._version import __version__
from ._ipcs import ipcs_subcmd
from .exceptions import TsoError, TsoInvalidReturnCodeError, DdirNotSet
from .util import default_driver_dsname, create_driver

class IpcsSession:
    """
    Manages TSO allocations, execs, and DDIRs, and other settings for your pyIPCS Session.

    Attributes
    ----------
    driver : str
        pyIPCS driver data set — a PDSE that stores the REXX and CLIST
        execs used to drive IPCS functionality.
    """

    def __init__(
        self,
        driver: str | None = None,
        allocations: IpcsAllocation | Iterable[IpcsAllocation] = (
            IpcsAllocation("IPCSPARM", ["SYS1.PARMLIB"]),
            IpcsAllocation("SYSPROC", ["SYS1.SBLSCLI0"]),
        ),
    ) -> None:
        """
        Constructor for :class:`pyipcs.IpcsSession` Object.

        Parameters
        ----------
        driver : str, optional
            Name of the pyIPCS driver data set — a PDSE that stores the REXX and CLIST
            execs used to drive IPCS functionality. If the data set does not exist, it
            will be created and populated on initialization. Defaults to
            <TSO_profile_prefix>.PYIPCS.V<pyIPCS_version>.
            
        
        allocations : IpcsAllocation or Iterable[IpcsAllocation], optional
            A single allocation or iterable of IPCS allocations.
            The default allocations are dataset SYS1.PARMLIB for DD name IPCSPARM
            and dataset SYS1.SBLSCLI0 for DD name SYSPROC.

        Returns
        -------
        None
        """
        # Set current DDIR to None
        self._ddir = None

        # Set session data set
        if driver is not None:
            self._dsname = driver.strip()
        else:
            self._dsname = default_driver_dsname()

        if isinstance(allocations, IpcsAllocation):
            allocations = [allocations]
        self._allocations = copy.deepcopy(list(allocations))

        # Allocation for session data set
        self._session_allocation = IpcsAllocation("PYIPCS", [self._dsname])

        if check_dataset_exists(self._dsname):
            # If session data set does exist, 
            # verify we are using the same pyIPCS version
            response = tso_cmd(
                cmd=f"ex \'{self._dsname}(IPCSVERS)\'",
                allocations=self._session_allocation,
            )
            if response["rc"] != 0 or f"PYIPCS={__version__}" not in response["output"]:
                raise TsoError(
                    f"pyIPCS driver data set {self._dsname} already exists and is invalid or does not match the current pyIPCS version"
                )
        else:
            # If session data set does not exist, create it
            create_driver(self._dsname)

    @property
    def dsname(self) -> str:
        return self._dsname

    def get_allocations(self) -> list[IpcsAllocation]:
        """
        Return a copy of the current IPCS allocations.

        Returns
        -------
        list[IpcsAllocation]
            Copy of the internal IPCS allocations.
        """
        return copy.deepcopy(self._allocations)

    def set_allocations(self, allocations: IpcsAllocation | Iterable[IpcsAllocation]) -> None:
        """
        Replace the current IPCS allocations with a copy of the provided IPCS allocations.

        Parameters
        ----------
        allocations : IpcsAllocation or Iterable[IpcsAllocation]
            A single allocation or iterable of allocations that will become the new IPCS allocations.

        Returns
        -------
        None
        """
        if isinstance(allocations, IpcsAllocation):
            allocations = [allocations]
        self._allocations = copy.deepcopy(list(allocations))

    def get_ddir(self) -> str | None:
        """
        Return the current dump directory (DDIR) data set name, or ``None`` if not set.

        Returns
        -------
        str or None
            Current DDIR data set name.
        """
        return self._ddir

    def set_ddir(self, dsname: str) -> None:
        """
        Set the current dump directory (DDIR) to the specified data set.

        Parameters
        ----------
        dsname : str
            Data set name of the DDIR to set as current.

        Returns
        -------
        None

        Raises
        ------
        ValueError
            If the data set does not exist.
        """
        assert_dataset_exists(dsname)
        self._ddir = dsname

    def create_ddir(
        self,
        dsname: str,
        parms: Optional[str | Iterable[str]] = None,
    ) -> dict:
        """
        Run the ``BLSCDDIR`` CLIST to create a dump directory (DDIR).
        Will set the newly created DDIR as the current DDIR.

        Parameters
        ----------
        dsname : str
            Data set name of the DDIR to create.

        parms : str or Iterable[str], optional
            Additional parameters to pass to the ``BLSCDDIR`` CLIST.
            May be a single string (e.g. ``'RECORDS(4000) VOLUME(MYVOL)'``)
            or an iterable of strings (e.g. ``['RECORDS(4000)', 'VOLUME(MYVOL)']``).

        Returns
        -------
        dict
            Dictionary with keys:

            - ``cmd`` : str — the ``BLSCDDIR`` CLIST command that was run.
            - ``rc`` : int — return code from the ``BLSCDDIR`` CLIST.
            - ``output`` : str — output produced by the ``BLSCDDIR`` CLIST.
        """
        # Run BLSCDDIR CLIST
        cmd = "%BLSCDDIR"
        if dsname is not None:
            cmd += f" DSNAME({dsname})"
        if parms is not None:
            cmd += " " + (parms if isinstance(parms, str) else " ".join(parms))
        response = tso_cmd(
            cmd=cmd,
            allocations=self.get_allocations(),
        )
        # Validate the return code
        if response["rc"] > 0:
            raise TsoInvalidReturnCodeError(response)
        # Set as the current DDIR
        self.set_ddir(dsname)
        # Return BLSCDDIR response
        return response

    def setdef_global(
        self,
        setdef_parms: Optional[str | Iterable[str]] = None,
    ) -> dict:
        """
        Set global defaults for you current dump directory.
        Run the ``SETDEF LIST GLOBAL <setdef_parms>`` IPCS subcommand.
        These defaults will carry over to future subcommands 
        for the currently set dump directory (DDIR).

        Parameters
        ----------
        setdef_parms : str or Iterable[str], optional
            Additional parameters to pass to ``SETDEF LIST GLOBAL``.
            May be a single string (e.g. ``'FLAG(WARNING) CONFIRM(NO)'``)
            or an iterable of strings (e.g. ``['FLAG(WARNING)', 'CONFIRM(NO)']``).
            Default is None.

        Returns
        -------
        dict
            Dictionary with keys:

            - ``subcmd`` : str — the IPCS subcommand that was run.
            - ``rc`` : int — return code of the IPCS subcommand.
            - ``output`` : str — output from the ``SETDEF LIST GLOBAL`` subcommand.
            - ``authorized`` : bool — whether the subcommand ran in an authorized environment.

        Raises
        ------
        DdirNotSet
            If no DDIR has been set for this session.
        """
        if self._ddir is None:
            raise DdirNotSet()
        subcmd = "SETDEF LIST GLOBAL"
        if setdef_parms is not None:
            subcmd += " " + (setdef_parms if isinstance(setdef_parms, str) else " ".join(setdef_parms))
        return ipcs_subcmd(
            subcmd=subcmd,
            driver=self._dsname,
            ddir=self._ddir,
            allocations=self.get_allocations(),
        )

    def setdef_source(
        self,
        dsname: str,
    ) -> dict:
        """
        Set the global default for your source (e.g. a dump data set)
        for you current dump directory.
        Run the ``SETDEF LIST GLOBAL DSNAME(<dsname>)`` IPCS subcommand
        to set the dump source for the current dump directory.
        This default will carry over to future subcommands 
        for the currently set dump directory (DDIR).

        Parameters
        ----------
        dsname : str
            Data set name of the dump source to set (e.g. a dump data set).

        Returns
        -------
        dict
            Dictionary with keys:

            - ``subcmd`` : str — the IPCS subcommand that was run.
            - ``rc`` : int — return code of the IPCS subcommand.
            - ``output`` : str — output from the ``SETDEF LIST GLOBAL`` subcommand.
            - ``authorized`` : bool — whether the subcommand ran in an authorized environment.

        Raises
        ------
        DdirNotSet
            If no DDIR has been set for this session.
        """
        return self.setdef_global(setdef_parms=f"DSNAME({dsname})")

    def run(
        self,
        subcmd: str,
        authorized: bool = True,
        source: Optional[str] = None,
        setdef_parms: Optional[str | Iterable[str]] = None,
        output: Optional[IO[str]] = None,
    ) -> dict:
        """
        Run an IPCS subcommand.

        Parameters
        ----------
        subcmd : str
            IPCS subcommand to run.

        authorized : bool, optional
            Indicates whether the subcommand will be run in an authorized environment.
            Default is ``True``.

        source : str, optional
            Data set name for your source source (e.g. a dump data set).
            If provided, ``DSNAME(<source>)`` is added to ``setdef_parms``,
            so the source will not carry over to future subcommands.
            Default is None.

        setdef_parms : str or Iterable[str], optional
            If provided, runs ``SETDEF LOCAL NOLIST <setdef_parms>`` before
            running the specified subcommand.
            Note: the defaults set by this will not carry over to future subcommands.
            May be a single string (e.g. ``'FLAG(WARNING) CONFIRM(NO)'``)
            or an iterable of strings (e.g. ``['FLAG(WARNING)', 'CONFIRM(NO)']``).
            Default is None.

        output : file object, optional
            An open, writable text file object. When provided, subcommand output is
            written to this file instead of being returned as a string
            (``"output"`` will be ``None`` in returned dict).
            Default is None.

        Returns
        -------
        dict
            Dictionary with keys:

            - ``subcmd`` : str — the IPCS subcommand that was run.
            - ``rc`` : int — return code of the IPCS subcommand.
            - ``output`` : str or None — output from the IPCS subcommand,
              or ``None`` if a file object was provided via ``output``.
            - ``authorized`` : bool — whether the subcommand ran in an authorized environment.

        Raises
        ------
        DdirNotSet
            If no DDIR has been set for this session.
        """
        if self._ddir is None:
            raise DdirNotSet()
        if source is not None:
            dsname_parm = f"DSNAME({source})"
            if setdef_parms is None:
                setdef_parms = dsname_parm
            elif isinstance(setdef_parms, str):
                setdef_parms = f"{setdef_parms} {dsname_parm}"
            else:
                setdef_parms = list(setdef_parms) + [dsname_parm]
        return ipcs_subcmd(
            subcmd=subcmd,
            driver=self._dsname,
            ddir=self._ddir,
            allocations=self.get_allocations(),
            authorized=authorized,
            setdef_parms=setdef_parms,
            output=output,
        )
