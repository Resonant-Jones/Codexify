from .codexify_export_gdrive import export_gdrive_cmd
from .codexify_oauth_begin import oauth_begin_cmd
from .codexify_oauth_status import oauth_status_cmd
from .codexify_save_entry import save_entry_cmd
from .imprint_zero_cli import ImprintZeroCommand as ImprintZero
from .memoryos_cli import cli

# Register additional memory-related commands
try:
    from guardian.cli.memory.embed import embed  # type: ignore
    from guardian.cli.memory.embed_diagnose import (
        embed_diagnose,  # type: ignore
    )

    cli.add_command(embed)
    cli.add_command(embed_diagnose)
except Exception:
    # Safe import in environments without optional deps
    pass

# Register codexify oauth status command
cli.add_command(oauth_status_cmd)
cli.add_command(oauth_begin_cmd)
cli.add_command(export_gdrive_cmd)
cli.add_command(save_entry_cmd)

__all__ = ["cli", "ImprintZero"]
