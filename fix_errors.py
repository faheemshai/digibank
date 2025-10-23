#!/usr/bin/env python3
"""
Maven Test Error Analyzer and Fix Suggester

OBJECTIVE:
This program automates the process of identifying, analyzing, and suggesting fixes for
Java test failures in Maven projects. It serves as an intelligent debugging assistant
that bridges the gap between test failure reports and actionable code fixes.

CORE FUNCTIONALITY:
1. **Test Analysis Engine**: Parses Maven Surefire XML test reports to extract detailed
   failure information including stack traces, assertion details, test context, and
   environment data.

2. **Dynamic Source Discovery**: Automatically identifies and includes relevant Java
   source files based on test class names, stack trace analysis, and common naming
   patterns (Service, Controller, Repository, etc.).

3. **AI-Powered Fix Generation**: Leverages IBM watsonx.ai to analyze test failures
   and generate precise, executable code fixes with specific file paths, line numbers,
   and exact code replacements.

4. **Comprehensive Reporting**: Creates structured JSON summaries optimized for both
   human review and AI analysis, including test metrics, failure categorization,
   and contextual information.

PROBLEM SOLVED:
- Eliminates manual analysis of complex test failure reports
- Reduces time from failure identification to fix implementation
- Provides consistent, structured approach to debugging test failures
- Scales debugging expertise across development teams
- Generates actionable fixes rather than just identifying problems

TARGET USE CASES:
- CI/CD pipeline integration for automated fix suggestions
- Developer productivity enhancement during test-driven development
- Code review assistance for test failure analysis
- Knowledge transfer and debugging education
- Rapid prototyping and bug triage in large codebases

WORKFLOW:
1. Analyze: Parse Maven test reports and extract failure details
2. Discover: Dynamically find related source files and test context
3. Generate: Create AI prompts with comprehensive failure information
4. Suggest: Receive specific, actionable code fixes from IBM watsonx.ai
5. Apply: Provide exact file/line/code changes for immediate implementation

Usage:
    python fix_errors.py analyze          # Run test analysis only
    python fix_errors.py suggest          # Generate fix suggestions only
    python fix_errors.py                  # Run both analysis and suggestions
"""

import os
import xml.etree.ElementTree as ET
import glob
import json
import sys
import argparse
import requests
from datetime import datetime
from typing import List, Dict, Any, Optional
import re
from dotenv import load_dotenv


class Logger:
    """Simple structured logger for consistent output formatting."""

    @staticmethod
    def info(message: str):
        print(f"[INFO] {message}")

    @staticmethod
    def warn(message: str):
        print(f"[WARN] {message}")

    @staticmethod
    def error(message: str):
        print(f"[ERROR] {message}")

    @staticmethod
    def success(message: str):
        print(f"[SUCCESS] {message}")

    @staticmethod
    def section(title: str):
        print(f"\n{title.upper()}:")


class TestFailure:
    def __init__(
        self,
        test_class: str,
        test_method: str,
        failure_type: str,
        failure_message: str,
        stack_trace: str,
        execution_time: float,
        failure_category: str,
        raw_failure_text: str,
        system_out: str,
        system_err: str,
    ):
        self.test_class = test_class
        self.test_method = test_method
        self.failure_type = failure_type
        self.failure_message = failure_message
        self.stack_trace = stack_trace
        self.execution_time = execution_time
        self.failure_category = failure_category
        self.raw_failure_text = raw_failure_text
        self.system_out = system_out
        self.system_err = system_err


class TestSuiteResult:
    def __init__(
        self,
        name: str,
        tests: int,
        failures: int,
        errors: int,
        skipped: int,
        time: float,
        report_file: str,
    ):
        self.name = name
        self.tests = tests
        self.failures = failures
        self.errors = errors
        self.skipped = skipped
        self.time = time
        self.report_file = report_file
        self.test_failures: List[TestFailure] = []
        self.properties: Dict[str, str] = {}
        self.suite_log_excerpt: Optional[str] = None


