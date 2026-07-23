"""
TSO Command Function
"""

import subprocess
import tempfile
from typing import Optional
from pyipcs.allocation import IpcsAllocation
from pyipcs._tso_shell_script import tso_shell_script
from pyipcs.exceptions import TsoError


def tso_cmd(
    cmd: str,
    allocations: Optional[IpcsAllocation | list[IpcsAllocation]] = None,
) -> dict:
    """
    Run a TSO/E command.

    Parameters
    ----------
    cmd : str
        TSO/E command to run.

    allocations : IpcsAllocation or list[IpcsAllocation], optional
        A single IpcsAllocation or a list of IpcsAllocation objects to set up
        before running the command. Default is None (no allocations).

    Returns
    -------
    dict
        Dictionary with keys:

        - ``cmd`` : str — the TSO/E command that was run.
        - ``rc`` : int — return code of the TSO command.
        - ``output`` : str — output from the TSO/E command.
    """
    if allocations is None:
        allocations = []
    elif isinstance(allocations, IpcsAllocation):
        allocations = [allocations]

    shell_script = tso_shell_script(
        cmd=cmd,
        authorized=True,
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
            output = tmp_file.read()
            raise TsoError(
                f"Failed to run TSO/E command '{cmd}'", output=output
            ) from e

        tmp_file.seek(0)
        output = tmp_file.read()

    return {
        "cmd": cmd,
        "rc": completed_process.returncode,
        "output": output,
    }
