You are producing a Codex Runner campaign audit output. Return JSON that conforms to the campaign_output schema.

Requirements:
- Include campaign_id, campaign_slug, campaign_doc_path, campaign_markdown, and tasks.
- campaign_doc_path must match:
  docs/Campaign/CAMPAIGN_YYYY_MM_DD.md
  OR
  docs/Campaign/CAMPAIGN_YYYY_MM_DD_<UPPER_SNAKE+_->.md
- task_artifact_path must match:
  docs/tasks/TASK_YYYY_MM_DD_NNN_lower_snake_slug.md
  where NNN is a 3-digit zero-padded number.
- Provide full markdown contents for campaign_markdown and task_artifact_markdown.
- Provide a fully formed activation_prompt for each task.

Do not invent additional top-level fields or task fields. Ensure the output passes JSON schema validation.
