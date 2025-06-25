# example_2.py - Simple MemoryOS Basic Demo

import os

from memoryos import Memoryos

# --- 基础配置 ---
USER_ID = "demo_user"
ASSISTANT_ID = "demo_assistant"
OPENAI_API_KEY = ""
OPENAI_BASE_URL = ""
DATA_STORAGE_PATH = "./simple_demo_data"
LLM_MODEL = "gpt-4o-mini"


def simple_demo():
    print("🚀 MemoryOS Simple Demo")

    # 1. 初始化 MemoryOS
    print("📦 Initializing MemoryOS...")
    try:
        memo = Memoryos(
            user_id=USER_ID,
            openai_api_key=OPENAI_API_KEY,
            openai_base_url=OPENAI_BASE_URL,
            data_storage_path=DATA_STORAGE_PATH,
            llm_model=LLM_MODEL,
            assistant_id=ASSISTANT_ID,
            short_term_capacity=7,
            mid_term_heat_threshold=5,
        )
        print("✅ MemoryOS initialized successfully!\n")
    except Exception as e:
        print(f"❌ Error: {e}")
        return

    # 2. 添加一些基础记忆
    print("💾 Adding some memories...")

    memo.add_memory(
        user_input="Hi! I'm Tom, I work as a data scientist in San Francisco.",
        agent_response="Hello Tom! Nice to meet you. Data science is such an exciting field. What kind of data do you work with?",
    )

    memo.add_memory(
        user_input="I mainly work with e-commerce data. I also love playing guitar in my free time.",
        agent_response="That's a great combination! E-commerce analytics must provide fascinating insights into consumer behavior. How long have you been playing guitar?",
    )

    memo.add_memory(
        user_input="I've been playing for about 5 years. I really enjoy blues and rock music.",
        agent_response="Five years is a solid foundation! Blues and rock are fantastic genres for guitar. Do you have a favorite artist or song you like to play?",
    )

    test_query = "What do you remember about my job and hobbies?"
    print(f" User: {test_query}")

    response = memo.get_response(
        query=test_query,
    )

    print(f"Assistant: {response}")


if __name__ == "__main__":
    simple_demo()
