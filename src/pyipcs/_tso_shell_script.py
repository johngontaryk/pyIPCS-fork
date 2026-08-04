"""
TSO Shell Script
"""

from pyipcs.allocation import IpcsAllocation

_TSO_SHELL_SCRIPT = """
# TSO Shell Script
# Shell Script to run TSO/E Command with allocations

# Use parenthesis around shell commands to create a subshell
(

# List all DD names in TSOALLOC export
{tsoalloc};

# TSO/E allocation specifications export statements
# Specifications are strings or concatenation of datasets separated by colon
{allocation_exports}

{tso_or_tsocmd} "{cmd}"

)
"""


def tso_shell_script(
    cmd: str,
    authorized: bool,
    allocations: list[IpcsAllocation],
) -> str:
    """
    Build the TSO shell script string from the given parameters.

    Args:
        cmd: TSO/E command to run.
        authorized: If ``True``, uses the ``tsocmd`` shell command which can issue
            authorized TSO/E commands via the TSO/E terminal monitor program
            (IKJEFT01). If ``False``, uses the ``tso`` shell command which sets up
            a mini TSO/E environment in a new address space through the OMVS
            interface.
        allocations: List of :class:`~pyipcs.IpcsAllocation` objects to set up
            before running the command.

    Returns:
        str: TSO shell script.
    """
    tsoalloc = (
        "export TSOALLOC=" + ":".join(a.dd_name for a in allocations)
        if allocations
        else ""
    )
    allocation_exports = "\n".join(
        (
            f'export {alloc.dd_name}="{alloc.specification}";'
            if isinstance(alloc.specification, str)
            else f"export {alloc.dd_name}={':'.join(alloc.specification)};"
        )
        for alloc in allocations
    )
    return _TSO_SHELL_SCRIPT.format(
        tsoalloc=tsoalloc,
        allocation_exports=allocation_exports,
        cmd=cmd,
        tso_or_tsocmd="tsocmd" if authorized else "tso",
    )
