#!/usr/bin/env python3
"""
Simple validation script to test our patch fixes without full dependency resolution.
"""

import logging
import os
import sys

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "guardian"))


def test_memory_analyzer_query_method():
    """Test that MemoryAnalyzer uses query_memory instead of query_memories"""
    logger.info("Testing Memory Analyzer query method...")

    # Read the file and check for the correct method call
    with open("guardian/plugins/memory_analyzer/main.py") as f:
        content = f.read()

    # Should have query_memory, not query_memories
    if "query_memory(" in content and "query_memories(" not in content:
        logger.info("Memory Analyzer: query_memory method used correctly")
        return True
    else:
        logger.error(
            "Memory Analyzer: Still using query_memories or missing query_memory"
        )
        return False


def test_pattern_analyzer_health_check():
    """Test that PatternAnalyzer has health_check method"""
    logger.info("Testing Pattern Analyzer health_check method...")

    with open("guardian/plugins/pattern_analyzer/main.py") as f:
        content = f.read()

    # Should have health_check method
    if "def health_check(self)" in content:
        logger.info("Pattern Analyzer: health_check method added")
        return True
    else:
        logger.error("Pattern Analyzer: health_check method missing")
        return False


def test_system_diagnostics_thread_info():
    """Test that SystemDiagnostics uses correct thread metadata"""
    logger.info("Testing System Diagnostics thread metadata...")

    with open("guardian/plugins/system_diagnostics/main.py") as f:
        content = f.read()

    # Should have "threads": monitored_threads_info, not "thread_info": thread_info
    if (
        '"threads": monitored_threads_info' in content
        and '"thread_info": thread_info' not in content
    ):
        logger.info("System Diagnostics: thread metadata fixed")
        return True
    else:
        logger.error("System Diagnostics: thread metadata still incorrect")
        return False


def test_system_diagnostics_test_fixes():
    """Test that SystemDiagnostics tests have correct assertions"""
    logger.info("Testing System Diagnostics test fixes...")

    with open(
        "guardian/plugins/system_diagnostics/tests/test_system_diagnostics.py",
    ) as f:
        content = f.read()

    # Should check for 'threads' in metadata and use max_retries + 2
    threads_check = "'threads' in result.metadata" in content
    retry_check = "max_retries'] + 2" in content

    if threads_check and retry_check:
        logger.info("System Diagnostics Tests: metadata and retry loop fixed")
        return True
    else:
        logger.error(
            f"System Diagnostics Tests: threads_check={threads_check}, retry_check={retry_check}"
        )
        return False


def test_memory_analyzer_test_mocks():
    """Test that Memory Analyzer tests use correct mock method"""
    logger.info("Testing Memory Analyzer test mocks...")

    with open(
        "guardian/plugins/memory_analyzer/tests/test_memory_analyzer.py"
    ) as f:
        content = f.read()

    # Should have query_memory mocks, not query_memories
    if (
        "query_memory.return_value" in content
        and "query_memories.return_value" not in content
    ):
        logger.info("Memory Analyzer Tests: mock methods fixed")
        return True
    else:
        logger.error("Memory Analyzer Tests: still using query_memories mocks")
        return False


def test_init_files():
    """Test that __init__.py files exist in test directories"""
    logger.info("Testing __init__.py files...")

    test_dirs = [
        "guardian/plugins/memory_analyzer/tests/__init__.py",
        "guardian/plugins/pattern_analyzer/tests/__init__.py",
        "guardian/plugins/system_diagnostics/tests/__init__.py",
    ]

    all_exist = True
    for init_file in test_dirs:
        if os.path.exists(init_file):
            logger.info(f"{init_file} exists")
        else:
            logger.error(f"{init_file} missing")
            all_exist = False

    return all_exist


def main():
    """Run all validation tests"""
    logger.info("Validating Guardian Plugin Patch Fixes")
    logger.info("=" * 50)

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
            logger.debug("")
        except Exception as e:
            logger.error(f"Test failed with error: {e}")
            results.append(False)
            logger.debug("")

    logger.info("=" * 50)
    passed = sum(results)
    total = len(results)

    if passed == total:
        logger.info(f"ALL TESTS PASSED ({passed}/{total})")
        logger.info("Patch sweep completed successfully!")
        logger.info("Summary of fixes applied:")
        logger.info("1. Memory Analyzer: Fixed query_memories -> query_memory")
        logger.info("2. Pattern Analyzer: Added health_check() method")
        logger.info(
            "3. System Diagnostics: Fixed thread_info -> monitored_threads_info"
        )
        logger.info(
            "4. System Diagnostics Tests: Fixed metadata assertions and retry loop"
        )
        logger.info("5. Memory Analyzer Tests: Fixed mock method calls")
        logger.info("6. Added __init__.py files to test directories")
        return 0
    else:
        logger.error(f"SOME TESTS FAILED ({passed}/{total})")
        return 1


if __name__ == "__main__":
    sys.exit(main())
