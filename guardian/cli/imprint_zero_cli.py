import json
import logging
from argparse import Namespace, _SubParsersAction

import typer

from guardian.cli.base_command import BaseCommand
from guardian.imprint_zero_onboarding import ImprintZero as ImprintZeroCore

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def _render_imprint_zero_prompt_dump(json_output: bool) -> str:
    # Single runtime path: the onboarding core resolves the prompt bundle.
    core = ImprintZeroCore()
    user_prompt = getattr(core, "question_scaffold", "")
    system_prompt = getattr(core, "system_prompt", "")
    if json_output:
        prompt_data = {
            "system_prompt": system_prompt,
            "question_scaffold": user_prompt,
        }
        return json.dumps(prompt_data, indent=2)
    return f"--- System Prompt ---\n{system_prompt}\n\n--- Question Scaffold ---\n{user_prompt}"


class ImprintZeroCommand(BaseCommand):
    @staticmethod
    def name() -> str:
        return "dump-imprint-zero-prompt"

    @staticmethod
    def help_text() -> str:
        return "Dump the ImprintZero prompt."

    def execute(self, args: Namespace) -> None:
        typer.echo(
            _render_imprint_zero_prompt_dump(
                getattr(args, "json_output", False)
            )
        )

    @classmethod
    def register(cls, subparsers: _SubParsersAction) -> None:
        parser = subparsers.add_parser(cls.name(), help=cls.help_text())
        parser.add_argument(
            "--json-output",
            "-j",
            action="store_true",
            help="Output in JSON format",
        )
        parser.set_defaults(func=cls.run)


# Typer-based CLI expected by tests
app = typer.Typer()
imprint_zero = typer.Typer(name="imprint-zero")
app.add_typer(imprint_zero)


@imprint_zero.command("dump-imprint-zero-prompt")
def dump_imprint_zero_prompt(
    json_output: bool = typer.Option(False, "--json-output", "-j")
):
    """Dump the ImprintZero prompt in text or JSON."""
    typer.echo(_render_imprint_zero_prompt_dump(json_output))
