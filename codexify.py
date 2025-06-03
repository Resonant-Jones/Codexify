

import re
import json
import os
from datetime import datetime

# --- LLM Summarization Council Logic ---
from dotenv import load_dotenv
load_dotenv()

# Nebius: OpenAI-compatible client
try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

def summarize_with_nebius(content):
    if not OpenAI:
        return "Nebius OpenAI client not installed."
    api_key = os.environ.get("NEBIUS_API_KEY")
    if not api_key:
        return "NEBIUS_API_KEY not set in environment."
    client = OpenAI(
        base_url="https://api.studio.nebius.ai/v1/",
        api_key=api_key,
    )
    try:
        response = client.chat.completions.create(
            model="meta-llama/Meta-Llama-3.1-405B-Instruct",
            messages=[
                {"role": "user", "content": f"Summarize the following:\n{content}"}
            ],
            temperature=0.6
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Nebius summary failed: {e}"

# Gemini: Google SDK
try:
    from google.generativeai import GenerativeModel
except ImportError:
    GenerativeModel = None

def summarize_with_gemini(content):
    if not GenerativeModel:
        return "Gemini SDK not installed."
    try:
        model = GenerativeModel("gemini-1.5-pro-latest")
        response = model.generate_content(
            f"Summarize the following:\n{content}"
        )
        return response.text
    except Exception as e:
        return f"Gemini summary failed: {e}"

LLM_COUNCIL = {
    "nebius": summarize_with_nebius,
    "gemini": summarize_with_gemini,
    # Add other models here as needed
}

def council_summarize(content, models=None, arbiter=None):
    if not models:
        models = list(LLM_COUNCIL.keys())
    votes = {}
    for model in models:
        votes[model] = LLM_COUNCIL[model](content)
    if arbiter and arbiter in LLM_COUNCIL:
        combined = "\n".join(f"{k}: {v}" for k, v in votes.items())
        return LLM_COUNCIL[arbiter](f"Given these summaries, pick or synthesize:\n{combined}")
    return votes

def flow_summarize(content, model_order=None):
    if not model_order:
        model_order = ["nebius", "gemini"]
    current = content
    for model in model_order:
        current = LLM_COUNCIL[model](current)
    return current

def summarize_entry(entry, mode="auto", council_models=None, flow_order=None, arbiter=None):
    content = entry.get("content", "")
    if not content:
        return ""
    if mode == "council":
        return council_summarize(content, models=council_models, arbiter=arbiter)
    elif mode == "flow":
        return flow_summarize(content, model_order=flow_order)
    elif mode == "background":
        return LLM_COUNCIL.get("nebius", lambda c: c)(content)
    elif mode == "gemini":
        return summarize_with_gemini(content)
    elif mode == "nebius":
        return summarize_with_nebius(content)
    # Default: fast/dumb summarizer
    return content.split(".")[0][:100] + ("..." if len(content) > 100 else "")

def parse_markdown_to_entries(md_text, agent="Guardian", tag=None):
    """
    Parses Markdown into a list of codex entries.
    Each top-level heading (#, ##) is a separate entry.
    """
    entries = []
    # Split on headings
    chunks = re.split(r'(^#+ .*$)', md_text, flags=re.MULTILINE)
    current_entry = {"content": "", "title": None, "timestamp": None}
    for chunk in chunks:
        if re.match(r'^#+ ', chunk):
            # Save previous entry if any
            if current_entry["content"]:
                entry = {
                    "timestamp": current_entry.get("timestamp") or datetime.now().isoformat(),
                    "title": current_entry["title"],
                    "content": current_entry["content"].strip(),
                    "tag": tag or "imported_md",
                    "agent": agent,
                    "source": "markdown"
                }
                entries.append(entry)
            current_entry = {"content": "", "title": chunk.strip("# ").strip(), "timestamp": None}
        else:
            current_entry["content"] += chunk
    # Save last entry
    if current_entry["content"]:
        entry = {
            "timestamp": current_entry.get("timestamp") or datetime.now().isoformat(),
            "title": current_entry["title"],
            "content": current_entry["content"].strip(),
            "tag": tag or "imported_md",
            "agent": agent,
            "source": "markdown"
        }
        entries.append(entry)
    return entries

def parse_json_to_entries(json_blob, agent="Guardian", tag=None):
    """
    Parses JSON blob/list into Codex entries. Expects a list of dicts.
    """
    try:
        if isinstance(json_blob, str):
            records = json.loads(json_blob)
        else:
            records = json_blob
    except Exception as e:
        raise ValueError("Could not decode JSON: %s" % e)

    entries = []
    for r in records:
        entry = {
            "timestamp": r.get("timestamp", datetime.now().isoformat()),
            "title": r.get("title"),
            "content": r.get("content") or r.get("command", ""),
            "tag": tag or r.get("tag", "imported_json"),
            "agent": r.get("agent", agent),
            "source": r.get("source", "json")
        }
        entries.append(entry)
    return entries

# summarize_entry is now replaced/extended above with LLM logic.

def enrich_with_tags(entry):
    """
    Stub for keyword/tag extraction from content.
    Replace with LLM or custom logic if desired.
    """
    content = entry.get("content", "")
    # Dummy tag extraction: extract words over 5 chars as 'tags'
    tags = [w for w in re.findall(r'\b\w+\b', content) if len(w) > 5]
    return list(set(tags)) if tags else ["general"]

# Core function: parse, enrich, codexify
def codexify_file(file_path, filetype=None, agent="Guardian"):
    """
    Main processing entry point: detect file type, parse, enrich, return entries.
    """
    ext = filetype or file_path.split(".")[-1].lower()
    with open(file_path, "r", encoding="utf-8") as f:
        raw = f.read()
    if ext == "md":
        entries = parse_markdown_to_entries(raw, agent=agent)
    elif ext == "json":
        entries = parse_json_to_entries(raw, agent=agent)
    else:
        # Treat as plain text
        entries = [{
            "timestamp": datetime.now().isoformat(),
            "title": None,
            "content": raw,
            "tag": "imported_txt",
            "agent": agent,
            "source": ext
        }]
    # Enrich with summaries and tags
    for entry in entries:
        entry["summary"] = summarize_entry(entry)
        entry["extracted_tags"] = enrich_with_tags(entry)
    return entries