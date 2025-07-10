"""
Guardian CLI Commands
------------------
Command-line interface for Guardian functionality.
"""

import argparse
import logging
import os
import time
from typing import List, Optional

from ..memory.memoryos import MemoryOS
from ..tts.tts_manager import TTSManager
from ..tts.tts_service import TTSError

# Configure logging
logger = logging.getLogger(__name__)


def cli_codemap_query(args: argparse.Namespace) -> None:
    """
    CLI command handler for codemap:query

    Args:
        args: Parsed command line arguments containing:
            - term: Search term to query
            - explain: Boolean flag for explanation mode
    """
    memos = MemoryOS()
    results = memos.query_codemap(args.term)

    # If explain flag is set, try to use LLM explanation
    if getattr(args, "explain", False):
        try:
            from guardian.llm import llm_explain

            explained_results = llm_explain(results)
            print(memos.format_codemap_results(explained_results, explain=True))
        except ImportError:
            logger.warning("LLM explanation not available - showing standard results")
            print(memos.format_codemap_results(results))
    else:
        print(memos.format_codemap_results(results))


def cli_conversation_simulate_overflow(args: argparse.Namespace) -> None:
    """
    CLI command handler for conversation:simulate-overflow

    Simulates hitting the token limit for a conversation and demonstrates
    the auto-branching behavior.

    Args:
        args: Parsed command line arguments containing:
            - conversation_id: ID of conversation to simulate with
            - message_count: Number of messages to simulate (default: 100)
    """
    memos = MemoryOS()

    # Create new conversation if ID not provided
    if not args.conversation_id:
        conversation = memos.create_conversation()
        conversation_id = conversation.id
        print(f"Created new conversation: {conversation_id}")
    else:
        conversation_id = args.conversation_id

    # Simulate adding messages until we trigger summarization
    print(f"\nSimulating conversation overflow for {conversation_id}")
    print("-" * 50)

    # Add dummy messages (1000 tokens each) until we hit the limit
    message_count = args.message_count if args.message_count else 100

    for i in range(message_count):
        # Monitor length before adding message
        status = memos.monitor_conversation_length(conversation_id)

        if status["status"] == "summarized":
            print("\nSummarization triggered!")
            print(f"Parent conversation: {conversation_id}")
            print(f"New child conversation: {status['new_conversation_id']}")
            print(f"Message: {status['message']}")
            break
        elif status["status"] == "error":
            print(f"\nError: {status['message']}")
            break
        else:
            # Add a dummy message (simulating 1000 tokens)
            conversation = memos.conversation_manager.load_conversation(conversation_id)
            if conversation:
                conversation.add_message(
                    {"role": "user", "content": f"Message {i+1}"}, token_count=1000
                )
                memos.conversation_manager.save_conversation(conversation)
                if (i + 1) % 10 == 0:  # Print status every 10 messages
                    print(status["message"])


def cli_tts_speak(args: argparse.Namespace) -> None:
    """
    CLI command handler for tts:speak

    Synthesizes text to speech using specified provider and voice.

    Args:
        args: Parsed command line arguments containing:
            - text: Text to synthesize
            - provider: TTS provider to use
            - voice: Voice to use
            - output: Output file path
            - list_voices: Flag to list available voices
    """
    try:
        tts_manager = TTSManager()

        # Handle --list-voices flag
        if args.list_voices:
            provider = args.provider or tts_manager.default_provider
            print(f"\nAvailable voices for provider '{provider}':")
            voices = tts_manager.list_voices(provider)
            for voice in voices:
                print(f"  - {voice}")
            return

        # Handle --list-providers flag
        if args.list_providers:
            print("\nAvailable TTS providers:")
            providers = tts_manager.list_providers()
            for provider in providers:
                if provider == tts_manager.default_provider:
                    print(f"  - {provider} (default)")
                else:
                    print(f"  - {provider}")
            return

        # Validate required arguments for synthesis
        if not args.text:
            print("Error: --text is required for speech synthesis")
            return

        if not args.voice:
            print("Error: --voice is required for speech synthesis")
            return

        # Generate output path if not provided
        output_path = args.output
        if not output_path:
            os.makedirs("tts_output", exist_ok=True)
            output_path = f"tts_output/speech_{int(time.time())}.wav"

        # Synthesize speech
        print(f"\nSynthesizing speech using provider '{args.provider or 'default'}'...")
        audio_data = tts_manager.synthesize(
            text=args.text, voice=args.voice, provider_name=args.provider
        )

        # Save audio file
        tts_manager.save_audio(audio_data, output_path)
        print(f"Audio saved to: {output_path}")

    except TTSError as e:
        print(f"TTS Error: {str(e)}")
    except Exception as e:
        print(f"Error: {str(e)}")


def setup_cli_parser() -> argparse.ArgumentParser:
    """
    Set up the command-line argument parser.

    Returns:
        argparse.ArgumentParser: Configured parser
    """
    parser = argparse.ArgumentParser(description="Guardian CLI: Digital Archive Nexus")
    subparsers = parser.add_subparsers(dest="command")

    # Add codemap:query command
    codemap_parser = subparsers.add_parser(
        "codemap:query", help="Query the codemap with a search term"
    )
    codemap_parser.add_argument(
        "term", type=str, help='Search term to query the codemap (e.g., "MyFunction")'
    )
    codemap_parser.add_argument(
        "--explain",
        action="store_true",
        help="Run the result through LLM explain function (if available)",
    )
    codemap_parser.set_defaults(func=cli_codemap_query)

    # Add conversation:simulate-overflow command
    conv_parser = subparsers.add_parser(
        "conversation:simulate-overflow",
        help="Simulate conversation token limit overflow",
    )
    conv_parser.add_argument(
        "--conversation-id",
        type=str,
        help="ID of existing conversation (creates new if not provided)",
    )
    conv_parser.add_argument(
        "--message-count",
        type=int,
        default=100,
        help="Number of messages to simulate (default: 100)",
    )
    conv_parser.set_defaults(func=cli_conversation_simulate_overflow)

    # Add tts:speak command
    tts_parser = subparsers.add_parser("tts:speak", help="Synthesize text to speech")
    tts_parser.add_argument("--text", type=str, help="Text to synthesize")
    tts_parser.add_argument(
        "--provider",
        type=str,
        help="TTS provider to use (default: configured default provider)",
    )
    tts_parser.add_argument("--voice", type=str, help="Voice ID/name to use")
    tts_parser.add_argument(
        "--output",
        type=str,
        help="Output audio file path (default: tts_output/speech_<timestamp>.wav)",
    )
    tts_parser.add_argument(
        "--list-voices",
        action="store_true",
        help="List available voices for the specified provider",
    )
    tts_parser.add_argument(
        "--list-providers", action="store_true", help="List available TTS providers"
    )
    tts_parser.set_defaults(func=cli_tts_speak)

    return parser


def main() -> None:
    """Main CLI entrypoint."""
    parser = setup_cli_parser()
    args = parser.parse_args()

    if hasattr(args, "func"):
        try:
            args.func(args)
        except Exception as e:
            logger.error(f"Command failed: {e}")
            print(f"Error: {e}")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
