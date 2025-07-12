import ast
import json
import os

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))


def extract_python_metadata(file_path):
    with open(file_path, "r", encoding="utf-8", errors="replace") as f:
        try:
            tree = ast.parse(f.read(), filename=file_path)
        except SyntaxError:
            return None

    functions = []
    classes = []

    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            functions.append({"name": node.name, "docstring": ast.get_docstring(node)})
        elif isinstance(node, ast.ClassDef):
            classes.append({"name": node.name, "docstring": ast.get_docstring(node)})

    return {"functions": functions, "classes": classes}


def generate_codemap():
    codemap = []

    for root, _, files in os.walk(BASE_DIR):
        for file in files:
            if file.endswith(".py"):
                full_path = os.path.join(root, file)
                rel_path = os.path.relpath(full_path, BASE_DIR)
                metadata = extract_python_metadata(full_path)
                if metadata:
                    codemap.append(
                        {"path": rel_path, "type": "python", "metadata": metadata}
                    )

    os.makedirs(os.path.join(BASE_DIR, "guardian/codemap"), exist_ok=True)
    output_path = os.path.join(BASE_DIR, "guardian/codemap/codemap.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(codemap, f, indent=2)

    print(f"Codemap written to {output_path}")
    return codemap


if __name__ == "__main__":
    generate_codemap()
