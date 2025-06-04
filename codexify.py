def markdown_to_notion_blocks(md_text):
    """
    Converts markdown to Notion-style block objects (headings, bullets, code, quotes, todos, etc.).
    Uses mistune for AST parsing and robust mapping.
    """
    import mistune  # You may need: pip install mistune
    renderer = mistune.create_markdown(renderer=mistune.AstRenderer())
    ast = renderer(md_text)
    blocks = []
    for node in ast:
        if node["type"] == "heading":
            level = node["level"]
            text = "".join(child.get("text", "") if isinstance(child, dict) else str(child)
                           for child in node.get("children", [])) if "children" in node else node["text"]
            block_type = f"heading_{min(level, 3)}"
            blocks.append({
                "type": block_type,
                "block": {
                    block_type: {
                        "rich_text": [{"type": "text", "text": {"content": text}}]
                    }
                }
            })
        elif node["type"] == "list":
            for item in node["children"]:
                block_type = "bulleted_list_item" if node["ordered"] is False else "numbered_list_item"
                text = "".join(child.get("text", "") if isinstance(child, dict) else str(child)
                               for child in item.get("children", [])) if "children" in item else item["text"]
                blocks.append({
                    "type": block_type,
                    "block": {
                        block_type: {
                            "rich_text": [{"type": "text", "text": {"content": text}}]
                        }
                    }
                })
        elif node["type"] == "block_code":
            blocks.append({
                "type": "code",
                "block": {
                    "code": {
                        "rich_text": [{"type": "text", "text": {"content": node["text"]}}],
                        "language": node.get("info") or "plain text"
                    }
                }
            })
        elif node["type"] == "block_quote":
            text = "".join(child.get("text", "") if isinstance(child, dict) else str(child)
                           for child in node.get("children", [])) if "children" in node else node.get("text", "")
            blocks.append({
                "type": "quote",
                "block": {
                    "quote": {
                        "rich_text": [{"type": "text", "text": {"content": text}}]
                    }
                }
            })
        elif node["type"] == "task_list":
            # Notion does not have a native todo block, so map to to-do
            for item in node["children"]:
                checked = item.get("checked", False)
                text = "".join(child.get("text", "") if isinstance(child, dict) else str(child)
                               for child in item.get("children", [])) if "children" in item else item.get("text", "")
                blocks.append({
                    "type": "to_do",
                    "block": {
                        "to_do": {
                            "rich_text": [{"type": "text", "text": {"content": text}}],
                            "checked": checked
                        }
                    }
                })
        elif node["type"] == "paragraph":
            text = "".join(child.get("text", "") if isinstance(child, dict) else str(child)
                           for child in node.get("children", [])) if "children" in node else node.get("text", "")
            blocks.append({
                "type": "paragraph",
                "block": {
                    "paragraph": {
                        "rich_text": [{"type": "text", "text": {"content": text}}]
                    }
                }
            })
        # Extend: add toggle, image, etc. as needed
    return blocks

def flatten_notion_blocks(blocks):
    """
    Returns a list of Notion block dicts (API-ready).
    """
    return [b["block"] for b in blocks if "block" in b]