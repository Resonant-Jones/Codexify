import os

import json
import click
from memoryos.memoryos import Memoryos
from memoryos.embedders.local_embedder import LocalEmbedder


def get_memory_instance():
    user_id = "default"
    openai_api_key = os.getenv("OPENAI_API_KEY", "sk-...")  # Replace as needed
    data_storage_path = "./data"
    embedder = LocalEmbedder()
    memory = Memoryos(
        user_id=user_id,
        llm_api_key=openai_api_key,
        data_storage_path=data_storage_path,
        embedder=embedder,
    )
    return memory


@click.group()
def cli():
    pass


@cli.command("codemap:query")
@click.argument("question", type=str)
def codemap_query(question):
    """Ask a question about the codebase using codemap.json."""
    memory = get_memory_instance()
    answer = memory.query_codemap(question)
    click.echo("\n--- CODEMAP ANSWER ---\n")
    click.echo(answer)


@cli.command("memory:show-user-profile")
def show_user_profile():
    """Display the current user's profile from long-term memory."""
    memory = get_memory_instance()
    profile = memory.get_user_profile_summary()
    click.echo("\n--- USER PROFILE ---\n")
    click.echo(profile)


@cli.command("memory:show-assistant-knowledge")
def show_assistant_knowledge():
    """Display current assistant knowledge from long-term memory."""
    memory = get_memory_instance()
    knowledge = memory.get_assistant_knowledge_summary()
    click.echo("\n--- ASSISTANT KNOWLEDGE ---\n")
    for entry in knowledge:
        click.echo(f"- {entry['knowledge']} (Recorded: {entry['timestamp']})")


@cli.command("memory:show-projects")
def show_projects():
    """Display all known projects from long-term memory."""
    memory = get_memory_instance()
    projects = memory.get_all_projects_summary()
    click.echo("\n--- PROJECTS ---\n")
    for project in projects:
        click.echo(f"- {project.get('project_id')} | {project.get('project_name')}")


@cli.command("memory:show-threads")
@click.argument("project_id", type=str)
def show_threads_by_project(project_id):
    """Display threads associated with a specific project."""
    memory = get_memory_instance()
    threads = memory.get_threads_by_project(project_id)
    click.echo(f"\n--- THREADS in PROJECT {project_id} ---\n")
    for thread in threads:
        click.echo(f"- {thread.get('thread_id')} | {thread.get('thread_title')}")


@cli.command("memory:show-conversations")
@click.argument("thread_id", type=str)
def show_conversations_by_thread(thread_id):
    """Display conversations associated with a specific thread."""
    memory = get_memory_instance()
    conversations = memory.get_conversations_by_thread(thread_id)
    click.echo(f"\n--- CONVERSATIONS in THREAD {thread_id} ---\n")
    for convo in conversations:
        click.echo(
            f"- {convo.get('conversation_id')} | {convo.get('title', 'Untitled')}"
        )


@cli.command("memory:get-conversation")
@click.argument("conversation_id", type=str)
def get_conversation_by_id(conversation_id):
    """Retrieve a specific conversation by its ID."""
    memory = get_memory_instance()
    convo = memory.get_conversation_by_id(conversation_id)
    click.echo(f"\n--- CONVERSATION {conversation_id} ---\n")
    click.echo(json.dumps(convo, indent=2))


@cli.command("memory:summarize-and-branch")
@click.argument("conversation_id", type=str)
def summarize_and_branch(conversation_id):
    """Summarize a conversation and create a child branch."""
    memory = get_memory_instance()
    result = memory.summarize_and_branch_conversation(conversation_id)
    click.echo("\n--- SUMMARY RESULT ---\n")
    click.echo(result if result else "No summary was generated.")
