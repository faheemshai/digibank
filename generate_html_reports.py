#!/usr/bin/env python3
"""
HTML Report Generator for Maven Test Analysis

Generates professional HTML reports from the JSON output of the fix_errors.py script.
Uses HTML5 Boilerplate, Tailwind CSS, and IBM Design System colors.
"""

import json
import os
from datetime import datetime
from typing import Dict, Any, List
import argparse


class HTMLReportGenerator:
    """Generates professional HTML reports from test analysis JSON data."""

    def __init__(self, output_dir: str = "output"):
        self.output_dir = output_dir
        self.ibm_colors = {
            'primary': '#0f62fe',
            'primary_hover': '#0353e9',
            'secondary': '#393939',
            'success': '#198038',
            'warning': '#f1c21b',
            'error': '#da1e28',
            'info': '#0043ce',
            'gray_10': '#f4f4f4',
            'gray_20': '#e0e0e0',
            'gray_30': '#c6c6c6',
            'gray_50': '#8d8d8d',
            'gray_70': '#525252',
            'gray_90': '#262626',
            'gray_100': '#161616'
        }

    def load_json_data(self) -> Dict[str, Any]:
        """Load both error summary and suggested fixes JSON files."""
        data = {}

        error_summary_path = os.path.join(self.output_dir, 'error-summary.json')
        fixes_path = os.path.join(self.output_dir, 'suggested-fixes.json')

        if os.path.exists(error_summary_path):
            with open(error_summary_path, 'r') as f:
                data['error_summary'] = json.load(f)

        if os.path.exists(fixes_path):
            with open(fixes_path, 'r') as f:
                data['suggested_fixes'] = json.load(f)

        return data

    def get_base_html_template(self, title: str, additional_styles: str = "") -> str:
        """Returns the base HTML5 template with Tailwind CSS and IBM colors."""
        return f'''<!DOCTYPE html>
<html lang="en" class="h-full">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <style>
        :root {{
            --ibm-blue: {self.ibm_colors['primary']};
            --ibm-blue-hover: {self.ibm_colors['primary_hover']};
            --ibm-gray-10: {self.ibm_colors['gray_10']};
            --ibm-gray-20: {self.ibm_colors['gray_20']};
            --ibm-gray-30: {self.ibm_colors['gray_30']};
            --ibm-gray-50: {self.ibm_colors['gray_50']};
            --ibm-gray-70: {self.ibm_colors['gray_70']};
            --ibm-gray-90: {self.ibm_colors['gray_90']};
            --ibm-gray-100: {self.ibm_colors['gray_100']};
            --ibm-success: {self.ibm_colors['success']};
            --ibm-warning: {self.ibm_colors['warning']};
            --ibm-error: {self.ibm_colors['error']};
        }}

        body {{
            font-family: 'IBM Plex Sans', sans-serif;
            background-color: var(--ibm-gray-10);
        }}

        .ibm-primary {{ background-color: var(--ibm-blue); }}
        .ibm-primary-hover:hover {{ background-color: var(--ibm-blue-hover); }}
        .ibm-success {{ background-color: var(--ibm-success); }}
        .ibm-warning {{ background-color: var(--ibm-warning); }}
        .ibm-error {{ background-color: var(--ibm-error); }}
        .ibm-gray-bg {{ background-color: var(--ibm-gray-20); }}

        .status-passed {{
            background-color: var(--ibm-success);
            color: white;
        }}
        .status-failed {{
            background-color: var(--ibm-error);
            color: white;
        }}
        .status-warning {{
            background-color: var(--ibm-warning);
            color: var(--ibm-gray-100);
        }}

        .code-block {{
            background-color: var(--ibm-gray-100);
            color: var(--ibm-gray-10);
            font-family: 'Courier New', monospace;
        }}

        .card-shadow {{
            box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.1), 0 1px 2px 0 rgba(0, 0, 0, 0.06);
        }}

        @media print {{
            .no-print {{ display: none; }}
            body {{ background-color: white; }}
        }}

        {additional_styles}
    </style>
    <script>
        function toggleSection(id) {{
            const element = document.getElementById(id);
            const icon = document.getElementById(id + '-icon');
            if (element.classList.contains('hidden')) {{
                element.classList.remove('hidden');
                icon.textContent = '▼';
            }} else {{
                element.classList.add('hidden');
                icon.textContent = '▶';
            }}
        }}

        function copyToClipboard(text) {{
            navigator.clipboard.writeText(text).then(() => {{
                alert('Code copied to clipboard!');
            }});
        }}
    </script>
</head>
<body class="h-full">'''

    def get_header_nav(self) -> str:
        """Returns the navigation header."""
        return '''
    <header class="ibm-primary text-white shadow-lg">
        <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div class="flex justify-between items-center py-6">
                <div class="flex items-center">
                    <h1 class="text-2xl font-bold">Maven Test Analysis</h1>
                </div>
                <nav class="hidden md:flex space-x-8">
                    <a href="test-analysis-dashboard.html" class="hover:text-gray-300 transition">Dashboard</a>
                    <a href="test-results-detailed.html" class="hover:text-gray-300 transition">Test Results</a>
                    <a href="fix-suggestions.html" class="hover:text-gray-300 transition">Fix Suggestions</a>
                </nav>
            </div>
        </div>
    </header>'''

    def generate_dashboard(self, data: Dict[str, Any]) -> str:
        """Generate the main dashboard HTML."""
        if 'error_summary' not in data:
            return self.generate_no_data_page("Dashboard")

        summary = data['error_summary']['summary']
        metadata = data['error_summary']['metadata']
        suites = data['error_summary']['suites']

        # Calculate metrics
        success_rate = summary['success_rate_percent']
        status_color = 'ibm-success' if success_rate == 100 else 'ibm-warning' if success_rate >= 80 else 'ibm-error'

        html = self.get_base_html_template("Maven Test Analysis - Dashboard")
        html += self.get_header_nav()

        html += f'''
    <main class="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
        <div class="px-4 py-6 sm:px-0">
            <!-- Page Header -->
            <div class="mb-8">
                <h1 class="text-3xl font-bold text-gray-900">Test Analysis Dashboard</h1>
                <p class="mt-2 text-sm text-gray-600">Generated on {metadata['generated_at']}</p>
            </div>

            <!-- KPI Cards -->
            <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
                <div class="bg-white overflow-hidden shadow rounded-lg card-shadow">
                    <div class="p-5">
                        <div class="flex items-center">
                            <div class="flex-shrink-0">
                                <div class="w-8 h-8 {status_color} rounded-full flex items-center justify-center">
                                    <span class="text-white font-bold">✓</span>
                                </div>
                            </div>
                            <div class="ml-5 w-0 flex-1">
                                <dl>
                                    <dt class="text-sm font-medium text-gray-500 truncate">Success Rate</dt>
                                    <dd class="text-lg font-medium text-gray-900">{success_rate:.1f}%</dd>
                                </dl>
                            </div>
                        </div>
                    </div>
                </div>

                <div class="bg-white overflow-hidden shadow rounded-lg card-shadow">
                    <div class="p-5">
                        <div class="flex items-center">
                            <div class="flex-shrink-0">
                                <div class="w-8 h-8 ibm-primary rounded-full flex items-center justify-center">
                                    <span class="text-white font-bold">#</span>
                                </div>
                            </div>
                            <div class="ml-5 w-0 flex-1">
                                <dl>
                                    <dt class="text-sm font-medium text-gray-500 truncate">Total Tests</dt>
                                    <dd class="text-lg font-medium text-gray-900">{summary['total_tests']}</dd>
                                </dl>
                            </div>
                        </div>
                    </div>
                </div>

                <div class="bg-white overflow-hidden shadow rounded-lg card-shadow">
                    <div class="p-5">
                        <div class="flex items-center">
                            <div class="flex-shrink-0">
                                <div class="w-8 h-8 ibm-error rounded-full flex items-center justify-center">
                                    <span class="text-white font-bold">✗</span>
                                </div>
                            </div>
                            <div class="ml-5 w-0 flex-1">
                                <dl>
                                    <dt class="text-sm font-medium text-gray-500 truncate">Failures</dt>
                                    <dd class="text-lg font-medium text-gray-900">{summary['total_failures']}</dd>
                                </dl>
                            </div>
                        </div>
                    </div>
                </div>

                <div class="bg-white overflow-hidden shadow rounded-lg card-shadow">
                    <div class="p-5">
                        <div class="flex items-center">
                            <div class="flex-shrink-0">
                                <div class="w-8 h-8 bg-gray-400 rounded-full flex items-center justify-center">
                                    <span class="text-white font-bold">⏱</span>
                                </div>
                            </div>
                            <div class="ml-5 w-0 flex-1">
                                <dl>
                                    <dt class="text-sm font-medium text-gray-500 truncate">Execution Time</dt>
                                    <dd class="text-lg font-medium text-gray-900">{summary['total_time_seconds']:.2f}s</dd>
                                </dl>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Test Suites Overview -->
            <div class="bg-white shadow rounded-lg card-shadow">
                <div class="px-4 py-5 sm:p-6">
                    <h3 class="text-lg leading-6 font-medium text-gray-900 mb-4">Test Suites Overview</h3>
                    <div class="overflow-x-auto">
                        <table class="min-w-full divide-y divide-gray-200">
                            <thead class="bg-gray-50">
                                <tr>
                                    <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Suite Name</th>
                                    <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Status</th>
                                    <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Tests</th>
                                    <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Time</th>
                                </tr>
                            </thead>
                            <tbody class="bg-white divide-y divide-gray-200">'''

        for suite in suites:
            suite_name = suite['name'].split('.')[-1]  # Get just the class name
            status_badge = 'status-passed' if suite['status'] == 'PASSED' else 'status-failed'

            html += f'''
                                <tr>
                                    <td class="px-6 py-4 whitespace-nowrap">
                                        <div class="text-sm font-medium text-gray-900">{suite_name}</div>
                                        <div class="text-sm text-gray-500">{suite['name']}</div>
                                    </td>
                                    <td class="px-6 py-4 whitespace-nowrap">
                                        <span class="inline-flex px-2 py-1 text-xs font-semibold rounded-full {status_badge}">
                                            {suite['status']}
                                        </span>
                                    </td>
                                    <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">{suite['tests']}</td>
                                    <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">{suite['time_seconds']:.2f}s</td>
                                </tr>'''

        html += '''
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        </div>
    </main>
</body>
</html>'''

        return html

    def generate_detailed_results(self, data: Dict[str, Any]) -> str:
        """Generate the detailed test results HTML."""
        if 'error_summary' not in data:
            return self.generate_no_data_page("Test Results")

        summary = data['error_summary']['summary']
        metadata = data['error_summary']['metadata']
        suites = data['error_summary']['suites']

        html = self.get_base_html_template("Maven Test Analysis - Detailed Results")
        html += self.get_header_nav()

        html += f'''
    <main class="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
        <div class="px-4 py-6 sm:px-0">
            <!-- Page Header -->
            <div class="mb-8">
                <h1 class="text-3xl font-bold text-gray-900">Detailed Test Results</h1>
                <p class="mt-2 text-sm text-gray-600">Generated on {metadata['generated_at']} | {summary['total_tests']} tests across {metadata['total_suites']} suites</p>
            </div>'''

        for i, suite in enumerate(suites):
            suite_name = suite['name'].split('.')[-1]
            status_badge = 'status-passed' if suite['status'] == 'PASSED' else 'status-failed'

            html += f'''
            <!-- Test Suite {i+1} -->
            <div class="bg-white shadow rounded-lg card-shadow mb-6">
                <div class="px-4 py-5 sm:p-6">
                    <div class="flex items-center justify-between mb-4">
                        <div>
                            <h3 class="text-lg leading-6 font-medium text-gray-900">{suite_name}</h3>
                            <p class="text-sm text-gray-500">{suite['name']}</p>
                        </div>
                        <span class="inline-flex px-3 py-1 text-sm font-semibold rounded-full {status_badge}">
                            {suite['status']}
                        </span>
                    </div>

                    <div class="grid grid-cols-1 md:grid-cols-4 gap-4 mb-4">
                        <div class="text-center">
                            <div class="text-2xl font-bold text-gray-900">{suite['tests']}</div>
                            <div class="text-sm text-gray-500">Tests</div>
                        </div>
                        <div class="text-center">
                            <div class="text-2xl font-bold text-green-600">{len([f for f in suite.get('failures', [])])}</div>
                            <div class="text-sm text-gray-500">Failures</div>
                        </div>
                        <div class="text-center">
                            <div class="text-2xl font-bold text-red-600">{suite['errors']}</div>
                            <div class="text-sm text-gray-500">Errors</div>
                        </div>
                        <div class="text-center">
                            <div class="text-2xl font-bold text-gray-600">{suite['time_seconds']:.2f}s</div>
                            <div class="text-sm text-gray-500">Duration</div>
                        </div>
                    </div>

                    <!-- Environment Info (Collapsible) -->
                    <div class="border-t pt-4">
                        <button onclick="toggleSection('env-{i}')" class="flex items-center text-sm font-medium text-gray-700 hover:text-gray-900">
                            <span id="env-{i}-icon" class="mr-2">▶</span>
                            Environment Information
                        </button>
                        <div id="env-{i}" class="hidden mt-3 bg-gray-50 rounded p-3">
                            <div class="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">'''

            for key, value in suite.get('environment', {}).items():
                html += f'''
                                <div>
                                    <span class="font-medium text-gray-700">{key}:</span>
                                    <span class="text-gray-900">{value}</span>
                                </div>'''

            html += f'''
                            </div>
                        </div>
                    </div>

                    <!-- Suite Log (Collapsible) -->
                    <div class="border-t pt-4 mt-4">
                        <button onclick="toggleSection('log-{i}')" class="flex items-center text-sm font-medium text-gray-700 hover:text-gray-900">
                            <span id="log-{i}-icon" class="mr-2">▶</span>
                            Suite Log
                        </button>
                        <div id="log-{i}" class="hidden mt-3">
                            <pre class="code-block p-4 rounded text-sm overflow-x-auto">{suite.get('suite_log_excerpt', 'No log available')}</pre>
                        </div>
                    </div>
                </div>
            </div>'''

        html += '''
        </div>
    </main>
</body>
</html>'''

        return html

    def generate_fix_suggestions(self, data: Dict[str, Any]) -> str:
        """Generate the fix suggestions HTML."""
        if 'suggested_fixes' not in data:
            return self.generate_no_data_page("Fix Suggestions")

        fixes_data = data['suggested_fixes']
        metadata = fixes_data['metadata']
        fixes = fixes_data.get('fixes', [])

        html = self.get_base_html_template("Maven Test Analysis - Fix Suggestions")
        html += self.get_header_nav()

        html += f'''
    <main class="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
        <div class="px-4 py-6 sm:px-0">
            <!-- Page Header -->
            <div class="mb-8">
                <h1 class="text-3xl font-bold text-gray-900">AI-Generated Fix Suggestions</h1>
                <p class="mt-2 text-sm text-gray-600">Generated on {metadata['generated_at']} | {len(fixes)} fix(es) suggested</p>
            </div>'''

        if not fixes:
            html += '''
            <div class="bg-green-50 border border-green-200 rounded-lg p-6 text-center">
                <div class="text-green-600 text-6xl mb-4">✓</div>
                <h2 class="text-xl font-semibold text-green-800 mb-2">All Tests Passing!</h2>
                <p class="text-green-700">No fixes needed. Your test suite is running successfully.</p>
            </div>'''
        else:
            for i, fix in enumerate(fixes):
                html += f'''
            <!-- Fix {i+1} -->
            <div class="bg-white shadow rounded-lg card-shadow mb-6">
                <div class="px-4 py-5 sm:p-6">
                    <div class="flex items-start justify-between mb-4">
                        <div>
                            <h3 class="text-lg leading-6 font-medium text-gray-900">Fix #{i+1}</h3>
                            <p class="text-sm text-gray-500">{fix['test_class']}.{fix['test_method']}</p>
                        </div>
                        <button onclick="copyToClipboard(`{fix['fixed_code']}`)"
                                class="ibm-primary ibm-primary-hover text-white px-3 py-1 text-sm rounded hover:bg-blue-700 transition">
                            Copy Fix
                        </button>
                    </div>

                    <!-- File and Line Info -->
                    <div class="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-4">
                        <div class="flex items-center">
                            <div class="text-blue-600 font-medium">📁 {fix['file_path']}</div>
                            <div class="ml-4 text-blue-600">Line {fix['line_number']}</div>
                        </div>
                    </div>

                    <!-- Root Cause -->
                    <div class="mb-6">
                        <h4 class="text-md font-semibold text-gray-900 mb-2">Root Cause Analysis</h4>
                        <div class="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
                            <p class="text-gray-800">{fix['root_cause']}</p>
                        </div>
                    </div>

                    <!-- Code Comparison -->
                    <div class="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
                        <div>
                            <h4 class="text-md font-semibold text-red-700 mb-2">❌ Current Code</h4>
                            <pre class="code-block p-4 rounded text-sm overflow-x-auto border-2 border-red-200">{fix['current_code']}</pre>
                        </div>
                        <div>
                            <h4 class="text-md font-semibold text-green-700 mb-2">✅ Fixed Code</h4>
                            <pre class="code-block p-4 rounded text-sm overflow-x-auto border-2 border-green-200">{fix['fixed_code']}</pre>
                        </div>
                    </div>

                    <!-- Verification -->
                    <div class="border-t pt-4">
                        <h4 class="text-md font-semibold text-gray-900 mb-2">Verification Steps</h4>
                        <div class="bg-gray-50 rounded-lg p-4">
                            <p class="text-gray-800">{fix['verification']}</p>
                        </div>
                    </div>
                </div>
            </div>'''

        html += '''
        </div>
    </main>
</body>
</html>'''

        return html

    def generate_no_data_page(self, page_type: str) -> str:
        """Generate a page when no data is available."""
        html = self.get_base_html_template(f"Maven Test Analysis - {page_type}")
        html += self.get_header_nav()

        html += f'''
    <main class="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
        <div class="px-4 py-6 sm:px-0">
            <div class="text-center">
                <div class="text-gray-400 text-6xl mb-4">📊</div>
                <h2 class="text-2xl font-semibold text-gray-900 mb-2">No Data Available</h2>
                <p class="text-gray-600">No {page_type.lower()} data found. Please run the test analysis first.</p>
            </div>
        </div>
    </main>
</body>
</html>'''

        return html

    def generate_all_reports(self):
        """Generate all HTML reports."""
        print("Loading JSON data...")
        data = self.load_json_data()

        reports = [
            ('test-analysis-dashboard.html', self.generate_dashboard(data)),
            ('test-results-detailed.html', self.generate_detailed_results(data)),
            ('fix-suggestions.html', self.generate_fix_suggestions(data))
        ]

        for filename, html_content in reports:
            output_path = os.path.join(self.output_dir, filename)
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
            print(f"Generated: {output_path}")

        print(f"\n✅ All reports generated successfully in {self.output_dir}/")
        print("📊 Dashboard: test-analysis-dashboard.html")
        print("📋 Test Results: test-results-detailed.html")
        print("🔧 Fix Suggestions: fix-suggestions.html")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='Generate HTML reports from Maven test analysis JSON data')
    parser.add_argument('--output-dir', default='output', help='Output directory containing JSON files')

    args = parser.parse_args()

    generator = HTMLReportGenerator(args.output_dir)
    generator.generate_all_reports()


if __name__ == '__main__':
    main()