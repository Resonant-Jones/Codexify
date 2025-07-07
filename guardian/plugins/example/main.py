from guardian.plugins.plugin_base import PluginBase


class ExamplePlugin(PluginBase):
    """Minimal example plugin."""

    @property
    def name(self) -> str:
        return "example"

    @property
    def version(self) -> str:
        return "0.1.0"

    def activate(self, core_services):
        pass

    def register_cli(self, cli):
        pass