class MavenTestAnalyzer:
    def __init__(self, reports_dir: str = "bank/target/surefire-reports"):
        self.reports_dir = reports_dir
        self.test_suites: List[TestSuiteResult] = []
        self.total_tests = 0
        self.total_failures = 0
        self.total_errors = 0
        self.total_skipped = 0
        self.total_time = 0.0

    def parse_xml_reports(self):
        """Parse all XML test reports in the surefire-reports directory."""
        xml_files = glob.glob(os.path.join(self.reports_dir, "TEST-*.xml"))

        if not xml_files:
            Logger.error(f"No XML test reports found in {self.reports_dir}")
            return

        Logger.info(f"Found {len(xml_files)} test report files")

        for xml_file in xml_files:
            try:
                self._parse_single_xml_report(xml_file)
            except Exception as e:
                Logger.warn(f"Could not parse {xml_file}: {e}")

    def _parse_single_xml_report(self, xml_file: str):
        """Parse a single XML test report file."""
        tree = ET.parse(xml_file)
        root = tree.getroot()

        # Extract test suite information
        suite_name = root.get('name', 'Unknown')
        tests = int(root.get('tests', '0'))
        failures = int(root.get('failures', '0'))
        errors = int(root.get('errors', '0'))
        skipped = int(root.get('skipped', '0'))
        time = float(root.get('time', '0'))

        suite = TestSuiteResult(suite_name, tests, failures, errors, skipped, time, xml_file)

        # Capture suite-level metadata
        suite.properties = self._filter_properties(self._extract_suite_properties(root))
        suite.suite_log_excerpt = self._load_suite_log_excerpt(xml_file)

        # Update totals
        self.total_tests += tests
        self.total_failures += failures
        self.total_errors += errors
        self.total_skipped += skipped
        self.total_time += time

        # Parse individual test cases
        for testcase in root.findall('.//testcase'):
            test_name = testcase.get('name', 'Unknown')
            test_class = testcase.get('classname', 'Unknown')
            test_time = float(testcase.get('time', '0'))

            # Check for failures
            failure_elem = testcase.find('failure')
            if failure_elem is not None:
                failure_type = failure_elem.get('type', 'Unknown')
                failure_text = failure_elem.text or ''
                failure_message = failure_elem.get('message') or self._extract_failure_message(failure_text)
                stack_trace = self._extract_stack_trace(failure_text)

                failure = TestFailure(
                    test_class=test_class,
                    test_method=test_name,
                    failure_type=failure_type,
                    failure_message=failure_message,
                    stack_trace=stack_trace,
                    execution_time=test_time,
                    failure_category='failure',
                    raw_failure_text=failure_text,
                    system_out=self._safe_strip(testcase.findtext('system-out')),
                    system_err=self._safe_strip(testcase.findtext('system-err')),
                )
                suite.test_failures.append(failure)

            # Check for errors
            error_elem = testcase.find('error')
            if error_elem is not None:
                error_type = error_elem.get('type', 'Unknown')
                error_text = error_elem.text or ''
                error_message = error_elem.get('message') or self._extract_failure_message(error_text)
                stack_trace = self._extract_stack_trace(error_text)

                failure = TestFailure(
                    test_class=test_class,
                    test_method=test_name,
                    failure_type=error_type,
                    failure_message=error_message,
                    stack_trace=stack_trace,
                    execution_time=test_time,
                    failure_category='error',
                    raw_failure_text=error_text,
                    system_out=self._safe_strip(testcase.findtext('system-out')),
                    system_err=self._safe_strip(testcase.findtext('system-err')),
                )
                suite.test_failures.append(failure)

        self.test_suites.append(suite)

    def extract_test_dependencies(self, test_file_path: str) -> List[str]:
        """Extract all service/component dependencies from test file."""
        dependencies = []

        if not os.path.exists(test_file_path):
            return dependencies

        try:
            with open(test_file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Extract imports that reference application classes (enhanced patterns)
            import_patterns = [
                # Specific service/component patterns
                r'import\s+([a-zA-Z0-9._]+(?:Service|Controller|Repository|Manager|Helper|Util|Component|Bean|DAO|Handler|Processor|Factory|Builder)[a-zA-Z0-9_]*)\s*;',
                # Any import from the main application package (not test/framework)
                r'import\s+([a-zA-Z0-9._]+(?:\.service\.|\.controller\.|\.repository\.|\.util\.|\.model\.|\.config\.)[a-zA-Z0-9._]+)\s*;',
                # Generic application imports (avoid common framework packages)
                r'import\s+((?:com|org|io|net)\.[a-zA-Z0-9._]+(?<!test)(?<!Test)(?<!junit)(?<!mockito)(?<!spring\.test))\s*;'
            ]

            for pattern in import_patterns:
                for match in re.finditer(pattern, content):
                    class_name = match.group(1)
                    # Skip test and framework imports
                    skip_keywords = ['test', 'junit', 'mockito', 'spring.test', 'hamcrest', 'assertj']
                    if not any(skip in class_name.lower() for skip in skip_keywords):
                        dependencies.append(class_name)

            # Extract @Autowired, @Mock, @InjectMocks field declarations (enhanced)
            dependency_annotations = ['@Autowired', '@Mock', '@InjectMocks', '@Inject', '@Resource']
            for annotation in dependency_annotations:
                # Enhanced pattern to match annotation followed by field declaration (handles multiple lines)
                annotation_pattern = rf'{re.escape(annotation)}(?:\([^)]*\))?\s*'
                field_pattern = rf'{annotation_pattern}(?:private|protected|public)?\s*([A-Z][a-zA-Z0-9_<>]+)\s+(\w+)\s*[;=]'
                for match in re.finditer(field_pattern, content, re.MULTILINE | re.DOTALL):
                    class_type = match.group(1)
                    # Remove generics if present (e.g., List<String> -> List)
                    class_type = re.sub(r'<.*?>', '', class_type)
                    dependencies.append(class_type)

            # Also look for field declarations without annotations but with service-like names
            field_only_pattern = r'(?:private|protected|public)\s+([A-Z][a-zA-Z0-9_]+(?:Service|Repository|Manager|DAO|Helper|Util|Handler))\s+(\w+)\s*[;=]'
            for match in re.finditer(field_only_pattern, content):
                class_type = match.group(1)
                dependencies.append(class_type)

            # Extract classes from @ContextConfiguration
            context_pattern = r'@ContextConfiguration\s*\(\s*classes\s*=\s*\{?([^}]+)\}?\s*\)'
            for match in re.finditer(context_pattern, content):
                classes_str = match.group(1)
                # Extract class names (e.g., SearchService.class -> SearchService)
                class_names = re.findall(r'([A-Z][a-zA-Z0-9_]+)\.class', classes_str)
                dependencies.extend(class_names)

            # Extract method calls to find service usage (e.g., searchService.method())
            method_call_pattern = r'(\w+)\.(\w+)\s*\('
            for match in re.finditer(method_call_pattern, content):
                field_name = match.group(1)
                # Find the type of this field by looking for its declaration
                field_decl_pattern = rf'(?:private|protected|public)?\s*([A-Z][a-zA-Z0-9_]+)\s+{re.escape(field_name)}\s*[;=]'
                field_match = re.search(field_decl_pattern, content)
                if field_match:
                    field_type = field_match.group(1)
                    dependencies.append(field_type)

            return list(set(dependencies))  # Remove duplicates

        except Exception as e:
            Logger.warn(f"Could not parse dependencies from {test_file_path}: {e}")
            return dependencies

    def _get_test_source_info(self, test_class: str, test_method: str) -> Dict[str, Any]:
        """Try to find the source file for the test and extract relevant lines."""
        # Convert class name to file path
        class_path = test_class.replace('.', '/') + '.java'

        # Common test source directories
        possible_paths = [
            f"bank/src/test/java/{class_path}",
            f"src/test/java/{class_path}",
            f"test/{class_path}"
        ]

        notes = []
        for path in possible_paths:
            if os.path.exists(path):
                try:
                    with open(path, 'r', encoding='utf-8') as f:
                        content = f.read()

                    # Find the test method
                    method_pattern = rf'(public|private|protected)?\s+void\s+{re.escape(test_method)}\s*\([^)]*\)'
                    match = re.search(method_pattern, content)

                    if match:
                        lines = content.split('\n')
                        method_line_index = content[:match.start()].count('\n')
                        start_line = max(0, method_line_index - 5)
                        end_line = min(len(lines), method_line_index + 30)

                        method_context = '\n'.join(lines[start_line:end_line])
                        return {
                            'found': True,
                            'path': path,
                            'method_signature': lines[method_line_index].strip() if method_line_index < len(lines) else '',
                            'context_start_line': start_line + 1,
                            'context_end_line': end_line,
                            'context': method_context,
                        }
                    else:
                        notes.append(f"Method '{test_method}' not found in {path}")
                except Exception as e:
                    notes.append(f"Could not read source file {path}: {e}")

        return {
            'found': False,
            'path': None,
            'context': None,
            'searched_paths': possible_paths,
            'notes': notes if notes else [f"Source file not found for {test_class}"],
        }

    def _extract_suite_properties(self, root: ET.Element) -> Dict[str, str]:
        properties = {}
        for prop in root.findall('./properties/property'):
            name = prop.get('name')
            value = prop.get('value')
            if name is not None and value is not None:
                properties[name] = value
        return properties

    def _load_suite_log_excerpt(self, xml_file: str, max_chars: int = 2000) -> Optional[str]:
        base_name = os.path.basename(xml_file)
        txt_name = base_name.replace('TEST-', '').replace('.xml', '.txt')
        txt_path = os.path.join(self.reports_dir, txt_name)
        if os.path.exists(txt_path):
            try:
                with open(txt_path, 'r', encoding='utf-8', errors='replace') as fh:
                    content = fh.read()
                return self._truncate_text(content, max_chars)
            except Exception as exc:
                return f"Could not read suite log {txt_path}: {exc}"
        return None

    @staticmethod
    def _filter_properties(properties: Dict[str, str]) -> Dict[str, str]:
        if not properties:
            return {}
        relevant_keys = {
            'java.version',
            'java.vendor',
            'os.name',
            'os.version',
            'os.arch',
            'user.dir',
            'user.language',
            'user.country',
            'basedir',
            'spring.profiles.active',
        }
        return {k: v for k, v in properties.items() if k in relevant_keys}

    @staticmethod
    def _extract_relevant_log(text: str, limit: int) -> str:
        if not text:
            return ''
        lines = [line.rstrip() for line in text.strip().splitlines()]
        important = [
            line for line in lines
            if re.search(
                r'(ERROR|WARN|Exception:|Caused by|AssertionFailedError|expected:|actual:|\bFAIL(?:URE)?!?)',
                line,
                re.IGNORECASE,
            )
        ]

        if not important:
            return ''

        snippet = '\n'.join(important)
        return MavenTestAnalyzer._truncate_text(snippet, limit) or ''

    @staticmethod
    def _truncate_text(value: Optional[str], limit: int) -> Optional[str]:
        if value is None:
            return None
        text = value.strip()
        if len(text) <= limit:
            return text
        truncated = text[:limit]
        return f"{truncated}\n...[truncated {len(text) - limit} characters]"

    @staticmethod
    def _safe_strip(value: Optional[str]) -> str:
        if value is None:
            return ''
        return value.strip()

    @staticmethod
    def _extract_failure_message(raw_text: str) -> str:
        if not raw_text:
            return ''
        first_line = raw_text.strip().splitlines()[0]
        return first_line.strip()

    @staticmethod
    def _extract_stack_trace(raw_text: str) -> str:
        if not raw_text:
            return ''
        lines = raw_text.strip().splitlines()
        if len(lines) <= 1:
            return raw_text.strip()
        return '\n'.join(lines[1:]).strip()

    @staticmethod
    def _extract_failure_location(stack_trace: str) -> Optional[Dict[str, Any]]:
        if not stack_trace:
            return None
        for line in stack_trace.splitlines():
            match = re.search(r'\(([^():\s]+):(\d+)\)', line)
            if match:
                return {
                    'file': match.group(1),
                    'line': int(match.group(2)),
                    'stack_line': line.strip(),
                }
        return None

    @staticmethod
    def _extract_assertion_details(message: str) -> Optional[Dict[str, Any]]:
        if not message:
            return None
        match = re.search(r'expected:\s*<(.*)>\s*but was:\s*<(.*)>', message)
        if match:
            return {
                'expected': match.group(1),
                'actual': match.group(2),
            }
        return None

    def generate_failures_summary(self, output_file: str = "output/error-summary.json"):
        """Generate a comprehensive failures summary for LLM analysis in JSON."""
        success_count = self.total_tests - self.total_failures - self.total_errors
        success_rate = (
            (success_count / self.total_tests * 100)
            if self.total_tests
            else 0.0
        )

        report_payload: Dict[str, Any] = {
            'metadata': {
                'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'reports_directory': self.reports_dir,
                'total_suites': len(self.test_suites),
            },
            'summary': {
                'total_tests': self.total_tests,
                'total_failures': self.total_failures,
                'total_errors': self.total_errors,
                'total_skipped': self.total_skipped,
                'total_time_seconds': round(self.total_time, 3),
                'successful_tests': success_count,
                'success_rate_percent': round(success_rate, 2),
            },
            'suites': [],
            'analysis_guidance': {
                'prompt': (
                    "Analyze the failing Maven Surefire tests, explain the root cause for each "
                    "failure, recommend precise code/configuration fixes, and highlight regression "
                    "risks or missing test coverage."
                ),
                'suggested_steps': [
                    'Review each failure entry, paying attention to stack traces and assertion details.',
                    'Use the source context to pinpoint the code under test and propose updates.',
                    'Validate whether external dependencies, data fixtures, or configuration need adjustments.',
                    'Recommend additional tests or assertions to prevent future regressions.',
                ],
            },
        }

        for suite in self.test_suites:
            suite_dict: Dict[str, Any] = {
                'name': suite.name,
                'report_file': suite.report_file,
                'tests': suite.tests,
                'failures': suite.failures,
                'errors': suite.errors,
                'skipped': suite.skipped,
                'time_seconds': round(suite.time, 3),
                'status': 'PASSED' if (suite.failures + suite.errors) == 0 else 'FAILED',
                'failures': [],
            }

            for failure in suite.test_failures:
                source_info = self._get_test_source_info(failure.test_class, failure.test_method)
                failure_location = self._extract_failure_location(failure.stack_trace)
                assertion_details = self._extract_assertion_details(
                    failure.failure_message or failure.raw_failure_text
                )

                failure_dict: Dict[str, Any] = {
                    'test_class': failure.test_class,
                    'test_method': failure.test_method,
                    'failure_type': failure.failure_type,
                    'failure_category': failure.failure_category,
                    'execution_time_seconds': round(failure.execution_time, 3),
                    'failure_message': failure.failure_message,
                    'stack_trace': failure.stack_trace,
                    'failure_location': failure_location,
                    'assertion_details': assertion_details,
                    'system_out_excerpt': self._extract_relevant_log(failure.system_out, 400),
                    'system_err_excerpt': self._extract_relevant_log(failure.system_err, 400),
                    'test_source': source_info,
                }

                if failure.raw_failure_text and failure.raw_failure_text.strip() != failure.failure_message:
                    failure_dict['raw_failure_excerpt'] = self._truncate_text(failure.raw_failure_text, 400)

                suite_dict['failures'].append(failure_dict)

            if suite.properties:
                suite_dict['environment'] = suite.properties
            if suite.suite_log_excerpt:
                suite_dict['suite_log_excerpt'] = suite.suite_log_excerpt

            report_payload['suites'].append(suite_dict)

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(report_payload, f, indent=2)

        Logger.info(f"Summary saved to {output_file}")

    def run_analysis(self):
        """Run the complete analysis process."""
        Logger.info(f"Analyzing test reports in {self.reports_dir}")

        if not os.path.exists(self.reports_dir):
            Logger.error(f"Reports directory '{self.reports_dir}' not found")
            Logger.error("Please run 'mvn test' first to generate test reports")
            return False

        self.parse_xml_reports()

        if self.total_tests == 0:
            Logger.error("No tests found in the reports")
            return False

        self.generate_failures_summary()

        success_count = self.total_tests - self.total_failures - self.total_errors
        success_rate = (success_count / self.total_tests * 100) if self.total_tests > 0 else 0

        Logger.info(f"Analysis complete: {self.total_tests} tests, {self.total_failures} failures, {self.total_errors} errors ({success_rate:.0f}% pass rate)")

        if self.total_failures > 0 or self.total_errors > 0:
            Logger.info("Summary saved to 'output/error-summary.json'")
            return True
        else:
            Logger.success("All tests passed")
            return False


class FixSuggester:
    def __init__(self):
        load_dotenv()
        self.api_key = os.getenv("IBM_API_KEY")
        if not self.api_key:
            Logger.error("IBM_API_KEY not found in environment variables")
            Logger.error("Please check your .env file")
            sys.exit(1)

    def extract_test_dependencies(self, test_file_path: str) -> List[str]:
        """Extract all service/component dependencies from test file."""
        dependencies = []

        if not os.path.exists(test_file_path):
            return dependencies

        try:
            with open(test_file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Extract imports that reference application classes (enhanced patterns)
            import_patterns = [
                # Specific service/component patterns
                r'import\s+([a-zA-Z0-9._]+(?:Service|Controller|Repository|Manager|Helper|Util|Component|Bean|DAO|Handler|Processor|Factory|Builder)[a-zA-Z0-9_]*)\s*;',
                # Any import from the main application package (not test/framework)
                r'import\s+([a-zA-Z0-9._]+(?:\.service\.|\.controller\.|\.repository\.|\.util\.|\.model\.|\.config\.)[a-zA-Z0-9._]+)\s*;',
                # Generic application imports (avoid common framework packages)
                r'import\s+((?:com|org|io|net)\.[a-zA-Z0-9._]+(?<!test)(?<!Test)(?<!junit)(?<!mockito)(?<!spring\.test))\s*;'
            ]

            for pattern in import_patterns:
                for match in re.finditer(pattern, content):
                    class_name = match.group(1)
                    # Skip test and framework imports
                    skip_keywords = ['test', 'junit', 'mockito', 'spring.test', 'hamcrest', 'assertj']
                    if not any(skip in class_name.lower() for skip in skip_keywords):
                        dependencies.append(class_name)

            # Extract @Autowired, @Mock, @InjectMocks field declarations (enhanced)
            dependency_annotations = ['@Autowired', '@Mock', '@InjectMocks', '@Inject', '@Resource']
            for annotation in dependency_annotations:
                # Enhanced pattern to match annotation followed by field declaration (handles multiple lines)
                annotation_pattern = rf'{re.escape(annotation)}(?:\([^)]*\))?\s*'
                field_pattern = rf'{annotation_pattern}(?:private|protected|public)?\s*([A-Z][a-zA-Z0-9_<>]+)\s+(\w+)\s*[;=]'
                for match in re.finditer(field_pattern, content, re.MULTILINE | re.DOTALL):
                    class_type = match.group(1)
                    # Remove generics if present (e.g., List<String> -> List)
                    class_type = re.sub(r'<.*?>', '', class_type)
                    dependencies.append(class_type)

            # Also look for field declarations without annotations but with service-like names
            field_only_pattern = r'(?:private|protected|public)\s+([A-Z][a-zA-Z0-9_]+(?:Service|Repository|Manager|DAO|Helper|Util|Handler))\s+(\w+)\s*[;=]'
            for match in re.finditer(field_only_pattern, content):
                class_type = match.group(1)
                dependencies.append(class_type)

            # Extract classes from @ContextConfiguration
            context_pattern = r'@ContextConfiguration\s*\(\s*classes\s*=\s*\{?([^}]+)\}?\s*\)'
            for match in re.finditer(context_pattern, content):
                classes_str = match.group(1)
                # Extract class names (e.g., SearchService.class -> SearchService)
                class_names = re.findall(r'([A-Z][a-zA-Z0-9_]+)\.class', classes_str)
                dependencies.extend(class_names)

            # Extract method calls to find service usage (e.g., searchService.method())
            method_call_pattern = r'(\w+)\.(\w+)\s*\('
            for match in re.finditer(method_call_pattern, content):
                field_name = match.group(1)
                # Find the type of this field by looking for its declaration
                field_decl_pattern = rf'(?:private|protected|public)?\s*([A-Z][a-zA-Z0-9_]+)\s+{re.escape(field_name)}\s*[;=]'
                field_match = re.search(field_decl_pattern, content)
                if field_match:
                    field_type = field_match.group(1)
                    dependencies.append(field_type)

            return list(set(dependencies))  # Remove duplicates

        except Exception as e:
            Logger.warn(f"Could not parse dependencies from {test_file_path}: {e}")
            return dependencies

    def analyze_code_for_logic_bugs(self, source_code: str, failure_details: Dict) -> List[Dict]:
        """Analyze source code for potential logic bugs based on test expectations."""
        potential_bugs = []

        if not source_code or not failure_details:
            return potential_bugs

        lines = source_code.split('\n')
        assertion_details = failure_details.get('assertion_details', {})
        expected = assertion_details.get('expected')
        actual = assertion_details.get('actual')

        # Look for suspicious conditions when we expect a specific count but get 0
        if expected and actual == '0':
            try:
                expected_count = int(expected)
                if expected_count > 0:
                    # Search for problematic conditional statements
                    for i, line in enumerate(lines):
                        line_clean = line.strip()

                        # Look for if statements with count comparisons
                        if line_clean.startswith('if') and 'count' in line_clean.lower():
                            # Check for common logic errors
                            for operator in ['>', '>=', '<', '<=']:
                                if operator in line_clean:
                                    # Extract the comparison value
                                    try:
                                        # Simple pattern matching for "if (count > N)"
                                        match = re.search(rf'count\s*{re.escape(operator)}\s*(\d+)', line_clean, re.IGNORECASE)
                                        if match:
                                            comparison_value = int(match.group(1))

                                            # Flag potential off-by-one errors
                                            if operator in ['>', '>='] and comparison_value >= expected_count:
                                                potential_bugs.append({
                                                    'line_number': i + 1,
                                                    'line_content': line_clean,
                                                    'bug_type': 'off_by_one_error',
                                                    'description': f'Condition requires count {operator} {comparison_value}, but test expects {expected_count} items',
                                                    'suggested_fix': f'Change to "count > 0" or "count >= {expected_count}"',
                                                    'confidence': 'high'
                                                })
                                    except (ValueError, AttributeError):
                                        continue

                        # Look for array/list size checks that might cause empty returns
                        size_keywords = ['size()', 'length', 'count', '.size', '.length()']
                        for keyword in size_keywords:
                            if keyword in line_clean.lower() and any(op in line_clean for op in ['>', '<', '>=', '<=']):
                                potential_bugs.append({
                                    'line_number': i + 1,
                                    'line_content': line_clean,
                                    'bug_type': 'size_check_error',
                                    'description': f'Size check on line {i + 1} might prevent returning expected {expected_count} items',
                                    'suggested_fix': 'Review the size comparison logic',
                                    'confidence': 'medium'
                                })

                        # Look for empty return statements in conditional blocks
                        if ('return' in line_clean and
                            ('empty' in line_clean.lower() or 'new arraylist()' in line_clean.lower() or
                             'collections.emptylist()' in line_clean.lower() or 'return [];' in line_clean)):
                            potential_bugs.append({
                                'line_number': i + 1,
                                'line_content': line_clean,
                                'bug_type': 'empty_return',
                                'description': 'Empty return statement might be executed when data should be returned',
                                'suggested_fix': 'Check if this return should be conditional',
                                'confidence': 'medium'
                            })

            except ValueError:
                pass  # expected is not a number

        return potential_bugs

    def get_access_token(self):
        """Get IBM Cloud access token using API key."""
        url = "https://iam.cloud.ibm.com/identity/token"
        payload = f"grant_type=urn:ibm:params:oauth:grant-type:apikey&apikey={self.api_key}"
        headers = {"Content-Type": "application/x-www-form-urlencoded"}

        try:
            response = requests.post(url, data=payload, headers=headers)
            response.raise_for_status()
            return response.json()["access_token"]
        except requests.exceptions.RequestException as e:
            Logger.error(f"Failed to get access token: {e}")
            sys.exit(1)
        except KeyError:
            Logger.error("Invalid response format when getting access token")
            sys.exit(1)

    def load_failure_data(self, file_path: str = "output/error-summary.json") -> Dict[str, Any]:
        """Load test failure data from JSON file."""
        try:
            with open(file_path, 'r') as file:
                return json.load(file)
        except FileNotFoundError:
            Logger.error(f"{file_path} not found")
            Logger.error("Please run analysis first to generate the error summary")
            sys.exit(1)
        except json.JSONDecodeError as e:
            Logger.error(f"Error parsing {file_path}: {e}")
            sys.exit(1)

    def load_source_code(self, file_path: str) -> str:
        """Load source code from a file for analysis."""
        try:
            with open(file_path, 'r') as file:
                return file.read()
        except FileNotFoundError:
            Logger.warn(f"Source file {file_path} not found")
            return ""
        except Exception as e:
            Logger.warn(f"Could not read {file_path}: {e}")
            return ""

    def find_related_source_files(self, test_class: str, failure_message: str, stack_trace: str, test_file_path: str = None) -> List[str]:
        """Find related source files based on test class name, failure message, stack trace, and test dependencies."""
        related_files = []
        all_dependencies = set()

        # 1. Extract dependencies from test file if available
        if test_file_path:
            test_dependencies = self.extract_test_dependencies(test_file_path)
            all_dependencies.update(test_dependencies)

        # 2. Extract class names from test class (remove "Test" suffix and common patterns)
        base_class_name = test_class.split('.')[-1]  # Get the last part of the package

        # Remove common test suffixes
        for suffix in ['Test', 'Tests', 'IT', 'Integration']:
            if base_class_name.endswith(suffix):
                base_class_name = base_class_name[:-len(suffix)]
                break

        # 3. Look for classes mentioned in stack trace
        stack_classes = set()
        if stack_trace:
            for line in stack_trace.split('\n'):
                # Find class references in stack trace (e.g., at com.example.Service.method(Service.java:123))
                if 'at ' in line and '.java:' in line:
                    try:
                        class_part = line.split('at ')[1].split('(')[0]
                        # Extract full class name, not just the last part
                        full_class_name = class_part.rsplit('.', 1)[0]  # Remove method name
                        class_name = class_part.split('.')[-2] if '.' in class_part else None
                        if class_name and not class_name.endswith('Test'):
                            stack_classes.add(class_name)
                            # Also add the full class name for better matching
                            if full_class_name and not full_class_name.endswith('Test'):
                                all_dependencies.add(full_class_name)
                    except (IndexError, AttributeError):
                        continue

        # 4. Common source file patterns to search for
        search_patterns = [
            base_class_name,  # Direct mapping (e.g., AtmLocationSearch -> AtmLocationSearch)
            base_class_name + 'Service',  # Service pattern
            base_class_name + 'Controller',  # Controller pattern
            base_class_name + 'Repository',  # Repository pattern
            base_class_name + 'Manager',  # Manager pattern
        ]

        # Add classes found in stack trace
        search_patterns.extend(stack_classes)

        # 5. Add dependency class names to search patterns
        for dependency in all_dependencies:
            if '.' in dependency:
                # Full package name (e.g., io.digisic.bank.service.SearchService)
                class_name = dependency.split('.')[-1]
                search_patterns.append(class_name)
            else:
                # Simple class name
                search_patterns.append(dependency)

        # 6. Dynamically detect source directories
        source_dirs = []
        possible_source_roots = [".", "bank", "src", "main"]
        for root in possible_source_roots:
            for subdir in ["src/main/java", "main/java", "java"]:
                potential_dir = os.path.join(root, subdir) if root != "." else subdir
                if os.path.exists(potential_dir):
                    source_dirs.append(potential_dir)

        # Remove duplicates while preserving order
        source_dirs = list(dict.fromkeys(source_dirs))

        # 7. Search for files by pattern matching
        for source_dir in source_dirs:
            if os.path.exists(source_dir):
                for pattern in search_patterns:
                    # Use glob to find matching files
                    for root, dirs, files in os.walk(source_dir):
                        for file in files:
                            if file.endswith('.java') and pattern in file:
                                full_path = os.path.join(root, file)
                                if full_path not in related_files:
                                    related_files.append(full_path)

        # 8. Search for files by full package name (more precise)
        for dependency in all_dependencies:
            if '.' in dependency:
                # Convert package name to file path (e.g., io.digisic.bank.service.SearchService -> io/digisic/bank/service/SearchService.java)
                package_path = dependency.replace('.', '/') + '.java'
                for source_dir in source_dirs:
                    potential_file = os.path.join(source_dir, package_path)
                    if os.path.exists(potential_file) and potential_file not in related_files:
                        related_files.append(potential_file)

        # 9. Search for files in same package as test
        test_package = '.'.join(test_class.split('.')[:-1])  # Remove class name
        if test_package:
            # Convert test package to main package (e.g., io.digisic.bank.test.junit.search -> io.digisic.bank.service)
            main_package_variants = [
                test_package.replace('.test.junit.', '.').replace('.test.', '.'),  # Remove test parts
                test_package.replace('.test.junit.search', '.service'),  # Specific mapping
                test_package.replace('.test.junit', '.service'),  # General mapping
                test_package.replace('.test', ''),  # Remove test completely
            ]

            for main_package in main_package_variants:
                package_path = main_package.replace('.', '/')
                for source_dir in source_dirs:
                    package_dir = os.path.join(source_dir, package_path)
                    if os.path.exists(package_dir):
                        for file in os.listdir(package_dir):
                            if file.endswith('.java'):
                                full_path = os.path.join(package_dir, file)
                                if full_path not in related_files:
                                    related_files.append(full_path)

        return related_files

    def analyze_code_for_logic_bugs(self, source_code: str, failure_details: Dict) -> List[Dict]:
        """Analyze source code for potential logic bugs based on test expectations."""
        potential_bugs = []

        if not source_code or not failure_details:
            return potential_bugs

        lines = source_code.split('\n')
        assertion_details = failure_details.get('assertion_details', {})
        expected = assertion_details.get('expected')
        actual = assertion_details.get('actual')

        # Look for suspicious conditions when we expect a specific count but get 0
        if expected and actual == '0':
            try:
                expected_count = int(expected)
                if expected_count > 0:
                    # Search for problematic conditional statements
                    for i, line in enumerate(lines):
                        line_clean = line.strip()

                        # Look for if statements with count comparisons
                        if line_clean.startswith('if') and 'count' in line_clean.lower():
                            # Check for common logic errors
                            for operator in ['>', '>=', '<', '<=']:
                                if operator in line_clean:
                                    # Extract the comparison value
                                    try:
                                        # Simple pattern matching for "if (count > N)"
                                        match = re.search(rf'count\s*{re.escape(operator)}\s*(\d+)', line_clean, re.IGNORECASE)
                                        if match:
                                            comparison_value = int(match.group(1))

                                            # Flag potential off-by-one errors
                                            if operator in ['>', '>='] and comparison_value >= expected_count:
                                                potential_bugs.append({
                                                    'line_number': i + 1,
                                                    'line_content': line_clean,
                                                    'bug_type': 'off_by_one_error',
                                                    'description': f'Condition requires count {operator} {comparison_value}, but test expects {expected_count} items',
                                                    'suggested_fix': f'Change to "count > 0" or "count >= {expected_count}"',
                                                    'confidence': 'high'
                                                })
                                    except (ValueError, AttributeError):
                                        continue

                        # Look for array/list size checks that might cause empty returns
                        size_keywords = ['size()', 'length', 'count', '.size', '.length()']
                        for keyword in size_keywords:
                            if keyword in line_clean.lower() and any(op in line_clean for op in ['>', '<', '>=', '<=']):
                                potential_bugs.append({
                                    'line_number': i + 1,
                                    'line_content': line_clean,
                                    'bug_type': 'size_check_error',
                                    'description': f'Size check on line {i + 1} might prevent returning expected {expected_count} items',
                                    'suggested_fix': 'Review the size comparison logic',
                                    'confidence': 'medium'
                                })

                        # Look for empty return statements in conditional blocks
                        if ('return' in line_clean and
                            ('empty' in line_clean.lower() or 'new arraylist()' in line_clean.lower() or
                             'collections.emptylist()' in line_clean.lower() or 'return [];' in line_clean)):
                            potential_bugs.append({
                                'line_number': i + 1,
                                'line_content': line_clean,
                                'bug_type': 'empty_return',
                                'description': 'Empty return statement might be executed when data should be returned',
                                'suggested_fix': 'Check if this return should be conditional',
                                'confidence': 'medium'
                            })

            except ValueError:
                pass  # expected is not a number

        return potential_bugs

    def generate_prompt(self, failure_data: Dict[str, Any]) -> str:
        """Generate a prompt for the AI model based on failure data."""
        prompt = "You are a Java debugging expert. Analyze the test failure and provide EXACT CODE FIXES that can be directly applied.\n\n"
        prompt += "IMPORTANT: Provide specific file paths, line numbers, and exact code replacements in this format:\n"
        prompt += "FILE: path/to/file.java\n"
        prompt += "LINE: 123\n"
        prompt += "REPLACE: old code here\n"
        prompt += "WITH: new code here\n\n"

        # Add summary information
        summary = failure_data.get("summary", {})
        prompt += f"**Test Summary:**\n"
        prompt += f"- Total tests: {summary.get('total_tests', 'N/A')}\n"
        prompt += f"- Failures: {summary.get('total_failures', 'N/A')}\n"
        prompt += f"- Success rate: {summary.get('success_rate_percent', 'N/A')}%\n\n"

        # Add failure details
        for suite in failure_data.get("suites", []):
            if suite.get("failures"):
                prompt += f"**Failed Test Suite: {suite['name']}**\n\n"

                for failure in suite["failures"]:
                    prompt += f"**Test Method:** {failure['test_method']}\n"
                    prompt += f"**Failure Type:** {failure['failure_type']}\n"
                    prompt += f"**Error Message:** {failure['failure_message']}\n"

                    if failure.get('failure_location'):
                        prompt += f"**Location:** {failure['failure_location']['file']}:{failure['failure_location']['line']}\n\n"

                    # Add assertion details if available
                    if failure.get("assertion_details"):
                        assertion = failure["assertion_details"]
                        prompt += f"**Assertion Details:**\n"
                        prompt += f"- Expected: {assertion.get('expected')}\n"
                        prompt += f"- Actual: {assertion.get('actual')}\n\n"

                    # Add test source context
                    if failure.get("test_source", {}).get("context"):
                        prompt += f"**Test Source Code:**\n```java\n{failure['test_source']['context']}\n```\n\n"

                    # Find and include related source code from the implementation
                    test_file_path = failure.get("test_source", {}).get("path")
                    related_files = self.find_related_source_files(
                        failure['test_class'],
                        failure.get('failure_message', ''),
                        failure.get('stack_trace', ''),
                        test_file_path
                    )

                    # Analyze related source files for potential logic bugs
                    all_potential_bugs = []
                    for related_file in related_files:
                        source_code = self.load_source_code(related_file)
                        if source_code:
                            prompt += f"**Related Source Code ({related_file}):**\n```java\n{source_code}\n```\n\n"

                            # Analyze this source file for potential bugs
                            bugs = self.analyze_code_for_logic_bugs(source_code, failure)
                            if bugs:
                                all_potential_bugs.extend([(related_file, bug) for bug in bugs])

                    # Add potential bug analysis to prompt
                    if all_potential_bugs:
                        prompt += "**🚨 POTENTIAL LOGIC BUGS DETECTED:**\n"
                        for file_path, bug in all_potential_bugs:
                            prompt += f"- **{bug['bug_type']}** in {file_path}:{bug['line_number']}\n"
                            prompt += f"  Line: `{bug['line_content']}`\n"
                            prompt += f"  Issue: {bug['description']}\n"
                            prompt += f"  Suggested Fix: {bug['suggested_fix']}\n"
                            prompt += f"  Confidence: {bug['confidence']}\n\n"

                    # Add environment info
                    if suite.get("environment"):
                        env = suite["environment"]
                        prompt += f"**Environment:**\n"
                        prompt += f"- Java Version: {env.get('java.version', 'N/A')}\n"
                        prompt += f"- OS: {env.get('os.name', 'N/A')} {env.get('os.version', 'N/A')}\n\n"

        prompt += "REQUIRED OUTPUT FORMAT:\n"
        prompt += "1. **ROOT CAUSE**: Brief explanation of what's wrong\n"
        prompt += "2. **EXACT FIXES**: For each file that needs changes:\n"
        prompt += "   FILE: exact/path/to/file.java\n"
        prompt += "   LINE: line_number\n"
        prompt += "   REPLACE: exact_current_code\n"
        prompt += "   WITH: exact_new_code\n\n"
        prompt += "3. **VERIFICATION**: How to verify the fix works\n\n"
        prompt += "Focus on providing executable, copy-paste ready code fixes.\n"

        return prompt

    def call_watsonx_ai(self, access_token: str, prompt: str) -> str:
        """Make API call to watsonx.ai to get fix suggestions."""
        url = "https://us-south.ml.cloud.ibm.com/ml/v1/text/chat?version=2024-03-14"

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

        payload = {
            "model_id": "mistralai/mistral-medium-2505",
            "space_id": "d8bd8d84-b101-4006-90c3-22dc4019748a",
            "messages": [
                {
                    "role": "system",
                    "content": "You are a Java debugging expert who provides EXACT, EXECUTABLE code fixes. Always specify the exact file path, line number, current code, and replacement code. Focus on providing actionable fixes that can be directly applied to resolve test failures."
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": prompt
                        }
                    ]
                }
            ],
            "max_completion_tokens": 16384,
            "temperature": 0.1,
        }

        try:
            response = requests.post(url, json=payload, headers=headers)
            response.raise_for_status()

            result = response.json()
            # Extract the AI response from the API response
            if "choices" in result and len(result["choices"]) > 0:
                return result["choices"][0]["message"]["content"]
            else:
                return "No response received from the AI model"

        except requests.exceptions.RequestException as e:
            Logger.error(f"watsonx.ai API call failed: {e}")
            if hasattr(e, 'response') and e.response is not None:
                Logger.error(f"Response status: {e.response.status_code}")
            sys.exit(1)
        except Exception as e:
            Logger.error(f"Unexpected error: {e}")
            sys.exit(1)

    def parse_ai_response(self, ai_response: str, failure_data: Dict[str, Any]) -> Dict[str, Any]:
        """Parse AI response into structured JSON format."""
        fixes = []

        # Split response into lines for parsing
        lines = ai_response.split('\n')

        # Variables to track current fix being parsed
        current_fix = {}
        root_cause = ""
        verification = ""
        additional_notes = ""
        in_root_cause = False
        in_verification = False
        in_notes = False

        # Parse the AI response line by line
        for i, line in enumerate(lines):
            line_stripped = line.strip()

            # Check for ROOT CAUSE section
            if '**ROOT CAUSE' in line or 'ROOT CAUSE:' in line:
                in_root_cause = True
                in_verification = False
                in_notes = False
                continue

            # Check for EXACT FIXES section
            if '**EXACT FIXES' in line or 'EXACT FIXES:' in line:
                in_root_cause = False
                in_verification = False
                in_notes = False
                continue

            # Check for VERIFICATION section
            if '**VERIFICATION' in line or 'VERIFICATION:' in line:
                in_verification = True
                in_root_cause = False
                in_notes = False
                continue

            # Check for ADDITIONAL NOTES section
            if '**ADDITIONAL NOTES' in line or 'ADDITIONAL NOTES:' in line:
                in_notes = True
                in_root_cause = False
                in_verification = False
                continue

            # Capture root cause
            if in_root_cause and line_stripped:
                root_cause += line_stripped + " "

            # Capture verification
            if in_verification and line_stripped:
                verification += line_stripped + " "

            # Capture additional notes
            if in_notes and line_stripped:
                additional_notes += line_stripped + " "

            # Parse FILE, LINE, REPLACE, WITH pattern
            if line_stripped.startswith('FILE:'):
                # Save previous fix if exists
                if current_fix and 'file_path' in current_fix:
                    fixes.append(current_fix)

                # Start new fix
                current_fix = {
                    'file_path': line_stripped.replace('FILE:', '').strip()
                }
            elif line_stripped.startswith('LINE:'):
                if current_fix:
                    try:
                        current_fix['line_number'] = int(line_stripped.replace('LINE:', '').strip())
                    except ValueError:
                        current_fix['line_number'] = line_stripped.replace('LINE:', '').strip()
            elif line_stripped.startswith('REPLACE:'):
                if current_fix:
                    # Capture the REPLACE content (might be multi-line)
                    replace_content = line_stripped.replace('REPLACE:', '').strip()
                    if replace_content.startswith('`'):
                        replace_content = replace_content.strip('`')
                    current_fix['current_code'] = replace_content
            elif line_stripped.startswith('WITH:'):
                if current_fix:
                    # Capture the WITH content (might be multi-line)
                    with_content = line_stripped.replace('WITH:', '').strip()
                    if with_content.startswith('`'):
                        with_content = with_content.strip('`')
                    current_fix['fixed_code'] = with_content

        # Don't forget the last fix
        if current_fix and 'file_path' in current_fix:
            fixes.append(current_fix)

        # Extract test information from failure_data
        test_info = []
        for suite in failure_data.get('suites', []):
            for failure in suite.get('failures', []):
                test_info.append({
                    'test_class': failure.get('test_class'),
                    'test_method': failure.get('test_method'),
                    'failure_type': failure.get('failure_type')
                })

        # Associate test info with fixes if possible
        for i, fix in enumerate(fixes):
            if i < len(test_info):
                fix['test_class'] = test_info[i]['test_class']
                fix['test_method'] = test_info[i]['test_method']
            fix['root_cause'] = root_cause.strip() if root_cause else "See AI response for details"
            fix['verification'] = verification.strip() if verification else "Run the test to verify the fix"
            if additional_notes:
                fix['additional_notes'] = additional_notes.strip()

        return {
            'metadata': {
                'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'total_failures': failure_data.get('summary', {}).get('total_failures', 0),
                'ai_model': 'mistralai/mistral-medium-2505'
            },
            'fixes': fixes,
            'raw_ai_response': ai_response  # Keep the raw response for reference
        }

    def suggest_fixes(self, output_file: str = "output/suggested-fixes.json"):
        """Main function to generate fix suggestions in JSON format."""
        Logger.info("Starting fix suggestion generation")

        # Load failure data
        failure_data = self.load_failure_data()

        # Check if there are any failures to analyze
        total_failures = failure_data.get("summary", {}).get("total_failures", 0)
        if total_failures == 0:
            Logger.success("No test failures found to analyze")
            return

        Logger.warn(f"Failed tests detected - generating fix suggestions for {total_failures} failure(s)")

        # Generate prompt and get suggestions
        Logger.info("Authenticating with IBM Cloud")
        access_token = self.get_access_token()

        Logger.info(f"Generating fixes for {total_failures} test failures")
        prompt = self.generate_prompt(failure_data)
        ai_response = self.call_watsonx_ai(access_token, prompt)

        # Parse AI response into structured JSON
        structured_fixes = self.parse_ai_response(ai_response, failure_data)

        # Save results as JSON
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(structured_fixes, f, indent=2)

        Logger.success(f"Fixes saved to {output_file}")

        # Display concise summary
        Logger.section("Fix Summary")
        self._display_fix_summary(structured_fixes)

    def _display_fix_summary(self, structured_fixes: Dict[str, Any]):
        """Display a concise summary of the suggested fixes from JSON structure."""
        fixes = structured_fixes.get('fixes', [])

        if not fixes:
            print("  No fixes were parsed from the AI response")
            print("  Review the raw AI response in the output file")
            return

        for i, fix in enumerate(fixes, 1):
            file_name = fix.get('file_path', 'Unknown').split('/')[-1]
            line_num = fix.get('line_number', '?')
            test_method = fix.get('test_method', '')

            # Create a concise description
            if fix.get('current_code'):
                issue = fix['current_code'][:50]
                if len(fix['current_code']) > 50:
                    issue += '...'
            else:
                issue = 'Fix available'

            # Display with test context if available
            if test_method:
                print(f"  {i}. {file_name}:{line_num} - {issue} (Test: {test_method})")
            else:
                print(f"  {i}. {file_name}:{line_num} - {issue}")

        # Show metadata
        metadata = structured_fixes.get('metadata', {})
        print(f"\n  Total failures analyzed: {metadata.get('total_failures', 'N/A')}")
        print(f"  Fixes generated: {len(fixes)}")


def main():
    # Run both analysis and suggestions
    Logger.info("Starting Maven test error analysis and fix suggestion workflow")

    # Step 1: Analyze tests
    analyzer = MavenTestAnalyzer()
    has_failures = analyzer.run_analysis()

    if has_failures:
        suggester = FixSuggester()
        suggester.suggest_fixes()
    else:
        Logger.info("No failures to suggest fixes for")


if __name__ == "__main__":
    main()