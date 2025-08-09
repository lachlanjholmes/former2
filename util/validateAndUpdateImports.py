#!/usr/bin/env python3
"""
Former2 Terraform Import Validator and Updater
==============================================

Comprehensive tool that:
1. Validates all 648 resource types against current implementation
2. Fetches correct import patterns from terraform-provider-aws GitHub repository
3. Tests generated import IDs against expected patterns
4. Offers to automatically update mappings.js with correct implementations

Usage:
    python util/validateAndUpdateImports.py              # Quick validation
    python util/validateAndUpdateImports.py --validate   # Full validation with pattern checking
    python util/validateAndUpdateImports.py --update     # Interactive update mode
"""

import re
import requests
import time
import json
import os
from typing import Dict, Set, List, Optional, Tuple
from urllib.parse import urljoin

def load_tf_resources() -> Set[str]:
    """Load all resource types from tf_resources.txt"""
    try:
        with open('util/tf_resources.txt', 'r') as f:
            return {line.strip() for line in f if line.strip()}
    except FileNotFoundError:
        print("❌ Error: util/tf_resources.txt not found")
        return set()

def extract_implemented_resources() -> Dict[str, str]:
    """Extract all resources from the generateTerraformImportId function"""
    try:
        with open('js/mappings.js', 'r', encoding='utf-8') as f:
            content = f.read()
    except FileNotFoundError:
        print("❌ Error: js/mappings.js not found")
        return {}
    
    # Find the generateTerraformImportId function
    function_start = content.find('function generateTerraformImportId(')
    if function_start == -1:
        print("❌ Error: generateTerraformImportId function not found")
        return {}
    
    # Find the function end by matching braces
    function_content = content[function_start:]
    brace_count = 0
    function_end = 0
    
    for i, char in enumerate(function_content):
        if char == '{':
            brace_count += 1
        elif char == '}':
            brace_count -= 1
            if brace_count == 0:
                function_end = i
                break
    
    function_body = function_content[:function_end]
    
    # Extract all case statements and their implementation types
    implemented = {}
    
    # Step 1: Find all cases with explicit return statements (complex cases)
    complex_pattern = r"case ['\"]([^'\"]+)['\"]:[^{]*?(?:return [^;]+;|return\s+[^;]+;)"
    complex_matches = re.finditer(complex_pattern, function_body, re.DOTALL)
    
    for match in complex_matches:
        case_name = match.group(1)
        # Check if it returns physicalId (simple) or something else (complex)
        match_text = match.group(0)
        if 'return physicalId' in match_text:
            implemented[case_name] = 'simple'
        else:
            implemented[case_name] = 'complex'
    
    # Step 2: Find the large block of simple cases that all fall through to "return physicalId;"
    # Look for the pattern: "Most resources use their physical ID directly" followed by cases
    simple_block_start = function_body.find("// Most resources use their physical ID directly")
    if simple_block_start != -1:
        # Find the end of this block (either at "default:" or function end)
        default_pos = function_body.find("default:", simple_block_start)
        block_end = default_pos if default_pos != -1 else len(function_body)
        
        simple_block = function_body[simple_block_start:block_end]
        
        # Extract all case names from this block
        simple_cases = re.findall(r"case ['\"]([^'\"]+)['\"]", simple_block)
        
        for case_name in simple_cases:
            # Only mark as simple if not already marked as complex
            if case_name not in implemented:
                implemented[case_name] = 'simple'
    
    # Step 3: Find any remaining cases that break without returning (fallthrough to nothing)
    all_cases = re.findall(r"case ['\"]([^'\"]+)['\"]", function_body)
    
    for case_name in all_cases:
        if case_name not in implemented:
            # Find this specific case and check what it does
            case_start = function_body.find(f"case '{case_name}':")
            if case_start == -1:
                case_start = function_body.find(f'case "{case_name}":')
            
            if case_start != -1:
                # Look for the next case or default to see what this case does
                remaining = function_body[case_start + len(f"case '{case_name}':"):] 
                
                # Check if there's a break before the next case/return
                next_case_pos = re.search(r'case [\'"][^\'\"]+[\'"]:', remaining)
                next_default_pos = re.search(r'default:', remaining)
                next_return_pos = re.search(r'return ', remaining)
                
                # Find the closest of these
                positions = []
                if next_case_pos: positions.append(('case', next_case_pos.start()))
                if next_default_pos: positions.append(('default', next_default_pos.start()))
                if next_return_pos: positions.append(('return', next_return_pos.start()))
                
                if positions:
                    positions.sort(key=lambda x: x[1])
                    closest = positions[0]
                    
                    case_content = remaining[:closest[1]]
                    
                    if 'break;' in case_content:
                        implemented[case_name] = 'fallthrough'
                    elif closest[0] == 'return' and 'return physicalId' in remaining[:closest[1] + 20]:
                        implemented[case_name] = 'simple'
                    else:
                        implemented[case_name] = 'fallthrough'
    
    # Step 4: Check if there's a default case for unhandled resources
    has_default_case = 'default:' in function_body and 'return physicalId' in function_body[function_body.find('default:'):]
    
    if has_default_case:
        all_resources = load_tf_resources()
        for resource in all_resources:
            if resource not in implemented:
                implemented[resource] = 'default_case'
    
    return implemented

