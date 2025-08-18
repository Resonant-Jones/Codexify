You are Codex. Apply the following patch set exactly.
Also load: codex_tasks/safe_task.md

TITLE: Add Python-level defaults to embed CLI callbacks so invoker can call them without Click

GOAL

- Ensure guardian CLI callbacks have default values on the function signature that match Click option defaults.
- Fixes TUI errors like “embed() missing positional argument: 'model'”.

PATCH
***Begin Patch
*** Update File: guardian/cli/memory/embed.py
@@
-import click
-from guardian.runtime.embed.embedder import embed_file
+import click
+from typing import Optional
+from guardian.runtime.embed.embedder import embed_file

 @click.command(name="embed")
<-@click.option>("--path", default="chunked_docs.txt", show_default=True, help="Input file (chunks separated by blank lines).")
<-@click.option>("--use-openai/--use-local", default=True, show_default=True, help="Use OpenAI API or local model.")
<-@click.option>("--model", default=None, help="Override embedding model name.")
<-@click.option>("--store", type=click.Choice(["chroma", "faiss"]), default="chroma", show_default=True, help="Vector store backend.")
<-@click.option>("--chroma-path", default="./.chroma", show_default=True, help="Chroma persistence path.")
<-@click.option>("--collection", default="codexify_vault", show_default=True, help="Chroma collection name.")
-def embed(path, use_openai, model, store, chroma_path, collection):
<+@click.option>("--path", default="chunked_docs.txt", show_default=True, help="Input file (chunks separated by blank lines).")
<+@click.option>("--use-openai/--use-local", default=True, show_default=True, help="Use OpenAI API or local model.")
<+@click.option>("--model", default=None, help="Override embedding model name.")
<+@click.option>("--store", type=click.Choice(["chroma", "faiss"]), default="chroma", show_default=True, help="Vector store backend.")
<+@click.option>("--chroma-path", default="./.chroma", show_default=True, help="Chroma persistence path.")
<+@click.option>("--collection", default="codexify_vault", show_default=True, help="Chroma collection name.")
+def embed(
- path: str = "chunked_docs.txt",
- use_openai: bool = True,
- model: Optional[str] = None,
- store: str = "chroma",
- chroma_path: str = "./.chroma",
- collection: str = "codexify_vault",
+):
     """Embed and index documents into the configured vector store."""
     result = embed_file(
         path=path,
         use_openai=use_openai,
         model=model,
         store=store,
         chroma_path=chroma_path,
         collection=collection,
     )
     click.echo(f"Embedded {result['count']} docs → store={result['store']}")
*** End Patch




PROMPT DONT LEAVE IN HERE
printf '%s\n' \
  "Your task is in: codex_tasks/2025-08-13-fix-embed-callback-defaults.md" \
  "Also load: codex_tasks/safe_task.md" \
  "Apply BOTH exactly as written. Obey all guardrails in safe_task.md." \
  > codex_tasks/run_with_safety.md

codex run --from-file codex_tasks/run_with_safety.md
