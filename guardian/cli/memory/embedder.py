import click

from guardian.cli.memory.embedder import embed

cli = click.Group()

cli.add_command(embed)
