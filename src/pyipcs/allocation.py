"""
IpcsAllocation Object
"""

from collections.abc import Iterable


class IpcsAllocation:
    """
    Represents a single TSO allocation.

    Attributes
    ----------
    dd_name : str
        The DD name for this allocation.

    specification : str | list[str]
        String data set allocation request or list of cataloged datasets.
    """

    def __init__(self, dd_name: str, specification: str | Iterable[str]) -> None:
        """
        Constructor for IpcsAllocation Object.

        Parameters
        ----------
        dd_name : str
            The DD name for this allocation.

        specification : str | Iterable[str]
            String data set allocation request or iterable of cataloged datasets.

        Returns
        -------
        None
        """
        self._dd_name: str = dd_name.strip()
        self._specification: str | list[str]
        if isinstance(specification, str):
            self._specification = specification.strip()
        else:
            self._specification = [s.strip() for s in specification]

    @property
    def dd_name(self) -> str:
        return self._dd_name

    @property
    def specification(self) -> str | list[str]:
        return self._specification
