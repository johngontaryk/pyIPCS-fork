"""
IPCS Subcommand Function
"""
# pylint: disable=duplicate-code

import subprocess
import tempfile
from typing import IO, Iterable, Optional
from pyipcs.allocation import IpcsAllocation
from pyipcs._tso_shell_script import tso_shell_script
from pyipcs.exceptions import TsoError, IpcsError
from pyipcs.response import IpcsResponse


def ipcs_subcmd(
    subcmd: str,
    driver: str,
    ddir: str,
    allocations: list[IpcsAllocation],
    authorized: bool,
    local_defaults: Optional[str] = None,
    output: Optional[IO[str]] = None,
) -> IpcsResponse:
    """
    Run an IPCS subcommand.

    Args:
        subcmd: IPCS subcommand to run.
        driver: Name of the pyIPCS driver data set (PDSE) that contains the
            IPCSRUN CLIST member.
        ddir: Data set name of the dump directory (DDIR) to allocate to
            ``IPCSDDIR`` for the subcommand.
        allocations: List of :class:`~pyipcs.IpcsAllocation` objects.
        authorized: Indicates whether the subcommand will be run in an
            authorized environment.
        local_defaults: If non-empty, runs
            ``SETDEF NOLIST LOCAL <local_defaults>`` before running the
            specified subcommand. Note: the defaults set by this will not carry
            over to future subcommands. May be a single string
            (e.g. ``'FLAG(WARNING) CONFIRM(NO)'``). Default is ``None`` to not
            run a ``SETDEF`` subcommand before running the specified subcommand.
        output: An open, writable text file object. When provided, subcommand
            output is written to this file instead of being returned as a string
            (``output`` attribute will be ``None`` in the returned
            :class:`~pyipcs.IpcsResponse`). Default is ``None``.

    Returns:
        IpcsResponse: Response from the IPCS subcommand.
    """
    allocations = allocations + [IpcsAllocation("IPCSDDIR", [ddir])]

    # Construct IPCS subcommand
    escaped_subcmd = subcmd.strip().replace("'", "''''")

    # Construct full SETDEF LOCAL NOLIST subcommand to run before specified subcommand
    if local_defaults:
        escaped_setdef = local_defaults.replace("'", "''''")
        cmd = (
            f"ex '{driver}(IPCSRUN)' "
            f"'SUBCMD(''{escaped_subcmd}'') "
            f"SETDEFLOCAL(''SETDEF NOLIST LOCAL {escaped_setdef}'')'"
        )
    else:
        cmd = f"ex '{driver}(IPCSRUN)' 'SUBCMD(''{escaped_subcmd}'')'"

    shell_script = tso_shell_script(
        cmd=cmd,
        authorized=authorized,
        allocations=allocations,
    )

    # Write output to temporary file first to ensure encoding of output
    with tempfile.NamedTemporaryFile(
        mode="w+", encoding="cp1047", delete=True
    ) as tmp_file:
        try:
            subprocess.run(
                shell_script,
                shell=True,
                stdout=tmp_file,
                stderr=subprocess.STDOUT,
                check=True,
            )
        except Exception as e:
            tmp_file.seek(0)
            for _ in range(3):
                tmp_file.readline()
            err_output = tmp_file.read()
            raise TsoError(
                f"Failed to execute IPCS process for subcommand '{subcmd}'",
                output=err_output,
            ) from e

        # Skip the first lines which are not output of the subcommand
        tmp_file.seek(0)
        for _ in range(3):
            tmp_file.readline()

        # Determine if file object was provided and pipe output if provided
        pyipcs_rc = None
        if output is not None:
            for line in tmp_file:
                if line.startswith("PYIPCS_RC="):
                    pyipcs_rc = int(line.strip().split("=", 1)[1])
                    break
                output.write(line)
            subcmd_output = None
        else:
            # If no file object was provided read in rest of IPCS subcommand output
            lines = []
            for line in tmp_file:
                if line.startswith("PYIPCS_RC="):
                    pyipcs_rc = int(line.strip().split("=", 1)[1])
                    break
                lines.append(line)
            subcmd_output = "".join(lines)

    if pyipcs_rc is None:
        raise IpcsError(
            f"Could not find return code output during pyIPCS driver execution "
            f"while running IPCS subcommand '{subcmd}'",
            output=subcmd_output if subcmd_output is not None else "",
        )

    return IpcsResponse(
        subcmd=subcmd,
        rc=pyipcs_rc,
        output=subcmd_output,
        authorized=authorized,
    )
