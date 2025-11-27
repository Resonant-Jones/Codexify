#!/usr/bin/env python3
"""
Simple validation script to test our patch fixes without full dependency resolution.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "guardian"))


def test_memory_analyzer_query_method():
    """Test that MemoryAnalyzer uses query_memory instead of query_memories"""
    print("Testing Memory Analyzer query method...")

    # Read the file and check for the correct method call
    with open("guardian/plugins/memory_analyzer/main.py") as f:
        content = f.read()

    # Should have query_memory, not query_memories
    if "query_memory(" in content and "query_memories(" not in content:
        print("✅ Memory Analyzer: query_memory method used correctly")
        return True
    else:
        print(
            "❌ Memory Analyzer: Still using query_memories or missing query_memory"
        )
        return False


def test_pattern_analyzer_health_check():
    """Test that PatternAnalyzer has health_check method"""
    print("Testing Pattern Analyzer health_check method...")

    with open("guardian/plugins/pattern_analyzer/main.py") as f:
        content = f.read()

    # Should have health_check method
    if "def health_check(self)" in content:
        print("✅ Pattern Analyzer: health_check method added")
        return True
    else:
        print("❌ Pattern Analyzer: health_check method missing")
        return False


def test_system_diagnostics_thread_info():
    """Test that SystemDiagnostics uses correct thread metadata"""
    print("Testing System Diagnostics thread metadata...")

    with open("guardian/plugins/system_diagnostics/main.py") as f:
        content = f.read()

    # Should have "threads": monitored_threads_info, not "thread_info": thread_info
    if (
        '"threads": monitored_threads_info' in content
        and '"thread_info": thread_info' not in content
    ):
        print("✅ System Diagnostics: thread metadata fixed")
        return True
    else:
        print("❌ System Diagnostics: thread metadata still incorrect")
        return False


def test_system_diagnostics_test_fixes():
    """Test that SystemDiagnostics tests have correct assertions"""
    print("Testing System Diagnostics test fixes...")

    with open(
        "guardian/plugins/system_diagnostics/tests/test_system_diagnostics.py",
    ) as f:
        content = f.read()

    # Should check for 'threads' in metadata and use max_retries + 2
    threads_check = "'threads' in result.metadata" in content
    retry_check = "max_retries'] + 2" in content

    if threads_check and retry_check:
        print("✅ System Diagnostics Tests: metadata and retry loop fixed")
        return True
    else:
        print(
            f"❌ System Diagnostics Tests: threads_check={threads_check}, retry_check={retry_check}"
        )
        return False


def test_memory_analyzer_test_mocks():
    """Test that Memory Analyzer tests use correct mock method"""
    print("Testing Memory Analyzer test mocks...")

    with open(
        "guardian/plugins/memory_analyzer/tests/test_memory_analyzer.py") as f:
        content = f.read()

    # Should have query_memory mocks, not query_memories
    if (
        "query_memory.return_value" in content
        and "query_memories.return_value" not in content
    ):
        print("✅ Memory Analyzer Tests: mock methods fixed")
        return True
    else:
        print("❌ Memory Analyzer Tests: still using query_memories mocks")
        return False


def test_init_files():
    """Test that __init__.py files exist in test directories"""
    print("Testing __init__.py files...")

    test_dirs = [
        "guardian/plugins/memory_analyzer/tests/__init__.py",
        "guardian/plugins/pattern_analyzer/tests/__init__.py",
        "guardian/plugins/system_diagnostics/tests/__init__.py",
    ]

    all_exist = True
    for init_file in test_dirs:
        if os.path.exists(init_file):
            print(f"✅ {init_file} exists")
        else:
            print(f"❌ {init_file} missing")
            all_exist = False

    return all_exist


def main():
    """Run all validation tests"""
    print("🔍 Validating Guardian Plugin Patch Fixes")
    print("=" * 50)

    tests = [
        test_memory_analyzer_query_method,
        test_pattern_analyzer_health_check,
        test_system_diagnostics_thread_info,
        test_system_diagnostics_test_fixes,
        test_memory_analyzer_test_mocks,
        test_init_files,
    ]

    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
            print()
        except Exception as e:
            print(f"❌ Test failed with error: {e}")
            results.append(False)
            print()

    print("=" * 50)
    passed = sum(results)
    total = len(results)

    if passed == total:
        print(f"🎉 ALL TESTS PASSED ({passed}/{total})")
        print("\n✅ Patch sweep completed successfully!")
        print("\nSummary of fixes applied:")
        print("1. ✅ Memory Analyzer: Fixed query_memories → query_memory")
        print("2. ✅ Pattern Analyzer: Added health_check() method")
        print(
            "3. ✅ System Diagnostics: Fixed thread_info → monitored_threads_info"
        )
        print(
            "4. ✅ System Diagnostics Tests: Fixed metadata assertions and retry loop"
        )
        print("5. ✅ Memory Analyzer Tests: Fixed mock method calls")
        print("6. ✅ Added __init__.py files to test directories")
        return 0
    else:
        print(f"❌ SOME TESTS FAILED ({passed}/{total})")
        return 1


if __name__ == "__main__":
    sys.exit(main())