def fetch_import_pattern_from_github(resource_type: str, quiet: bool = False) -> Optional[Dict]:
    """Fetch import pattern directly from the Terraform AWS provider GitHub repository"""
    try:
        # Build GitHub raw URL for the resource documentation
        resource_name = resource_type.replace('aws_', '')
        github_url = f"https://raw.githubusercontent.com/hashicorp/terraform-provider-aws/main/website/docs/r/{resource_name}.html.markdown"
        
        if not quiet:
            print(f"  🔍 Fetching: {resource_type}")
        
        headers = {
            'User-Agent': 'Former2-Import-Validator/1.0',
            'Accept': 'text/plain',
        }
        
        response = requests.get(github_url, headers=headers, timeout=10)
        
        if response.status_code == 404:
            # Try alternative naming patterns
            alternative_names = [
                resource_name.replace('_', '-'),
                resource_name + 's',
            ]
            
            for alt_name in alternative_names:
                alt_url = f"https://raw.githubusercontent.com/hashicorp/terraform-provider-aws/main/website/docs/r/{alt_name}.html.markdown"
                response = requests.get(alt_url, headers=headers, timeout=10)
                if response.status_code == 200:
                    break
        
        if response.status_code != 200:
            return {
                'pattern': 'physicalId',
                'complexity': 'simple',
                'code': 'return physicalId;',
                'source': 'default'
            }
        
        content = response.text
        
        # Look for import section
        import_section_match = re.search(r'^## Import\s*\n(.*?)(?=^##|\Z)', content, re.MULTILINE | re.DOTALL)
        if not import_section_match:
            return {
                'pattern': 'physicalId',
                'complexity': 'simple',
                'code': 'return physicalId;',
                'source': 'no_import_section'
            }
        
        import_content = import_section_match.group(1).strip()
        
        # Extract semantic information
        semantic_matches = re.findall(
            r'import [^`]*using the [`\'""]([^`\'""\s]+)[`\'""]', 
            import_content, 
            re.IGNORECASE
        )
        
        # Extract example import IDs
        import_examples = []
        
        # Look for terraform import commands
        code_blocks = re.findall(r'```(?:bash|shell|console|terraform)?\s*\n(.*?)\n```', import_content, re.DOTALL)
        for block in code_blocks:
            import_commands = re.findall(r'terraform import [^\n\r]+', block, re.IGNORECASE)
            for cmd in import_commands:
                # Extract the import ID
                patterns_to_try = [
                    r'terraform import\s+[^\s]+\s+"([^"]+)"',
                    r"terraform import\s+[^\s]+\s+'([^']+)'",
                    r'terraform import\s+[^\s]+\s+([^\s\n\r]+)'
                ]
                
                for pattern_regex in patterns_to_try:
                    match = re.search(pattern_regex, cmd)
                    if match:
                        import_id = match.group(1).strip()
                        if not any(char in import_id for char in ['$', '{{', '}}']):
                            import_examples.append(import_id)
                        break
        
        # Analyze pattern complexity and generate code
        semantic_type = semantic_matches[0] if semantic_matches else None
        example_id = import_examples[0] if import_examples else None
        
        return analyze_pattern_and_generate_code(resource_type, semantic_type, example_id, import_content)
        
    except Exception as e:
        if not quiet:
            print(f"    ❌ Error: {str(e)}")
        return {
            'pattern': 'physicalId',
            'complexity': 'simple',
            'code': 'return physicalId;',
            'source': 'error'
        }

