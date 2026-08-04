"""
TSO Command Function
"""
# pylint: disable=duplicate-code

import subprocess
import tempfile
from typing import Optional
from pyipcs.allocation import IpcsAllocation
from pyipcs._tso_shell_script import tso_shell_script
from pyipcs.exceptions import TsoError
from pyipcs.response import TsoResponse


def tso_cmd(
    cmd: str,
    allocations: Optional[list[IpcsAllocation]] = None,
) -> TsoResponse:
    """
    Run a TSO/E command.

    Args:
        cmd: TSO/E command to run.
        allocations: List of :class:`~pyipcs.IpcsAllocation` objects to set up
            before running the command. Default is ``None`` (no allocations).

    Returns:
        TsoResponse: Response from the TSO/E command.
    """
    if allocations is None:
        allocations = []

    shell_script = tso_shell_script(
        cmd=cmd,
        authorized=True,
        allocations=allocations,
    )

    # Write output to temporary file first to ensure encoding of output
    with tempfile.NamedTemporaryFile(
        mode="w+", encoding="cp1047", delete=True
    ) as tmp_file:
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
            raise TsoError(f"Failed to run TSO/E command '{cmd}'", output=output) from e

        tmp_file.seek(0)
        output = tmp_file.read()

    return TsoResponse(
        cmd=cmd,
        rc=completed_process.returncode,
        output=output,
        authorized=True,
    )
