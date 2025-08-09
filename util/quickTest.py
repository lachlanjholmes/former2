#!/usr/bin/env python3
"""
Quick Test Tool for Former2 Terraform Imports

Test specific resources or patterns quickly without running the full validation.

Usage (run from the root former2 directory):
    python util/quickTest.py aws_lambda_function
    python util/quickTest.py aws_s3_bucket aws_iam_role
    python util/quickTest.py --pattern "aws_api_gateway_*"
"""

import sys
import re
import os

# Add the util directory to the path so we can import the other module
util_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(util_dir)

from validateAndUpdateImports import (
    extract_implemented_resources,
    fetch_import_pattern_from_github,
    test_import_pattern,
    load_tf_resources
)

def test_resources(resource_patterns):
    """Test specific resources or patterns"""
    
    # Load all implemented resources
    implemented = extract_implemented_resources()
    
    if not implemented:
        print("❌ Could not load implemented resources. Make sure you're running from the former2 root directory.")
        return
    
    resources_to_test = []
    
    for pattern in resource_patterns:
        if '*' in pattern:
            # Handle wildcard patterns
            pattern_regex = pattern.replace('*', '.*')
            matching = [res for res in implemented.keys() if re.match(pattern_regex, res)]
            resources_to_test.extend(matching)
        else:
            # Direct resource name
            if pattern in implemented:
                resources_to_test.append(pattern)
            else:
                print(f"❌ Resource not found in implementation: {pattern}")
                # Show some similar resources as suggestions
                similar = [res for res in implemented.keys() if pattern.lower() in res.lower()][:5]
                if similar:
                    print(f"   💡 Similar resources: {', '.join(similar)}")
    
    if not resources_to_test:
        print("❌ No resources to test")
        return
    
    resources_to_test = list(set(resources_to_test))  # Remove duplicates
    
    print(f"🧪 Testing {len(resources_to_test)} resources")
    print("=" * 50)
    
    for resource in sorted(resources_to_test):
        current_impl = implemented.get(resource, 'missing')
        
        print(f"\n🔍 {resource}")
        print(f"   Current: {current_impl}")
        
        # Fetch expected pattern
        expected_pattern = fetch_import_pattern_from_github(resource, quiet=False)
        if expected_pattern:
            test_result = test_import_pattern(resource, expected_pattern, current_impl)
            
            status_emoji = {
                'correct': '✅',
                'probably_correct': '✨',
                'incorrect': '❌',
                'missing': '➕',
                'review_needed': '🔍'
            }.get(test_result['status'], '❓')
            
            print(f"   Expected: {expected_pattern['complexity']}")
            print(f"   Status: {status_emoji} {test_result['status']}")
            
            if test_result['needs_update']:
                print(f"   Suggested: {test_result['suggested_code']}")
        else:
            print(f"   ❌ Could not fetch pattern from GitHub")

def main():
    try:
        if len(sys.argv) < 2:
            print("Usage: python util/quickTest.py <resource_type> [resource_type2] ...")
            print("Examples:")
            print("  python util/quickTest.py aws_lambda_function")
            print("  python util/quickTest.py aws_s3_bucket aws_iam_role")
            print('  python util/quickTest.py --pattern "aws_api_gateway_*"')
            print("\n💡 Make sure you're running from the former2 root directory!")
            return
        
        resource_patterns = []
        pattern_mode = False
        
        for arg in sys.argv[1:]:
            if arg == '--pattern':
                pattern_mode = True
            elif pattern_mode:
                resource_patterns.append(arg)
                pattern_mode = False
            else:
                resource_patterns.append(arg)
        
        test_resources(resource_patterns)
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
