from guardian.cli.memory.embedder import embed

import click

cli = click.Group()

cli.add_command(embed)