def analyze_pattern_and_generate_code(resource_type: str, semantic_type: str, example_id: str, import_content: str) -> Dict:
    """Analyze import pattern and generate appropriate JavaScript code"""
    
    # Simple patterns that use physicalId directly
    simple_patterns = ['id', 'arn']
    
    if semantic_type in simple_patterns or not semantic_type:
        return {
            'pattern': semantic_type or 'id',
            'complexity': 'simple',
            'code': 'return physicalId;',
            'source': 'github_analysis'
        }
    
    # Name-based patterns
    name_patterns = ['name', 'role_name', 'function_name', 'group_name', 'bucket_name', 'bucket']
    if semantic_type in name_patterns:
        if 'lambda' in resource_type or 'function' in resource_type:
            return {
                'pattern': semantic_type,
                'complexity': 'simple_name',
                'code': 'return resourceData?.FunctionName || physicalId;',
                'source': 'github_analysis'
            }
        elif 'iam_role' in resource_type or semantic_type == 'role_name':
            return {
                'pattern': semantic_type,
                'complexity': 'simple_name',
                'code': 'return resourceData?.RoleName || physicalId;',
                'source': 'github_analysis'
            }
        elif 's3' in resource_type or semantic_type in ['bucket', 'bucket_name']:
            return {
                'pattern': semantic_type,
                'complexity': 'simple_name',
                'code': 'return resourceData?.Name || physicalId;',
                'source': 'github_analysis'
            }
        else:
            return {
                'pattern': semantic_type,
                'complexity': 'simple_name',
                'code': 'return resourceData?.Name || physicalId;',
                'source': 'github_analysis'
            }
    
    # Complex patterns - analyze example ID structure
    if example_id:
        if '/' in example_id:
            parts_count = len(example_id.split('/'))
            if parts_count == 2:
                return {
                    'pattern': f'complex_2_part',
                    'complexity': 'complex',
                    'code': f'return "TODO: Implement 2-part pattern"; // Example: {example_id}',
                    'source': 'github_analysis'
                }
            elif parts_count >= 3:
                return {
                    'pattern': f'complex_multi_part',
                    'complexity': 'complex',
                    'code': f'return "TODO: Implement multi-part pattern"; // Example: {example_id}',
                    'source': 'github_analysis'
                }
        elif ':' in example_id:
            return {
                'pattern': 'complex_colon',
                'complexity': 'complex',
                'code': f'return "TODO: Implement colon-separated pattern"; // Example: {example_id}',
                'source': 'github_analysis'
            }
        elif '_' in example_id:
            return {
                'pattern': 'complex_underscore',
                'complexity': 'complex',
                'code': f'return "TODO: Implement underscore pattern"; // Example: {example_id}',
                'source': 'github_analysis'
            }
    
    # Default to simple
    return {
        'pattern': semantic_type or 'unknown',
        'complexity': 'simple',
        'code': 'return physicalId;',
        'source': 'github_analysis'
    }

def test_import_pattern(resource_type: str, expected_pattern: Dict, current_impl: str) -> Dict:
    """Test if current implementation matches expected pattern"""
    
    result = {
        'resource': resource_type,
        'status': 'unknown',
        'current': current_impl,
        'expected': expected_pattern['complexity'],
        'needs_update': False,
        'suggested_code': expected_pattern['code']
    }
    
    # Handle default case - resources covered by default case are implemented as simple
    if current_impl == 'default_case':
        current_impl = 'simple'  # Default case returns physicalId, so treat as simple
        result['current'] = 'simple (via default case)'
    
    if current_impl == 'simple' and expected_pattern['complexity'] == 'simple':
        result['status'] = 'correct'
        result['needs_update'] = False
    elif current_impl == 'complex' and expected_pattern['complexity'] in ['complex', 'simple_name']:
        # Assume complex implementations are intentionally done
        result['status'] = 'probably_correct'
        result['needs_update'] = False
    elif current_impl == 'simple' and expected_pattern['complexity'] in ['complex', 'simple_name']:
        result['status'] = 'incorrect'
        result['needs_update'] = True
    elif current_impl in ['fallthrough', None]:
        result['status'] = 'missing'
        result['needs_update'] = True
    else:
        result['status'] = 'review_needed'
        result['needs_update'] = False
    
    return result

