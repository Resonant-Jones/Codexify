"""
MemoryOS MCP 服务器综合测试客户端
使用官方MCP Python SDK进行测试
"""

import asyncio
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, Optional

# 尝试导入官方MCP客户端
try:
    from mcp import ClientSession, StdioServerParameters, types
    from mcp.client.stdio import stdio_client
except ImportError as e:
    print(f"❌ 无法导入MCP客户端库: {e}")
    print("请安装官方MCP SDK: pip install mcp")
    sys.exit(1)


class MemoryOSMCPTester:
    """MemoryOS MCP服务器测试类"""

    def __init__(
        self, server_script: str = "server_new.py", config_file: str = "config.json"
    ):
        self.server_script = Path(server_script)
        self.config_file = Path(config_file)

        # 验证文件存在
        if not self.server_script.exists():
            raise FileNotFoundError(f"服务器脚本不存在: {self.server_script}")
        if not self.config_file.exists():
            raise FileNotFoundError(f"配置文件不存在: {self.config_file}")

    async def test_server_initialization(self):
        """测试服务器初始化"""
        print("\n🔄 测试1: 服务器初始化")

        server_params = StdioServerParameters(
            command=sys.executable,
            args=[str(self.server_script), "--config", str(self.config_file)],
            env=None,
        )

        try:
            async with stdio_client(server_params) as (read_stream, write_stream):
                async with ClientSession(read_stream, write_stream) as session:
                    # 初始化连接
                    await session.initialize()
                    print("✅ 服务器初始化成功")
                    return True
        except Exception as e:
            print(f"❌ 服务器初始化失败: {e}")
            return False

    async def test_tools_discovery(self):
        """测试工具发现"""
        print("\n🔧 测试2: 工具发现")

        server_params = StdioServerParameters(
            command=sys.executable,
            args=[str(self.server_script), "--config", str(self.config_file)],
            env=None,
        )

        try:
            async with stdio_client(server_params) as (read_stream, write_stream):
                async with ClientSession(read_stream, write_stream) as session:
                    await session.initialize()

                    # 获取工具列表
                    tools_result = await session.list_tools()
                    tools = tools_result.tools if hasattr(tools_result, "tools") else []

                    print(f"✅ 发现 {len(tools)} 个工具:")
                    expected_tools = [
                        "add_memory",
                        "retrieve_memory",
                        "get_user_profile",
                    ]

                    for tool in tools:
                        print(f"  - {tool.name}: {tool.description}")
                        if tool.name in expected_tools:
                            expected_tools.remove(tool.name)

                    if expected_tools:
                        print(f"⚠️ 缺少预期工具: {expected_tools}")
                    else:
                        print("✅ 所有预期工具都已找到")

                    return tools
        except Exception as e:
            print(f"❌ 工具发现失败: {e}")
            return []

    async def test_add_memory_tool(self):
        """测试添加记忆工具 - 20轮测试"""
        print("\n💾 测试3: 添加记忆工具 (20轮测试)")

        server_params = StdioServerParameters(
            command=sys.executable,
            args=[str(self.server_script), "--config", str(self.config_file)],
            env=None,
        )

        # 准备20轮测试数据
        test_conversations = [
            ("Hello, I'm a new user", "Welcome to MemoryOS! I'm your AI assistant."),
            (
                "I like programming",
                "Great! Programming is a very interesting skill. What programming language do you mainly use?",
            ),
            ("I often use Python", "Python is a great language! Simple yet powerful."),
            (
                "I'm learning machine learning",
                "Machine learning has great prospects! Which field are you focusing on?",
            ),
            (
                "I'm interested in natural language processing",
                "NLP is a fascinating field! It has many practical applications.",
            ),
            (
                "I want to understand how ChatGPT works",
                "ChatGPT is based on the Transformer architecture and uses massive pre-training data.",
            ),
            (
                "What is the attention mechanism?",
                "The attention mechanism allows models to focus on the most relevant parts of the input sequence.",
            ),
            (
                "I want to learn deep learning",
                "For deep learning beginners, I suggest starting with neural network fundamentals.",
            ),
            (
                "Recommend some learning resources",
                "I recommend classic resources like 'Deep Learning' book and CS231n course.",
            ),
            (
                "I have a project idea",
                "Awesome! Share your project idea and I'll help you analyze it.",
            ),
            (
                "I want to build an intelligent dialogue system",
                "Intelligent dialogue systems need to consider intent recognition, context understanding and other technologies.",
            ),
            (
                "How to handle multi-turn conversations?",
                "Multi-turn conversations require maintaining dialogue state and context memory.",
            ),
            (
                "How does MemoryOS work?",
                "MemoryOS maintains long-term dialogue context through hierarchical memory management.",
            ),
            (
                "What's the difference between short-term and long-term memory",
                "Short-term memory stores current conversations, while long-term memory saves important user information.",
            ),
            (
                "How to optimize memory retrieval?",
                "You can use vector similarity search and semantic understanding to improve retrieval accuracy.",
            ),
            (
                "I want to contribute code",
                "Welcome to contribute! You can start by reading documentation and solving issues.",
            ),
            (
                "What open source projects do you recommend?",
                "I recommend following popular AI open source projects like Hugging Face and LangChain.",
            ),
            (
                "My interest is computer vision",
                "Computer vision covers areas like image recognition and object detection.",
            ),
            (
                "Advice on choosing deep learning frameworks",
                "Both PyTorch and TensorFlow are great. PyTorch is better for research, TensorFlow for production.",
            ),
            (
                "Thank you for your help!",
                "You're welcome! I'm glad I could help you, looking forward to our next conversation.",
            ),
        ]

        try:
            async with stdio_client(server_params) as (read_stream, write_stream):
                async with ClientSession(read_stream, write_stream) as session:
                    await session.initialize()

                    success_count = 0

                    # 执行20轮添加记忆测试
                    for i, (user_input, agent_response) in enumerate(
                        test_conversations, 1
                    ):
                        print(f"   第{i:2d}轮: 添加记忆...")

                        test_data = {
                            "user_input": user_input,
                            "agent_response": agent_response,
                            # 不包含 meta_data
                        }

                        result = await session.call_tool("add_memory", test_data)

                        if hasattr(result, "content") and result.content:
                            content = result.content[0]
                            if hasattr(content, "text"):
                                response = json.loads(content.text)
                                if response.get("status") == "success":
                                    success_count += 1
                                    print(f"   第{i:2d}轮: ✅ 成功")
                                else:
                                    print(
                                        f"   第{i:2d}轮: ❌ 失败 - {response.get('message', '未知错误')}"
                                    )
                            else:
                                print(f"   第{i:2d}轮: ❌ 失败 - 无效响应格式")
                        else:
                            print(f"   第{i:2d}轮: ❌ 失败 - 无响应内容")

                        # 短暂延迟，避免过快请求
                        await asyncio.sleep(0.1)

                    print(
                        f"\n✅ 记忆添加测试完成: {success_count}/{len(test_conversations)} 成功"
                    )
                    return success_count == len(test_conversations)

        except Exception as e:
            print(f"❌ 记忆添加测试失败: {e}")
            return False

    async def test_retrieve_memory_tool(self):
        """测试检索记忆工具"""
        print("\n🔍 测试4: 检索记忆工具")

        server_params = StdioServerParameters(
            command=sys.executable,
            args=[str(self.server_script), "--config", str(self.config_file)],
            env=None,
        )

        # 准备多个检索查询
        test_queries = [
            (
                "user's programming skills",
                "Find user's programming related information",
            ),
            (
                "machine learning related content",
                "Retrieve machine learning and AI related conversations",
            ),
            (
                "learning resource recommendations",
                "Find recommended learning resources",
            ),
            ("project related discussions", "Retrieve conversations about projects"),
            (
                "user's interests and hobbies",
                "Understand user's interests and preferences",
            ),
        ]

        try:
            async with stdio_client(server_params) as (read_stream, write_stream):
                async with ClientSession(read_stream, write_stream) as session:
                    await session.initialize()

                    success_count = 0

                    # 执行多个检索查询测试
                    for i, (query, description) in enumerate(test_queries, 1):
                        print(f"   第{i}个查询: {description}")

                        test_query = {
                            "query": query,
                            "relationship_with_user": "friend",
                            "style_hint": "helpful and informative",
                            "max_results": 10,
                        }

                        result = await session.call_tool("retrieve_memory", test_query)

                        if hasattr(result, "content") and result.content:
                            content = result.content[0]
                            if hasattr(content, "text"):
                                response = json.loads(content.text)
                                if response.get("status") == "success":
                                    success_count += 1
                                    print(f"   第{i}个查询: ✅ 成功")
                                    print(
                                        f"     - 检索到页面数: {response.get('total_pages_found', 0)}"
                                    )
                                    print(
                                        f"     - 用户知识数: {response.get('total_user_knowledge_found', 0)}"
                                    )
                                    print(
                                        f"     - 助手知识数: {response.get('total_assistant_knowledge_found', 0)}"
                                    )
                                else:
                                    print(
                                        f"   第{i}个查询: ❌ 失败 - {response.get('message', '未知错误')}"
                                    )
                            else:
                                print(f"   第{i}个查询: ❌ 失败 - 无效响应格式")
                        else:
                            print(f"   第{i}个查询: ❌ 失败 - 无响应内容")

                        # 短暂延迟
                        await asyncio.sleep(0.1)

                    print(
                        f"\n✅ 记忆检索测试完成: {success_count}/{len(test_queries)} 成功"
                    )
                    return success_count >= len(test_queries) // 2  # 至少一半成功即可

        except Exception as e:
            print(f"❌ 记忆检索测试失败: {e}")
            return False

    async def test_get_user_profile_tool(self):
        """测试获取用户画像工具"""
        print("\n👤 测试5: 获取用户画像工具")

        server_params = StdioServerParameters(
            command=sys.executable,
            args=[str(self.server_script), "--config", str(self.config_file)],
            env=None,
        )

        # 准备不同的参数组合测试
        test_configs = [
            (
                {"include_knowledge": True, "include_assistant_knowledge": False},
                "包含用户知识",
            ),
            (
                {"include_knowledge": False, "include_assistant_knowledge": True},
                "包含助手知识",
            ),
            (
                {"include_knowledge": True, "include_assistant_knowledge": True},
                "包含所有知识",
            ),
            (
                {"include_knowledge": False, "include_assistant_knowledge": False},
                "仅基本画像",
            ),
        ]

        try:
            async with stdio_client(server_params) as (read_stream, write_stream):
                async with ClientSession(read_stream, write_stream) as session:
                    await session.initialize()

                    success_count = 0

                    # 执行不同配置的用户画像测试
                    for i, (test_params, description) in enumerate(test_configs, 1):
                        print(f"   第{i}种配置: {description}")

                        result = await session.call_tool(
                            "get_user_profile", test_params
                        )

                        if hasattr(result, "content") and result.content:
                            content = result.content[0]
                            if hasattr(content, "text"):
                                response = json.loads(content.text)
                                if response.get("status") == "success":
                                    success_count += 1
                                    print(f"   第{i}种配置: ✅ 成功")
                                    print(
                                        f"     - 用户ID: {response.get('user_id', 'N/A')}"
                                    )
                                    print(
                                        f"     - 助手ID: {response.get('assistant_id', 'N/A')}"
                                    )

                                    # 显示用户画像信息
                                    user_profile = response.get("user_profile", "暂无")
                                    if len(user_profile) > 100:
                                        user_profile = user_profile[:100] + "..."
                                    print(f"     - 用户画像: {user_profile}")

                                    # 显示知识条目数量
                                    if "user_knowledge_count" in response:
                                        print(
                                            f"     - 用户知识条目数: {response.get('user_knowledge_count', 0)}"
                                        )
                                    if "assistant_knowledge_count" in response:
                                        print(
                                            f"     - 助手知识条目数: {response.get('assistant_knowledge_count', 0)}"
                                        )
                                else:
                                    print(
                                        f"   第{i}种配置: ❌ 失败 - {response.get('message', '未知错误')}"
                                    )
                            else:
                                print(f"   第{i}种配置: ❌ 失败 - 无效响应格式")
                        else:
                            print(f"   第{i}种配置: ❌ 失败 - 无响应内容")

                        # 短暂延迟
                        await asyncio.sleep(0.1)

                    print(
                        f"\n✅ 用户画像测试完成: {success_count}/{len(test_configs)} 成功"
                    )
                    return success_count >= 3  # 至少3种配置成功

        except Exception as e:
            print(f"❌ 用户画像测试失败: {e}")
            return False

    async def run_all_tests(self):
        """运行所有测试"""
        print("🚀 开始MemoryOS MCP服务器综合测试")
        print(f"服务器脚本: {self.server_script}")
        print(f"配置文件: {self.config_file}")
        print("=" * 60)

        test_results = []

        # 运行所有测试
        tests = [
            ("服务器初始化", self.test_server_initialization),
            ("工具发现", self.test_tools_discovery),
            ("添加记忆 (20轮)", self.test_add_memory_tool),
            ("检索记忆", self.test_retrieve_memory_tool),
            ("获取用户画像", self.test_get_user_profile_tool),
        ]

        for test_name, test_func in tests:
            try:
                result = await test_func()
                test_results.append(
                    {"name": test_name, "result": result, "error": None}
                )
            except Exception as e:
                test_results.append(
                    {"name": test_name, "result": False, "error": str(e)}
                )

        # 输出测试结果汇总
        print("\n" + "=" * 60)
        print("📊 测试结果汇总:")

        passed_count = 0
        total_count = len(test_results)

        for test in test_results:
            status = "✅ 通过" if test["result"] else "❌ 失败"
            print(f"  {status} - {test['name']}")
            if test["error"]:
                print(f"    错误: {test['error']}")
            if test["result"]:
                passed_count += 1

        print(f"\n总计: {passed_count}/{total_count} 测试通过")

        if passed_count == total_count:
            print("🎉 所有测试通过！MemoryOS MCP服务器工作正常")
        else:
            print("⚠️ 部分测试失败，请检查服务器配置和实现")

        return passed_count == total_count


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="MemoryOS MCP服务器综合测试")
    parser.add_argument("--server", default="server_new.py", help="服务器脚本路径")
    parser.add_argument("--config", default="config.json", help="配置文件路径")

    args = parser.parse_args()

    try:
        tester = MemoryOSMCPTester(args.server, args.config)
        success = asyncio.run(tester.run_all_tests())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n⚠️ 测试被用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 测试过程中发生严重错误: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
