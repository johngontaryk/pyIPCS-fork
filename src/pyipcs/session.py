"""
IpcsSession Object
"""

from collections.abc import Iterable
import copy
import random
from typing import Self, IO, Optional
from .allocation import IpcsAllocation
from .dump import IpcsDump
from ._util import check_dataset_exists, tso_profile_prefix
from ._tso import tso_cmd
from ._version import __version__
from ._ipcs import ipcs_subcmd
from .exceptions import TsoError, TsoInvalidReturnCodeError, DdirNotSet
from .util import default_driver_dsname, create_driver
from .response import TsoResponse, IpcsResponse

class IpcsSession:
    """
    Drives IPCS subcommand execution.
    Manages the settings for your pyIPCS session, such TSO allocations and dump directories (DDIRs).

    Attributes
    ----------
    driver : str
        pyIPCS driver data set — a PDSE that stores the REXX and CLIST
        execs used to drive IPCS functionality.
    allocations : list[IpcsAllocation]
        Copy of the current IPCS allocations.
    ddir : str or None
        Current dump directory (DDIR) data set name, or ``None`` if not set.
    """

    def __init__(
        self,
        driver: str | None = None,
        allocations: IpcsAllocation | Iterable[IpcsAllocation] = [
            IpcsAllocation("IPCSPARM", ["SYS1.PARMLIB"]),
            IpcsAllocation("SYSPROC", ["SYS1.SBLSCLI0"]),
        ],
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

        Notes
        -----
        If you do not know which allocations are needed in order to run IPCS on your current system,
        please reach out to your system administrator.
        """
        # Set current DDIR to None
        self._ddir = None
        # Whether the current DDIR is temporary and should be deleted on close/replace
        self._temp_ddir = False

        # Set session data set
        self._driver = driver.strip() if driver else default_driver_dsname()

        if isinstance(allocations, IpcsAllocation):
            allocations = [allocations]
        self._allocations = copy.deepcopy(list(allocations))

        # Allocation for session data set
        self._session_allocation = IpcsAllocation("PYIPCS", [self._driver])

        if check_dataset_exists(self._driver):
            # If session data set does exist,
            # verify we are using the same pyIPCS version
            response = tso_cmd(
                cmd=f"ex \'{self._driver}(IPCSVERS)\'",
                allocations=self._session_allocation,
            )
            if response.rc != 0 or f"PYIPCS={__version__}" not in response.output:
                raise TsoError(
                    f"pyIPCS driver data set {self._driver} already exists and is invalid or does not match the current pyIPCS version"
                )
        else:
            # If session data set does not exist, create it
            create_driver(self._driver)

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *_) -> None:
        self.close()

    def close(self) -> None:
        """
        Close the session. If the current DDIR is temporary (set via
        :meth:`set_temp_ddir` with ``delete=True``), it is deleted.

        Returns
        -------
        None
        """
        if self._ddir is not None and self._temp_ddir:
            self.delete_ddir()

    @property
    def driver(self) -> str:
        return self._driver

    @property
    def allocations(self) -> list[IpcsAllocation]:
        return copy.deepcopy(self._allocations)

    @property
    def ddir(self) -> str | None:
        return self._ddir

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

        Notes
        -----
        If you do not know which allocations are needed in order to run IPCS on your current system,
        please reach out to your system administrator.
        """
        if isinstance(allocations, IpcsAllocation):
            allocations = [allocations]
        self._allocations = copy.deepcopy(list(allocations))

    def set_ddir(
        self,
        dsname: str,
        parms: Optional[str | Iterable[str]] = None,
    ) -> TsoResponse:
        """
        Set the current dump directory (DDIR) by running the ``BLSCDDIR`` CLIST.
        If the dump directory does not exist, the ``BLSCDDIR`` CLIST will create it.

        If the current DDIR is temporary (set via :meth:`set_temp_ddir` with
        ``delete=True``), it is deleted before the new DDIR is set.

        Parameters
        ----------
        dsname : str
            Data set name of the DDIR to set as current.

        parms : str or Iterable[str], optional
            Additional parameters to pass to the ``BLSCDDIR`` CLIST.
            May be a single string (e.g. ``'RECORDS(4000) VOLUME(MYVOL)'``)
            or an iterable of strings (e.g. ``['RECORDS(4000)', 'VOLUME(MYVOL)']``).

        Returns
        -------
        TsoResponse

        Raises
        ------
        TsoInvalidReturnCodeError
            If ``BLSCDDIR`` returns a return code >= 12.
        """
        # Delete the existing temp DDIR before switching to a new one
        if self._ddir is not None and self._temp_ddir:
            self.delete_ddir()
        # Run BLSCDDIR CLIST
        cmd = f"%BLSCDDIR DSNAME({dsname})"
        if parms is not None:
            if not isinstance(parms, str):
                parms = " ".join(parms)
            cmd += f" {parms}"
        response = tso_cmd(
            cmd=cmd,
            allocations=self.allocations,
        )
        # Validate the return code
        # BLSCDDIR only treats LASTCC >= 12 as a hard failure; lower codes
        # are soft warnings from subordinate TSO/VSAM services and are safe
        # to ignore (matching every LASTCC check within the CLIST itself).
        if response.rc >= 12:
            raise TsoInvalidReturnCodeError(response)
        # Set as the current DDIR (not temporary)
        self._ddir = dsname
        self._temp_ddir = False
        # Return BLSCDDIR response
        return response

    def set_temp_ddir(
        self,
        hlq: Optional[str] = None,
        parms: Optional[str | Iterable[str]] = None,
        delete: bool = True,
    ) -> TsoResponse:
        """
        Create and set a randomly named temporary dump directory (DDIR).

        The DDIR data set name is ``<hlq>.DDIR<4_digit_ID>``.

        Parameters
        ----------
        hlq : str, optional
            High-level qualifier prefix for the temporary DDIR name.
            Defaults to ``<TSO_profile_prefix>.PYIPCS``.

        parms : str or Iterable[str], optional
            Additional parameters to pass to the ``BLSCDDIR`` CLIST.
            May be a single string (e.g. ``'RECORDS(4000) VOLUME(MYVOL)'``)
            or an iterable of strings (e.g. ``['RECORDS(4000)', 'VOLUME(MYVOL)']``).

        delete : bool, optional
            If ``True`` (the default), the temporary DDIR will be deleted
            automatically when :meth:`close` is called, when the session exits
            a ``with`` block, or when a new DDIR is set via :meth:`set_ddir`
            or :meth:`set_temp_ddir`.

        Returns
        -------
        TsoResponse

        Raises
        ------
        TsoInvalidReturnCodeError
            If ``BLSCDDIR`` returns a return code >= 12.
        """
        if hlq is None:
            hlq = f"{tso_profile_prefix()}.PYIPCS"
        suffix = str(random.randint(0, 9999)).zfill(4)
        dsname = f"{hlq}.DDIR{suffix}"
        # set_ddir will handle deleting any existing temp DDIR first
        response = self.set_ddir(dsname, parms=parms)
        self._temp_ddir = delete
        return response

    def delete_ddir(self) -> TsoResponse:
        """
        Delete the current dump directory (DDIR) data set using the TSO ``DELETE`` command
        and unset it to ``None``.

        Returns
        -------
        TsoResponse

        Raises
        ------
        DdirNotSet
            If no DDIR has been set for this session.
        TsoInvalidReturnCodeError
            If the TSO ``DELETE`` command returns a non-zero return code.
        """
        if self._ddir is None:
            raise DdirNotSet()
        # Run TSO DELETE command
        response = tso_cmd(
            cmd=f"DELETE '{self._ddir}'",
            allocations=IpcsAllocation("PYIPCS", self._ddir),
        )
        if response.rc != 0:
            raise TsoInvalidReturnCodeError(response)
        # Unset the current DDIR
        self._ddir = None
        return response

    def sources(self) -> list[str]:
        """
        Return the source dump data set names described in the current DDIR.

        Uses the pyIPCS driver ``IPCSSRC`` REXX exec, 
        which calls ``EVALDUMP`` to iterate
        all source descriptions in the current DDIR.

        Returns
        -------
        list[str]
            Source dump data set names described in the current DDIR.

        Raises
        ------
        DdirNotSet
            If no DDIR has been set for this session.
        TsoInvalidReturnCodeError
            If ``IPCSSRC`` returns a non-zero return code.
        """
        if self._ddir is None:
            raise DdirNotSet()
        response = tso_cmd(
            cmd=f"ex '{self._driver}(IPCSSRC)'",
            allocations=[
                self._session_allocation,
                IpcsAllocation("IPCSDDIR", [self._ddir]),
            ] + self.allocations,
        )
        if response.rc != 0:
            raise TsoInvalidReturnCodeError(response)
        if not response.output:
            return []
        return [
            line.strip()
            for line in response.output.splitlines()
            if line.strip()
        ]

    def init_dump(
        self,
        dump: IpcsDump,
    ) -> IpcsResponse:
        """
        Attempt initialization of a dump data set by running 
        ``SETDEF LOCAL NOLIST DSNAME(<dump.dsname>)`` then the ``STATUS`` subcommand.

        Parameters
        ----------
        dump : pyipcs.IpcsDump
            Dump data set.

        Returns
        -------
        IpcsResponse
            IPCS response from running ``STATUS`` subcommand.

        Raises
        ------
        DdirNotSet
            If no DDIR has been set for this session.

        Notes
        -----
        This will not set the global source dump default for your session. 
        To run future subcommands against the dump data set you must 
        specify the ``dump`` parameter for :meth:`setdef_global` or :meth:`run`.
        """
        return self.run("STATUS", dump=dump)

    def drop_dump(
        self,
        dsname: str,
    ) -> IpcsResponse:
        """
        Delete a source description from the current dump directory (DDIR)
        by running ``DROPDUMP DSNAME(<dsname>)``.

        Parameters
        ----------
        dsname : str
            Data set name of the dump to drop.

        Returns
        -------
        IpcsResponse

        Raises
        ------
        DdirNotSet
            If no DDIR has been set for this session.
        """
        return self.run(f"DROPDUMP DSNAME({dsname})")

    def setdef_global(
        self,
        dump: Optional[IpcsDump] = None,
        setdef_parms: Optional[str | Iterable[str]] = None,
    ) -> IpcsResponse:
        """
        Set global defaults for your current dump directory.
        Run the ``SETDEF LIST GLOBAL <setdef_parms>`` IPCS subcommand.
        These defaults will carry over to future subcommands
        for the currently set dump directory (DDIR).

        Parameters
        ----------
        dump : pyipcs.IpcsDump, optional
            Dump data set. When provided, sets the global default source dump
            by adding ``DSNAME(<dump.dsname>)`` to ``setdef_parms``.

        setdef_parms : str or Iterable[str], optional
            Additional parameters to pass to ``SETDEF LIST GLOBAL``.
            May be a single string (e.g. ``'FLAG(WARNING) CONFIRM(NO)'``)
            or an iterable of strings (e.g. ``['FLAG(WARNING)', 'CONFIRM(NO)']``).
            Default is None.

        Returns
        -------
        IpcsResponse
            IPCS response from the ``SETDEF LIST GLOBAL`` subcommand.

        Raises
        ------
        DdirNotSet
            If no DDIR has been set for this session.
        """
        if self._ddir is None:
            raise DdirNotSet()
        subcmd = "SETDEF LIST GLOBAL"
        if dump is not None:
            subcmd += f" DSNAME({dump.dsname})"
        if setdef_parms is not None:
            if not isinstance(setdef_parms, str):
                setdef_parms = " ".join(setdef_parms)
            subcmd += f" {setdef_parms}"
        return ipcs_subcmd(
            subcmd=subcmd,
            driver=self._driver,
            ddir=self._ddir,
            allocations=self.allocations,
        )

    def run(
        self,
        subcmd: str,
        authorized: bool = True,
        dump: Optional[IpcsDump] = None,
        setdef_parms: Optional[str | Iterable[str]] = None,
        output: Optional[IO[str]] = None,
    ) -> IpcsResponse:
        """
        Run an IPCS subcommand.

        Parameters
        ----------
        subcmd : str
            IPCS subcommand to run.

        authorized : bool, optional
            Indicates whether the subcommand will be run in an authorized environment.
            Default is ``True``.

        dump : pyipcs.IpcsDump, optional
            Source dump data set name to run the subcommand against.
            If provided, ``DSNAME(<dump.dsname>)`` is added to ``setdef_parms``,
            so the source will not carry over to future subcommands.
            Default is None.

        setdef_parms : str or Iterable[str], optional
            If provided, runs ``SETDEF NOLIST LOCAL <setdef_parms>`` before
            running the specified subcommand.
            Note: the defaults set by this will not carry over to future subcommands.
            May be a single string (e.g. ``'FLAG(WARNING) CONFIRM(NO)'``)
            or an iterable of strings (e.g. ``['FLAG(WARNING)', 'CONFIRM(NO)']``).
            Default is None.

        output : file object, optional
            An open, writable text file object. When provided, subcommand output is
            written to this file instead of being returned as a string
            (``output`` attribute will be ``None`` in returned ``IpcsResponse``).
            Default is None.

        Returns
        -------
        IpcsResponse

        Raises
        ------
        DdirNotSet
            If no DDIR has been set for this session.
        ValueError
            If the ``source`` data set is specified and does not exist.
        """
        if self._ddir is None:
            raise DdirNotSet()
        if dump is not None:
            dsname_parm = f"DSNAME({dump.dsname})"
            if setdef_parms is None:
                setdef_parms = dsname_parm
            elif isinstance(setdef_parms, str):
                setdef_parms = f"{setdef_parms} {dsname_parm}"
            else:
                setdef_parms = list(setdef_parms) + [dsname_parm]
        return ipcs_subcmd(
            subcmd=subcmd,
            driver=self._driver,
            ddir=self._ddir,
            allocations=self.allocations,
            authorized=authorized,
            setdef_parms=setdef_parms,
            output=output,
        )
