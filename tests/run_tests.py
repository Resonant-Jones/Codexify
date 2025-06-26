"""
Test Runner
----------
Executes all system tests and generates a comprehensive report.
"""

import asyncio
import json
import logging
import sys
import time
import unittest
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class TestResult:
    """Represents a test execution result."""
    
    def __init__(
        self,
        name: str,
        status: str,
        duration: float,
        error: Optional[str] = None
    ):
        self.name = name
        self.status = status
        self.duration = duration
        self.error = error
        self.timestamp = datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary representation."""
        return {
            'name': self.name,
            'status': self.status,
            'duration': self.duration,
            'error': self.error,
            'timestamp': self.timestamp.isoformat()
        }

class TestReport:
    """Generates and manages test execution reports."""
    
    def __init__(self):
        self.results: List[TestResult] = []
        self.start_time: Optional[datetime] = None
        self.end_time: Optional[datetime] = None
        self.total_duration: float = 0.0
        self.summary: Dict[str, int] = {
            'total': 0,
            'passed': 0,
            'failed': 0,
            'error': 0
        }
    
    def add_result(self, result: TestResult) -> None:
        """Add a test result to the report."""
        self.results.append(result)
        self.summary['total'] += 1
        
        if result.status == 'passed':
            self.summary['passed'] += 1
        elif result.status == 'failed':
            self.summary['failed'] += 1
        else:
            self.summary['error'] += 1
    
    def generate_report(self) -> Dict[str, Any]:
        """Generate complete test report."""
        return {
            'summary': self.summary,
            'execution_time': {
                'start': self.start_time.isoformat() if self.start_time else None,
                'end': self.end_time.isoformat() if self.end_time else None,
                'duration': self.total_duration
            },
            'results': [r.to_dict() for r in self.results]
        }
    
    def save_report(self, path: Path) -> None:
        """Save report to file."""
        report = self.generate_report()
        
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, 'w') as f:
                json.dump(report, f, indent=2)
            logger.info(f"Test report saved to {path}")
        except Exception as e:
            logger.error(f"Failed to save test report: {e}")
    
    def print_summary(self) -> None:
        """Print test execution summary."""
        print("\n=== Test Execution Summary ===")
        print(f"Total Tests: {self.summary['total']}")
        print(f"Passed: {self.summary['passed']}")
        print(f"Failed: {self.summary['failed']}")
        print(f"Errors: {self.summary['error']}")
        print(f"Total Duration: {self.total_duration:.2f}s")
        
        if self.summary['failed'] > 0 or self.summary['error'] > 0:
            print("\nFailures and Errors:")
            for result in self.results:
                if result.status in ('failed', 'error'):
                    print(f"\n{result.name}:")
                    print(f"Status: {result.status}")
                    if result.error:
                        print(f"Error: {result.error}")

class TestRunner:
    """Executes test suites and manages results."""
    
    def __init__(self):
        self.report = TestReport()
        self.test_modules = [
            'test_system_integration',
            'test_agents_and_plugins'
        ]
    
    async def run_tests(self) -> TestReport:
        """Run all test suites."""
        self.report.start_time = datetime.utcnow()
        
        try:
            # Import test modules
            for module_name in self.test_modules:
                try:
                    module = __import__(module_name)
                    await self._run_test_module(module)
                except Exception as e:
                    logger.error(f"Failed to run {module_name}: {e}")
                    self.report.add_result(
                        TestResult(
                            name=module_name,
                            status='error',
                            duration=0.0,
                            error=str(e)
                        )
                    )
        finally:
            self.report.end_time = datetime.utcnow()
            self.report.total_duration = (
                self.report.end_time - self.report.start_time
            ).total_seconds()
        
        return self.report
    
    async def _run_test_module(self, module: Any) -> None:
        """Run tests from a specific module."""
        # Get test cases
        test_cases = self._get_test_cases(module)
        
        for test_case in test_cases:
            await self._run_test_case(test_case)
    
    def _get_test_cases(self, module: Any) -> List[unittest.TestCase]:
        """Get all test cases from a module."""
        test_cases = []
        
        for item in dir(module):
            obj = getattr(module, item)
            if (
                isinstance(obj, type) and
                issubclass(obj, unittest.TestCase) and
                obj != unittest.TestCase
            ):
                test_cases.append(obj)
        
        return test_cases
    
    async def _run_test_case(self, test_case: unittest.TestCase) -> None:
        """Run a specific test case."""
        instance = test_case()
        
        for name in dir(instance):
            if name.startswith('test_'):
                method = getattr(instance, name)
                if callable(method):
                    start_time = time.time()
                    try:
                        # Set up
                        instance.setUp()
                        
                        # Run test
                        if asyncio.iscoroutinefunction(method):
                            await method()
                        else:
                            method()
                        
                        # Record success
                        self.report.add_result(
                            TestResult(
                                name=f"{test_case.__name__}.{name}",
                                status='passed',
                                duration=time.time() - start_time
                            )
                        )
                        
                    except AssertionError as e:
                        # Test failure
                        self.report.add_result(
                            TestResult(
                                name=f"{test_case.__name__}.{name}",
                                status='failed',
                                duration=time.time() - start_time,
                                error=str(e)
                            )
                        )
                        
                    except Exception as e:
                        # Test error
                        self.report.add_result(
                            TestResult(
                                name=f"{test_case.__name__}.{name}",
                                status='error',
                                duration=time.time() - start_time,
                                error=str(e)
                            )
                        )
                        
                    finally:
                        # Clean up
                        instance.tearDown()

async def main():
    """Main entry point for test execution."""
    try:
        # Initialize runner
        runner = TestRunner()
        
        # Run tests
        report = await runner.run_tests()
        
        # Save report
        report.save_report(
            Path(__file__).parent / 'reports' / 
            f"test_report_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
        )
        
        # Print summary
        report.print_summary()
        
        # Exit with appropriate status code
        if report.summary['failed'] > 0 or report.summary['error'] > 0:
            sys.exit(1)
        sys.exit(0)
        
    except Exception as e:
        logger.error(f"Test execution failed: {e}")
        sys.exit(1)

if __name__ == '__main__':
    asyncio.run(main())
