


## Plugin Test Placement

✅ Each plugin in `guardian/plugins/` should contain its own `tests/` directory.

✅ Always include an `__init__.py` file inside each `tests/` folder to ensure proper package discovery.

✅ Use absolute imports inside test files:
  For example:
  from guardian.plugins.pattern_analyzer.main import PatternAnalyzer

✅ Run all tests from the project root with:
  export PYTHONPATH=$(pwd)
  pytest guardian/

✅ Do not move plugin tests to the root `/tests` directory. Keep them co-located with their plugin logic to maintain modular integrity and make it easy for plugin developers to contribute consistent tests.