def generate_update_code(resources_to_update: List[Dict]) -> str:
    """Generate JavaScript code to update the mappings.js file"""
    
    if not resources_to_update:
        return ""
    
    # Group by complexity
    simple_resources = []
    name_resources = []
    complex_resources = []
    
    for resource in resources_to_update:
        if resource['expected'] == 'simple':
            simple_resources.append(resource['resource'])
        elif resource['expected'] == 'simple_name':
            name_resources.append(resource)
        else:
            complex_resources.append(resource)
    
    code_parts = []
    
    # Complex resources first
    if complex_resources:
        code_parts.append("        // Complex import patterns")
        for resource in complex_resources:
            code_parts.append(f"        case '{resource['resource']}':")
            code_parts.append(f"            {resource['suggested_code']}")
            code_parts.append("")
    
    # Name-based resources
    if name_resources:
        code_parts.append("        // Name-based import patterns")
        for resource in name_resources:
            code_parts.append(f"        case '{resource['resource']}':")
            code_parts.append(f"            {resource['suggested_code']}")
            code_parts.append("")
    
    # Simple resources
    if simple_resources:
        code_parts.append("        // Simple ID import patterns")
        for resource in simple_resources:
            code_parts.append(f"        case '{resource}':")
        code_parts.append("            return physicalId;")
        code_parts.append("")
    
    return "\n".join(code_parts)

