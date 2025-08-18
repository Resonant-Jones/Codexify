DESTRUCTIVE = {"gm:init_db", "gm:init_threads_table_cmd", "gm:generate_codemap"}


def require_confirm(name: str, args: dict):
    if name in DESTRUCTIVE and not (args or {}).get("confirm", False):
        raise RuntimeError(f"{name} requires confirm=true")

