import time
from guardian.chat.cli import plugin_cli

def test_cli_startup_benchmark(benchmark):
    start = time.time()
    plugin_cli.main(['--help'])
    duration = time.time() - start
    benchmark(lambda: None)  # record baseline
    assert duration < 1.0
