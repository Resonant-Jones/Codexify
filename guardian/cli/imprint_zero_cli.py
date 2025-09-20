import json
from argparse import Namespace, _SubParsersAction
from pathlib import Path

import typer

from guardian import imprint_zero as imprint_facade
from guardian.cli.base_command import BaseCommand
from guardian.imprint_zero_onboarding import ImprintZero as ImprintZeroCore


class ImprintZeroCommand(BaseCommand):
    @staticmethod
    def name() -> str:
        return "dump-imprint-zero-prompt"

    @staticmethod
    def help_text() -> str:
        return "Dump the ImprintZero prompt."

    def execute(self, args: Namespace) -> None:
        core = ImprintZeroCore()
        user_prompt = getattr(core, "question_scaffold", "")
        system_prompt = getattr(core, "system_prompt", "")
        if getattr(args, "json_output", False):
            prompt_data = {
                "system_prompt": system_prompt,
                "question_scaffold": user_prompt,
            }
            print(json.dumps(prompt_data, indent=2))
        else:
            text = f"--- System Prompt ---\n{system_prompt}\n\n--- Question Scaffold ---\n{user_prompt}"
            print(text)

    @classmethod
    def register(cls, subparsers: _SubParsersAction) -> None:
        parser = subparsers.add_parser(cls.name(), help=cls.help_text())
        parser.add_argument(
            "--json-output", "-j", action="store_true", help="Output in JSON format"
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
    # Prefer prompt files from guardian.imprint_zero.settings if provided (for tests)
    dir_path = getattr(
        getattr(imprint_facade, "settings", object()), "PROMPT_DIR_PATH", ""
    )
    system_prompt = None
    question_scaffold = None
    if dir_path:
        p = Path(dir_path)
        try:
            system_prompt = (p / "imprint_zero_system_prompt.md").read_text()
            question_scaffold = (p / "imprint_zero_question_scaffold.md").read_text()
        except Exception:
            system_prompt = None
            question_scaffold = None

    if system_prompt is None or question_scaffold is None:
        # Fallback to the core agent
        ImprintZeroCommand().execute(Namespace(json_output=json_output))
        return

    if json_output:
        print(
            json.dumps(
                {
                    "system_prompt": system_prompt,
                    "question_scaffold": question_scaffold,
                },
                indent=2,
            )
        )
    else:
        print(
            f"--- System Prompt ---\n{system_prompt}\n\n--- Question Scaffold ---\n{question_scaffold}"
        )
