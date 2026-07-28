"""
TsoResponse and IpcsResponse Objects
"""

from typing import Optional


class TsoResponse:
    """
    Response from running a TSO/E command.

    Attributes
    ----------
    cmd : str
        The TSO/E command that was run.
    rc : int
        Return code of the TSO/E command.
    output : str
        Output from the TSO/E command.
    authorized : bool
        Whether the command ran in an authorized environment.
    """

    def __init__(self, cmd: str, rc: int, output: str, authorized: bool) -> None:
        self._cmd = cmd
        self._rc = rc
        self._output = output
        self._authorized = authorized

    @property
    def cmd(self) -> str:
        return self._cmd

    @property
    def rc(self) -> int:
        return self._rc

    @property
    def output(self) -> str:
        return self._output

    @property
    def authorized(self) -> bool:
        return self._authorized

    def __repr__(self) -> str:
        return (
            f"TsoResponse(cmd={self._cmd!r}, rc={self._rc!r}, "
            f"authorized={self._authorized!r})"
        )


class IpcsResponse:
    """
    Response from running an IPCS subcommand.

    Attributes
    ----------
    subcmd : str
        The IPCS subcommand that was run.
    rc : int
        Return code of the IPCS subcommand.
    output : str or None
        Output from the IPCS subcommand, or ``None`` if a file object was
        provided via the ``output`` parameter.
    authorized : bool
        Whether the subcommand ran in an authorized environment.
    """

    def __init__(
        self,
        subcmd: str,
        rc: int,
        output: Optional[str],
        authorized: bool,
    ) -> None:
        self._subcmd = subcmd
        self._rc = rc
        self._output = output
        self._authorized = authorized

    @property
    def subcmd(self) -> str:
        return self._subcmd

    @property
    def rc(self) -> int:
        return self._rc

    @property
    def output(self) -> Optional[str]:
        return self._output

    @property
    def authorized(self) -> bool:
        return self._authorized

    def __repr__(self) -> str:
        return (
            f"IpcsResponse(subcmd={self._subcmd!r}, rc={self._rc!r}, "
            f"authorized={self._authorized!r})"
        )
