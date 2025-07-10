import typer
import json
from guardian.imprint_zero import ImprintZero as ImprintZeroCore

ImprintZero = typer.Typer()

@ImprintZero.command("dump-imprint-zero-prompt")
def dump_imprint_zero_prompt(json_output: bool = typer.Option(False, "--json-output", "-j", help="Output in JSON format")):
    """Dump the ImprintZero prompt."""
    core = ImprintZeroCore()
    user_prompt = getattr(core, "question_scaffold", "")
    system_prompt = getattr(core, "system_prompt", "")

    if json_output:
        prompt_data = {
            "system_prompt": system_prompt,
            "question_scaffold": user_prompt,
        }
        typer.echo(json.dumps(prompt_data, indent=2))
    else:
        text = f"--- System Prompt ---\n{system_prompt}\n\n--- Question Scaffold ---\n{user_prompt}"
        typer.echo(text)
