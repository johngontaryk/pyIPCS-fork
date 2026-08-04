"""
IpcsAllocation Object
"""

from collections.abc import Iterable


class IpcsAllocation:
    """
    Represents a single TSO allocation.
    """

    def __init__(self, dd_name: str, specification: str | Iterable[str]) -> None:
        """
        Constructor for :class:`IpcsAllocation`.

        Args:
            dd_name: The DD name for this allocation.
            specification: String data set allocation request or iterable of
                cataloged datasets.
        """
        self._dd_name: str = dd_name.strip()
        self._specification: str | list[str]
        if isinstance(specification, str):
            self._specification = specification.strip()
        else:
            self._specification = [s.strip() for s in specification]

    @property
    def dd_name(self) -> str:
        """The DD name for this allocation."""
        return self._dd_name

    @property
    def specification(self) -> str | list[str]:
        """String data set allocation request or list of cataloged datasets."""
        return self._specification