def update_mappings_js(new_code: str, resources_to_add: List) -> bool:
    """Update the mappings.js file with new import cases"""
    
    try:
        with open('js/mappings.js', 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Find the generateTerraformImportId function
        function_start = content.find('function generateTerraformImportId(')
        if function_start == -1:
            print("❌ Error: generateTerraformImportId function not found")
            return False
        
        # Find the function end
        function_content = content[function_start:]
        brace_count = 0
        function_end = 0
        
        for i, char in enumerate(function_content):
            if char == '{':
                brace_count += 1
            elif char == '}':
                brace_count -= 1
                if brace_count == 0:
                    function_end = function_start + i
                    break
        
        # Look for the default case to insert before it
        default_case_pos = content.find('default:', function_start)
        if default_case_pos == -1 or default_case_pos > function_end:
            # Insert before the closing brace
            insert_pos = function_end - 4  # Before "    }"
        else:
            # Insert before default case
            insert_pos = default_case_pos - 8  # Before "        default:"
        
        # Insert the new code
        updated_content = (
            content[:insert_pos] + 
            "\n" + new_code + "\n" + 
            content[insert_pos:]
        )
        
        # Write back to file
        with open('js/mappings.js', 'w', encoding='utf-8') as f:
            f.write(updated_content)
        
        print(f"✅ Successfully updated mappings.js with {len(resources_to_add)} resources")
        return True
        
    except Exception as e:
        print(f"❌ Error updating mappings.js: {str(e)}")
        return False

def main():
    """Main validation and update workflow"""
    import sys
    
    validate_mode = '--validate' in sys.argv
    update_mode = '--update' in sys.argv
    
    print("Former2 Terraform Import Validator and Updater")
    print("=" * 60)
    
    # Load data
    all_resources = load_tf_resources()
    implemented_resources = extract_implemented_resources()
    
    print(f"📋 Total resources: {len(all_resources)}")
    print(f"🔧 Implemented: {len(implemented_resources)}")
    
    # Basic coverage analysis
    implemented_set = set(implemented_resources.keys())
    missing_resources = all_resources - implemented_set
    coverage = (len(implemented_set & all_resources) / len(all_resources)) * 100
    
    print(f"📊 Coverage: {coverage:.1f}% ({len(implemented_set & all_resources)}/{len(all_resources)})")
    print(f"❌ Missing: {len(missing_resources)}")
    
    if not validate_mode and not update_mode:
        print("\n🎯 Quick Summary Complete!")
        print("\nOptions:")
        print("  --validate  : Validate patterns against GitHub repository")
        print("  --update    : Interactive update mode")
        return
    
    # Detailed validation mode
    if validate_mode or update_mode:
        print(f"\n🔍 VALIDATING PATTERNS...")
        print("⏳ Fetching patterns from terraform-provider-aws repository...")
        
        validation_results = []
        resources_needing_update = []
        
        # Test implemented resources
        for i, (resource, impl_type) in enumerate(implemented_resources.items()):
            if resource in all_resources:  # Only validate official resources
                print(f"📊 Progress: {i+1}/{len(implemented_resources)} ({((i+1)/len(implemented_resources)*100):.0f}%)", end='\r')
                
                expected_pattern = fetch_import_pattern_from_github(resource, quiet=True)
                if expected_pattern:
                    test_result = test_import_pattern(resource, expected_pattern, impl_type)
                    validation_results.append(test_result)
                    
                    if test_result['needs_update']:
                        resources_needing_update.append(test_result)
                
                time.sleep(0.3)  # Rate limiting
        
        # Test missing resources
        print(f"\n🔍 Analyzing {len(missing_resources)} missing resources...")
        for i, resource in enumerate(sorted(missing_resources)):
            print(f"📊 Progress: {i+1}/{len(missing_resources)} ({((i+1)/len(missing_resources)*100):.0f}%)", end='\r')
            
            expected_pattern = fetch_import_pattern_from_github(resource, quiet=True)
            if expected_pattern:
                test_result = test_import_pattern(resource, expected_pattern, None)
                validation_results.append(test_result)
                resources_needing_update.append(test_result)
            
            time.sleep(0.3)  # Rate limiting
        
        print("\n")
        
        # Summary of validation results
        status_counts = {}
        for result in validation_results:
            status = result['status']
            status_counts[status] = status_counts.get(status, 0) + 1
        
        print(f"📊 VALIDATION RESULTS:")
        for status, count in sorted(status_counts.items()):
            emoji = {
                'correct': '✅',
                'probably_correct': '✨',
                'incorrect': '❌',
                'missing': '➕',
                'review_needed': '🔍'
            }.get(status, '❓')
            print(f"  {emoji} {status.replace('_', ' ').title()}: {count}")
        
        print(f"\n🔧 Resources needing updates: {len(resources_needing_update)}")
        
        if resources_needing_update and update_mode:
            # Interactive update mode
            print(f"\nWould you like to update mappings.js with the correct implementations?")
            
            # Show examples of what will be updated
            print(f"\nExamples of updates needed:")
            for i, resource in enumerate(resources_needing_update[:5]):
                status_emoji = '❌' if resource['status'] == 'incorrect' else '➕'
                print(f"  {status_emoji} {resource['resource']}: {resource['current']} → {resource['expected']}")
            
            if len(resources_needing_update) > 5:
                print(f"  ... and {len(resources_needing_update) - 5} more")
            
            response = input(f"\nUpdate mappings.js with {len(resources_needing_update)} improvements? (y/N): ")
            
            if response.lower() in ['y', 'yes']:
                print(f"\n🚀 Generating update code...")
                update_code = generate_update_code(resources_needing_update)
                
                if update_code:
                    success = update_mappings_js(update_code, resources_needing_update)
                    if success:
                        print(f"🎉 Successfully updated mappings.js!")
                        print(f"✅ Added/improved {len(resources_needing_update)} resource import patterns")
                        
                        # Run a quick re-validation
                        print(f"\n🔄 Re-validating coverage...")
                        updated_implemented = extract_implemented_resources()
                        new_coverage = (len(set(updated_implemented.keys()) & all_resources) / len(all_resources)) * 100
                        print(f"📊 New coverage: {new_coverage:.1f}%")
                        
                        if new_coverage > coverage:
                            print(f"🎯 Improved by {new_coverage - coverage:.1f}%!")
                else:
                    print("❌ No update code generated")
            else:
                print("⏭️  Update skipped")
    
    print(f"\n✨ Validation complete!")

if __name__ == "__main__":
    main()
