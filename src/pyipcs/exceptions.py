"""
pyIPCS Exceptions
"""

from pyipcs.response import TsoResponse, IpcsResponse


class TsoError(Exception):
    """
    Base level exception for TSO/E errors.
    """

    def __init__(self, message: str, output: str = "") -> None:
        """
        Constructor for TsoError.

        Parameters
        ----------
        message : str
            Error message.
        output : str, optional
            Output captured before the error occurred. Default is ``""``.

        Returns
        -------
        None
        """
        self._output: str = output
        full_message = message
        if output:
            full_message += f"\n[OUTPUT]:\n{output}"
        super().__init__(full_message)

    @property
    def output(self) -> str:
        return self._output


class TsoInvalidReturnCodeError(TsoError):
    """
    TSO/E error for an invalid return code from a TSO command.
    """

    def __init__(self, response: TsoResponse) -> None:
        """
        Constructor for TsoInvalidReturnCodeError.

        Parameters
        ----------
        response : TsoResponse
            TSO response.

        Returns
        -------
        None
        """
        self._response = response
        super().__init__(
            f"TSO command {response.cmd} "
            f"(authorized={response.authorized}) "
            f"exited with an invalid return code {response.rc}.",
            output=response.output,
        )

    @property
    def response(self):
        return self._response


class IpcsError(TsoError):
    """
    Base level exception for IPCS errors.
    """

    def __init__(self, message: str, output: str = "") -> None:
        """
        Constructor for IpcsError.

        Parameters
        ----------
        message : str
            Error message.
        output : str, optional
            Output captured before the error occurred. Default is ``""``.

        Returns
        -------
        None
        """
        self._output: str = output
        super().__init__(message, output=output)

    @property
    def output(self) -> str:
        return self._output


class IpcsInvalidReturnCodeError(TsoError):
    """
    IPCS error for an invalid return code while trying to run an IPCS subcommand.
    """

    def __init__(self, response: IpcsResponse) -> None:
        """
        Constructor for IpcsInvalidReturnCodeError.

        Parameters
        ----------
        response : IpcsResponse
            IPCS response.

        Returns
        -------
        None
        """
        self._response = response
        super().__init__(
            f"IPCS subcommand {response.subcmd!r} "
            f"(authorized={response.authorized}) "
            f"exited with an invalid return code {response.rc}.",
            output=response.output if response.output is not None else "",
        )

    @property
    def response(self):
        return self._response


class DdirNotSet(TsoError):
    """
    Exception raised when no dump directory (DDIR) is set for the pyIPCS session.
    """

    def __init__(self) -> None:
        super().__init__(
            "There is no current dump directory (DDIR) set for your pyIPCS session"
            " - use set_ddir to set one before running subcommands"
        )
