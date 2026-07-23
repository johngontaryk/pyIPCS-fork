"""
IPCS Subcommand Function
"""

import subprocess
import tempfile
from typing import IO, Iterable, Optional
from pyipcs.allocation import IpcsAllocation
from pyipcs._tso_shell_script import tso_shell_script
from pyipcs.exceptions import TsoError


def ipcs_subcmd(
    subcmd: str,
    driver: str,
    ddir: str,
    allocations: Optional[IpcsAllocation | list[IpcsAllocation]] = None,
    authorized: bool = True,
    setdef_parms: Optional[str | Iterable[str]] = None,
    output: Optional[IO[str]] = None,
) -> dict:
    """
    Run an IPCS subcommand.

    Parameters
    ----------
    subcmd : str
        IPCS subcommand to run.

    driver : str
        Name of the pyIPCS driver data set (PDSE) that contains the IPCSRUN
        CLIST member.

    ddir : str
        Data set name of the dump directory (DDIR) to allocate to ``IPCSDDIR``
        for the subcommand.

    allocations : IpcsAllocation or list[IpcsAllocation], optional
        A single IpcsAllocation or a list of IpcsAllocation objects to set up
        before running the command. Default is None (no allocations).

    authorized : bool, optional
        Indicates whether the subcommand will be run in an authorized environment.

    setdef_parms : str or Iterable[str], optional
        If this parameter is provided will run ``SETDEF NOLIST LOCAL <setdef_parms>``
        before running the specified subcommand.
        Note: the defaults set by this will not carry over to future subcommands.
        May be a single string (e.g. ``'FLAG(WARNING) CONFIRM(NO)'``)
        or an iterable of strings (e.g. ``['FLAG(WARNING)', 'CONFIRM(NO)']``).
        Default is None to not run a ``SETDEF`` subcommand
        before running the specified subcommand.

    output : file object, optional
        An open, writable text file object. When provided, subcommand output is
        to this file instead of being returned as a string 
        (``"output"`` will be ``None``in returned dict).
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
    """
    if allocations is None:
        allocations = []
    elif isinstance(allocations, IpcsAllocation):
        allocations = [allocations]

    allocations = allocations + [IpcsAllocation("IPCSDDIR", [ddir])]

    # Construct IPCS subcommand
    escaped_subcmd = subcmd.strip().replace("'", "''''")
    cmd = f"ex '{driver}(IPCSRUN)' 'SUBCMD(''{escaped_subcmd}'')'"

    # Construct SETDEF LOCAL NOLIST subcommand to run before specified subcommand
    if setdef_parms is not None:
        setdef_str = setdef_parms if isinstance(setdef_parms, str) else " ".join(setdef_parms)
        escaped_setdef = setdef_str.replace("'", "''''")
        cmd += f" 'SETDEFPARMS(''{escaped_setdef}'')'"

    shell_script = tso_shell_script(
        cmd=cmd,
        authorized=authorized,
        allocations=allocations,
    )

    # Write output to temporary file first to ensure encoding of output
    with tempfile.NamedTemporaryFile(mode="w+", encoding="cp1047", delete=True) as tmp_file:
        try:
            completed_process = subprocess.run(
                shell_script,
                shell=True,
                stdout=tmp_file,
                stderr=subprocess.STDOUT,
                check=False,
            )
        except Exception as e:
            tmp_file.seek(0)
            for _ in range(3):
                tmp_file.readline()
            err_output = tmp_file.read()
            raise TsoError(
                f"Failed to run IPCS subcommand '{subcmd}'", output=err_output
            ) from e

        # Skip the first lines which are not output of the subcommand
        tmp_file.seek(0)
        for _ in range(3):
            tmp_file.readline()

        # Determine if file object was provided and pipe output if provided
        if output is not None:
            for line in tmp_file:
                output.write(line)
            subcmd_output = None
        else:
            # If no file object was provided read in rest of IPCS subcommand output
            subcmd_output = tmp_file.read()

    return {
        "subcmd": subcmd,
        "rc": completed_process.returncode,
        "output": subcmd_output,
        "authorized": authorized,
    }
