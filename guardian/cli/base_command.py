from __future__ import annotations

import abc
from argparse import Namespace, _SubParsersAction
from guardian.logging_config import logger as Logger


class BaseCommand(abc.ABC):
    """Abstract Base Command class for CLI commands."""

    _logger = Logger

    @abc.abstractmethod
    def execute(self, args: Namespace) -> None:
        """Execute the command."""
        # TODO: Implement command logic
        self._logger.info("Executing command...")

    @classmethod
    def register(cls, subparsers: _SubParsersAction) -> None:
        """Register the command with argparse."""
        parser = subparsers.add_parser(
            # TODO: Set command name
            "command-name",
            help="TODO: Add help text",  # TODO: Add help text
        )
        # TODO: Define arguments
        # parser.add_argument(...) 
        parser.set_defaults(func=cls.run)

    @classmethod
    def run(cls, args: Namespace) -> None:
        """Entry point for command execution."""
        command = cls()
        command.execute(args)
