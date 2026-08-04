"""
IpcsDdir Object
"""

from __future__ import annotations
from collections.abc import Iterable
import copy
import random
import warnings
import weakref
from typing import Self, IO, Optional
from .allocation import IpcsAllocation
from .dump import IpcsDump
from ._util import check_dataset_exists, tso_profile_prefix
from ._tso import tso_cmd
from ._version import __version__
from ._ipcs import ipcs_subcmd
from .exceptions import (
    TsoError,
    TsoInvalidReturnCodeError,
    TsoInvalidReturnCodeWarning,
    IpcsInvalidReturnCodeError,
    DdirDeletedError,
)
from .util import default_driver_dsname, create_driver
from .response import TsoResponse, IpcsResponse


class IpcsDdir:
    """
    IPCS dump directory (DDIR).
    Drives IPCS subcommand execution.

    Runs ``BLSCDDIR`` on initialization to create or open the DDIR data set.

    References:
        - `Using User and Sysplex Dump Directories
          <https://www.ibm.com/docs/en/zos/3.2.0?topic=functions-using-user-sysplex-dump-directories>`_
        - `BLSCDDIR CLIST
          <https://www.ibm.com/docs/en/zos/3.2.0?topic=execs-blscddir-clist-create-dump-directory>`_
    """

    def __init__(
        self,
        dsname: str,
        driver: Optional[str] = None,
        allocations: Optional[Iterable[IpcsAllocation]] = None,
        parms: Optional[str | Iterable[str]] = None,
        delete: bool = False,
    ) -> None:
        """
        Constructor for :class:`pyipcs.IpcsDdir`.

        Runs ``BLSCDDIR DSNAME('<dsname>')`` to create or open the dump directory.

        Args:
            dsname: Data set name of the DDIR.
            driver: Name of the pyIPCS driver data set — a PDSE that stores the
                REXX and CLIST execs used to drive IPCS functionality. If the
                data set does not exist, it will be created and populated on
                initialization. Defaults to
                ``<TSO_profile_prefix>.PYIPCS.V<pyIPCS_version>``.
            allocations: Iterable of IPCS allocations. The default allocations
                are dataset ``SYS1.PARMLIB`` for DD name ``IPCSPARM`` and
                dataset ``SYS1.SBLSCLI0`` for DD name ``SYSPROC``.
            parms: Additional parameters to pass to the ``BLSCDDIR`` CLIST.
                May be a single string (e.g. ``'RECORDS(4000) VOLUME(MYVOL)'``)
                or an iterable of string parms
                (e.g. ``['RECORDS(4000)', 'VOLUME(MYVOL)']``).
                Default is ``None``.
            delete: If ``True``, the current DDIR is deleted via :meth:`delete`
                when exiting the context manager (``with`` block), or when the
                :class:`pyipcs.IpcsDdir` instance is finalized by the garbage
                collector. Deletion upon finalization is not guaranteed if the
                process terminates abruptly or if the object remains referenced
                (e.g., in exception tracebacks). If ``False`` (the default),
                the current DDIR will persist after the object is exited or
                garbage-collected.

        Note:
            If you do not know which allocations are needed in order to run IPCS
            on your current system, please reach out to your system administrator.

        Raises:
            TsoInvalidReturnCodeError: If ``BLSCDDIR`` returns a return code >= 12.

        References:
            - `BLSCDDIR CLIST
              <https://www.ibm.com/docs/en/zos/3.2.0?topic=execs-blscddir-clist-create-dump-directory>`_
        """
        self._dsname = dsname.strip()
        if allocations is None:
            allocations = [
                IpcsAllocation("IPCSPARM", ["SYS1.PARMLIB"]),
                IpcsAllocation("SYSPROC", ["SYS1.SBLSCLI0"]),
            ]
        self._allocations = copy.deepcopy(list(allocations))

        # Run BLSCDDIR CLIST
        self._response: TsoResponse = IpcsDdir._blscddir(
            self._dsname, parms, self._allocations
        )

        # Set delete policy and create finalizer
        self._delete_policy = {"delete": delete, "is_deleted": True}
        self._finalizer = weakref.finalize(
            self, IpcsDdir._cleanup, self._dsname, self._delete_policy
        )

        # Create/Load driver data set
        self._driver = driver.strip() if driver else default_driver_dsname()
        if check_dataset_exists(self._driver):
            IpcsDdir._validate_driver(self._driver)
        else:
            create_driver(self._driver)

    @property
    def dsname(self) -> str:
        """Data set name of this dump directory (DDIR)."""
        return self._dsname

    @property
    def driver(self) -> str:
        """pyIPCS driver data set name."""
        return self._driver

    @property
    def allocations(self) -> list[IpcsAllocation]:
        """Current IPCS allocations (deep copy)."""
        return copy.deepcopy(self._allocations)

    @property
    def response(self) -> TsoResponse:
        """Response from the ``BLSCDDIR`` command issued during initialization."""
        return self._response

    @property
    def is_deleted(self) -> bool:
        """Whether this DDIR has been deleted via :meth:`delete`."""
        return self._delete_policy["is_deleted"]

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *_) -> None:
        if hasattr(self, "_delete_policy"):
            IpcsDdir._cleanup(self.dsname, self._delete_policy)

    @classmethod
    def create_temp(
        cls,
        hlq: Optional[str] = None,
        driver: Optional[str] = None,
        allocations: Optional[Iterable[IpcsAllocation]] = None,
        parms: Optional[str | Iterable[str]] = None,
        delete: bool = True,
    ) -> Self:
        """
        Alternative constructor that creates a temporary DDIR with a randomly generated name.

        Generates a unique DDIR data set name under ``<hlq>.DDIR<4_digit_ID>``
        and runs ``BLSCDDIR`` to create or open it.

        Args:
            hlq: High-level qualifier prefix for the temporary DDIR name.
                Defaults to ``<TSO_profile_prefix>.PYIPCS``.
            driver: Name of the pyIPCS driver data set — a PDSE that stores the
                REXX and CLIST execs used to drive IPCS functionality. If the
                data set does not exist, it will be created and populated on
                initialization. Defaults to
                ``<TSO_profile_prefix>.PYIPCS.V<pyIPCS_version>``.
            allocations: Iterable of IPCS allocations. The default allocations
                are dataset ``SYS1.PARMLIB`` for DD name ``IPCSPARM`` and
                dataset ``SYS1.SBLSCLI0`` for DD name ``SYSPROC``.
            parms: Additional parameters to pass to the ``BLSCDDIR`` CLIST.
                May be a single string (e.g. ``'RECORDS(4000) VOLUME(MYVOL)'``)
                or an iterable of string parms
                (e.g. ``['RECORDS(4000)', 'VOLUME(MYVOL)']``).
                Default is ``None``.
            delete: If ``True`` (the default), the DDIR data set is deleted
                automatically when the ``with`` block exits. If ``False``, the
                data set is left in place.

        Returns:
            IpcsDdir: A new :class:`IpcsDdir` instance backed by the generated
            temporary data set.

        Note:
            If you do not know which allocations are needed in order to run IPCS
            on your current system, please reach out to your system administrator.

        Raises:
            TsoError: If no available DDIR name can be found after 100 attempts.
            TsoInvalidReturnCodeError: If ``BLSCDDIR`` returns a return code >= 12.

        References:
            - `BLSCDDIR CLIST
              <https://www.ibm.com/docs/en/zos/3.2.0?topic=execs-blscddir-clist-create-dump-directory>`_
        """
        if hlq is None:
            hlq = f"{tso_profile_prefix()}.PYIPCS"
        max_attempts = 100
        for _ in range(max_attempts):
            suffix = f"{random.randint(0, 9999):04d}"
            dsname = f"{hlq}.DDIR{suffix}"
            if not check_dataset_exists(dsname):
                break
        else:
            raise TsoError(
                f"Could not find an available temporary DDIR name under '{hlq}' "
                f"after {max_attempts} attempts."
            )
        return cls(
            dsname, driver=driver, allocations=allocations, parms=parms, delete=delete
        )

    def set_allocations(self, allocations: Iterable[IpcsAllocation]) -> None:
        """
        Replace the current IPCS allocations with a copy of the provided IPCS allocations.

        Args:
            allocations: Iterable of allocations that will become the new IPCS
                allocations.

        Note:
            If you do not know which allocations are needed in order to run IPCS
            on your current system, please reach out to your system administrator.
        """
        self._allocations = copy.deepcopy(list(allocations))

    def delete(self) -> TsoResponse:
        """
        Delete this dump directory (DDIR) data set using the TSO ``DELETE`` command.

        Returns:
            TsoResponse: Response from the ``DELETE`` command.

        Raises:
            DdirDeletedError: If this DDIR has already been deleted.

        Warns:
            TsoInvalidReturnCodeWarning: If the TSO ``DELETE`` command returns a
                return code greater than 4.
        """
        if self._delete_policy["is_deleted"]:
            raise DdirDeletedError()
        response = IpcsDdir._delete_ddir(self._dsname)
        self._delete_policy["is_deleted"] = True
        return response

    def sources(self) -> list[str]:
        """
        Return the source dump data set names described in the current DDIR.

        Runs a pyIPCS driver exec, which calls ``EVALDUMP`` to iterate
        all source descriptions in the current DDIR.

        Returns:
            list[str]: Source dump data set names described in the current DDIR.

        Raises:
            DdirDeletedError: If this DDIR has already been deleted.
            TsoInvalidReturnCodeError: If ``IPCSSRC`` returns a non-zero return
                code.

        References:
            - `EVALDUMP subcommand
              <https://www.ibm.com/docs/en/zos/3.2.0?topic=subcommands-evaldump-subcommand-format-dump-attributes>`_
        """
        response = self.run(f"ex '{self._driver}(IPCSSRC)'")
        if response.rc != 0:
            raise IpcsInvalidReturnCodeError(response)
        if not response.output:
            return []
        return [line.strip() for line in response.output.splitlines() if line.strip()]

    def init_dump(
        self,
        dump: IpcsDump,
    ) -> IpcsResponse:
        """
        Attempt initialization of a dump data set by running
        ``SETDEF LOCAL NOLIST DSNAME(<dump.dsname>)`` then the ``STATUS`` subcommand.

        Args:
            dump: Dump data set to initialize.

        Returns:
            IpcsResponse: IPCS response from running the ``STATUS`` subcommand.

        Raises:
            DdirDeletedError: If this DDIR has already been deleted.

        Note:
            This will not set the global source dump default. To run future
            subcommands against the dump data set you must specify the ``dump``
            parameter for :meth:`set_global_defaults` or :meth:`run`.

        References:
            - `SETDEF subcommand
              <https://www.ibm.com/docs/en/zos/3.2.0?topic=subcommands-setdef-subcommand-set-defaults>`_
            - `STATUS subcommand
              <https://www.ibm.com/docs/en/zos/3.2.0?topic=subcommands-status-subcommand-describe-system-status>`_
        """
        return self.run("STATUS", dump=dump)

    def drop_dump(
        self,
        dsname: str,
    ) -> IpcsResponse:
        """
        Delete a source description from the current dump directory (DDIR)
        by running ``DROPDUMP DSNAME(<dsname>)``.

        Args:
            dsname: Data set name of the dump to drop.

        Returns:
            IpcsResponse: Response from the ``DROPDUMP`` subcommand.

        Raises:
            DdirDeletedError: If this DDIR has already been deleted.
        """
        return self.run(f"DROPDUMP DSNAME('{dsname}')")

    def global_defaults(
        self,
        dump: Optional[IpcsDump] = None,
        parms: Optional[str | Iterable[str]] = None,
    ) -> IpcsResponse:
        """
        Global defaults for the current dump directory.

        Runs ``SETDEF LIST GLOBAL <parms>``. These defaults carry over to future
        subcommands for the current dump directory (DDIR).

        Args:
            dump: Dump data set. When provided, sets the global default source
                dump by adding ``DSNAME(<dump.dsname>)`` to ``parms``.
            parms: Additional parameters to pass to ``SETDEF LIST GLOBAL``.
                May be a single string (e.g. ``'FLAG(WARNING) CONFIRM(NO)'``)
                or an iterable of string parms
                (e.g. ``['FLAG(WARNING)', 'CONFIRM(NO)']``).
                Default is ``None`` (no additional parameters).

        Returns:
            IpcsResponse: IPCS response from the ``SETDEF`` subcommand.

        Raises:
            DdirDeletedError: If this DDIR has already been deleted.

        Note:
            Unsafe if multiple users share the same DDIR — this overwrites global
            defaults for the directory and may conflict with concurrent sessions.
            Use the ``dump``/``local_defaults`` parameters of :meth:`run` instead
            if you do not have exclusive access.

        References:
            - `SETDEF subcommand
              <https://www.ibm.com/docs/en/zos/3.2.0?topic=subcommands-setdef-subcommand-set-defaults>`_
        """
        if self._delete_policy["is_deleted"]:
            raise DdirDeletedError()
        subcmd = "SETDEF LIST GLOBAL"
        if dump is not None:
            subcmd += f" DSNAME('{dump.dsname}')"
        if parms is not None:
            if not isinstance(parms, str):
                parms = " ".join(parms)
            subcmd += f" {parms}"
        return self.run(subcmd)

    def run(
        self,
        subcmd: str,
        authorized: bool = False,
        dump: Optional[IpcsDump] = None,
        local_defaults: Optional[str | Iterable[str]] = None,
        output: Optional[IO[str]] = None,
    ) -> IpcsResponse:
        """
        Run an IPCS subcommand.

        Args:
            subcmd: IPCS subcommand to run.
            authorized: Indicates whether the subcommand will be run in an
                authorized environment. Default is ``False``.
            dump: Source dump data set to run the subcommand against. If
                provided, ``DSNAME(<dump.dsname>)`` is added to
                ``local_defaults``, so the source will not carry over to future
                subcommands. Default is ``None``.
            local_defaults: If non-empty, runs
                ``SETDEF NOLIST LOCAL <local_defaults>`` before running the
                specified subcommand. Note: the defaults set by this will not
                carry over to future subcommands. May be a single string
                (e.g. ``'FLAG(WARNING) CONFIRM(NO)'``) or an iterable of string
                parms (e.g. ``['FLAG(WARNING)', 'CONFIRM(NO)']``).
                Default is ``None`` to not run the ``SETDEF`` subcommand.
            output: An open, writable text file object. When provided,
                subcommand output is written to this file instead of being
                returned as a string (``output`` attribute will be ``None`` in
                the returned :class:`~pyipcs.IpcsResponse`).
                Default is ``None``.

        Returns:
            IpcsResponse: Response from the IPCS subcommand.

        Raises:
            DdirDeletedError: If this DDIR has already been deleted.
            ValueError: If the ``source`` data set is specified and does not
                exist.

        Note:
            A return code of 5 indicates that there was an error before the
            specified subcommand ran during the ``SETDEF NOLIST LOCAL``.

            If you have exclusive access to the DDIR, using
            :meth:`set_global_defaults` once up front is faster than passing
            ``dump``/``local_defaults`` per call, as it avoids a
            ``SETDEF NOLIST LOCAL`` on every invocation.

        References:
            - `SETDEF subcommand
              <https://www.ibm.com/docs/en/zos/3.2.0?topic=subcommands-setdef-subcommand-set-defaults>`_
        """
        if self._delete_policy["is_deleted"]:
            raise DdirDeletedError()

        # Pass Optional[str] to ipcs_subcmd
        parsed_local_defaults = None
        if dump is not None:
            parsed_local_defaults = f"DSNAME('{dump.dsname}')"
            if local_defaults is not None:
                if isinstance(local_defaults, str):
                    parsed_local_defaults += f" {local_defaults}"
                else:
                    parsed_local_defaults += f" {' '.join(local_defaults)}"

        return ipcs_subcmd(
            subcmd=subcmd,
            driver=self._driver,
            ddir=self._dsname,
            allocations=self._allocations,
            authorized=authorized,
            local_defaults=parsed_local_defaults,
            output=output,
        )

    @staticmethod
    def _delete_ddir(dsname: str) -> TsoResponse:
        """
        Issue the TSO ``DELETE`` command against *dsname*.

        Args:
            dsname: The fully-qualified data set name to delete.

        Returns:
            TsoResponse: Response from the ``DELETE`` command.

        Warns:
            TsoInvalidReturnCodeWarning: If the TSO ``DELETE`` command returns a
                return code greater than 4.
        """
        response = tso_cmd(
            cmd=f"DELETE '{dsname}'",
            allocations=[IpcsAllocation("PYIPCS", dsname)],
        )
        if response.rc > 4:
            warnings.warn(TsoInvalidReturnCodeWarning(response), stacklevel=3)
        return response

    @staticmethod
    def _blscddir(
        dsname: str,
        parms: Optional[str | Iterable[str]],
        allocations: list[IpcsAllocation],
    ) -> TsoResponse:
        """
        Run the ``BLSCDDIR`` CLIST to create or open a dump directory (DDIR).

        Args:
            dsname: The fully-qualified DDIR data set name.
            parms: Additional parameters to pass to ``BLSCDDIR``.
            allocations: IPCS allocations to use for the TSO command.

        Returns:
            TsoResponse: Response from the ``BLSCDDIR`` command.

        Raises:
            TsoInvalidReturnCodeError: If ``BLSCDDIR`` returns a return code >= 12.
        """
        if parms is None:
            parms_list: list[str] = []
        elif isinstance(parms, str):
            parms_list = [parms]
        else:
            parms_list = list(parms)
        cmd = f"%BLSCDDIR DSNAME('{dsname}')"
        if parms_list:
            cmd += f" {' '.join(parms_list)}"
        response = tso_cmd(
            cmd=cmd,
            allocations=allocations,
        )
        # BLSCDDIR only treats LASTCC >= 12 as a hard failure; lower codes
        # are soft warnings from subordinate TSO/VSAM services and are safe
        # to ignore (matching every LASTCC check within the CLIST itself).
        if response.rc >= 12:
            raise TsoInvalidReturnCodeError(response)
        return response

    @staticmethod
    def _validate_driver(dsname: str) -> None:
        """
        Validate an existing pyIPCS driver data set.

        Confirms the driver is valid and matches the current pyIPCS version.

        Args:
            dsname: The fully-qualified driver data set name.

        Raises:
            TsoError: If the driver is invalid or does not match the current
                pyIPCS version.
        """
        # Verify we are using the same pyIPCS version
        response = tso_cmd(
            cmd=f"ex '{dsname}(IPCSVERS)'",
            allocations=[IpcsAllocation("PYIPCS", [dsname])],
        )
        if response.rc != 0 or f"PYIPCS={__version__}" not in response.output:
            raise TsoError(
                f"pyIPCS driver data set {dsname} already exists and is invalid "
                f"or does not match the current pyIPCS version"
            )

    @staticmethod
    def _cleanup(dsname: str, delete_policy: dict) -> None:
        """
        Finalizer callback invoked for :class:`IpcsDdir`.

        Args:
            dsname: The fully-qualified DDIR data set name.
            delete_policy: The instance's ``_delete_policy`` dict, containing
                ``"delete"`` (whether to delete on cleanup) and ``"is_deleted"``
                (whether the DDIR has already been deleted).
        """
        if delete_policy["delete"] and not delete_policy["is_deleted"]:
            IpcsDdir._delete_ddir(dsname)
            delete_policy["is_deleted"] = True
