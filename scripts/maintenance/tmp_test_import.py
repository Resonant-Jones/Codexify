import importlib
import sys

sys.path.append(".")
mod = importlib.import_module("guardian.imprint_zero")
print("Has get_memoryos_instance?", hasattr(mod, "get_memoryos_instance"))
print("dir:", [x for x in dir(mod) if not x.startswith("__")])
