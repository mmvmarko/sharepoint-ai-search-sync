#!/usr/bin/env python3
"""
Example: Complete Intelligent Vertical Workflow

This script demonstrates the full workflow from file analysis to vertical creation.
"""

import sys
import os
from pathlib import Path

# Add project root to path
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

from intelligent_vertical_creator import IntelligentVerticalCreator


def example_analyze_code_corpus():
    """Example: Analyze the existing code corpus structure."""
    print("="*80)
    print("EXAMPLE 1: Analyzing Code Corpus")
    print("="*80)
    
    creator = IntelligentVerticalCreator()
    
    # Analyze one of the project folders
    corpus_path = "./code_corpus_v2/ATL__ATLANTIS__atlpp-main"
    
    if not Path(corpus_path).exists():
        print(f"⚠️  Path not found: {corpus_path}")
        print("This example requires the code_corpus_v2 directory.")
        return
    
    print(f"\n🔍 Analyzing: {corpus_path}")
    
    try:
        report = creator.analyze_directory(corpus_path, recursive=True)
        creator.print_report(report)
        
        print("\n💡 Insights:")
        print("   - The tool identified different file categories")
        print("   - Each category has optimal chunking suggestions")
        print("   - Multiple vertical options are provided")
        
    except Exception as e:
        print(f"❌ Error: {e}")


def example_create_vertical_structure():
    """Example: Create vertical structure for a sample directory."""
    print("\n" + "="*80)
    print("EXAMPLE 2: Creating Vertical Structure")
    print("="*80)
    
    creator = IntelligentVerticalCreator()
    
    # For demo purposes, analyze the config directory (small)
    source_path = "./config"
    output_path = "./example_output/verticals"
    
    if not Path(source_path).exists():
        print(f"⚠️  Path not found: {source_path}")
        return
    
    print(f"\n🔍 Analyzing: {source_path}")
    print(f"📂 Output will be created in: {output_path}")
    
    try:
        # Analyze
        report = creator.analyze_directory(source_path, recursive=True)
        
        print(f"\n📊 Found {report.total_files} files")
        
        # Create structure
        print("\n🏗️  Creating vertical structure...")
        created = creator.create_vertical_structure(report, output_path)
        
        print("\n✅ Structure created!")
        print("\n📂 Created files:")
        
        for prefix, info in created.items():
            print(f"\n  Vertical: {prefix}")
            print(f"    Directory: {info['directory']}")
            print(f"    Config: {info['config']}")
            print(f"    Files: {info['file_count']}")
        
        print("\n💡 Next Steps:")
        print("   1. Review the generated vertical_config.json files")
        print("   2. Upload files to blob storage")
        print(f"   3. Create verticals: python main.py create_vertical --prefix [prefix]")
        
    except Exception as e:
        print(f"❌ Error: {e}")


def example_programmatic_usage():
    """Example: Using the tool programmatically."""
    print("\n" + "="*80)
    print("EXAMPLE 3: Programmatic Usage")
    print("="*80)
    
    creator = IntelligentVerticalCreator()
    
    source_path = "./src"
    
    if not Path(source_path).exists():
        print(f"⚠️  Path not found: {source_path}")
        return
    
    print(f"\n🔍 Analyzing: {source_path}")
    
    try:
        report = creator.analyze_directory(source_path, recursive=True)
        
        print(f"\n📊 Analysis Results:")
        print(f"   Total Files: {report.total_files}")
        print(f"   Total Size: {creator._format_size(report.total_size)}")
        print(f"   Categories: {len(report.category_stats)}")
        
        print("\n🎯 Vertical Suggestions:")
        for i, suggestion in enumerate(report.vertical_suggestions, 1):
            print(f"\n   {i}. {suggestion.name}")
            print(f"      Prefix: {suggestion.prefix}")
            print(f"      Files: {suggestion.file_count}")
            print(f"      Extensions: {', '.join(suggestion.file_extensions[:5])}")
            print(f"      Chunk Size: {suggestion.chunk_size}")
            print(f"      Overlap: {suggestion.overlap}")
        
        print("\n💡 You can now:")
        print("   - Access report.vertical_suggestions for automation")
        print("   - Create custom logic based on suggestion properties")
        print("   - Integrate with your deployment pipeline")
        
    except Exception as e:
        print(f"❌ Error: {e}")


def example_category_breakdown():
    """Example: Detailed category analysis."""
    print("\n" + "="*80)
    print("EXAMPLE 4: Category Breakdown")
    print("="*80)
    
    creator = IntelligentVerticalCreator()
    
    source_path = "./scripts"
    
    if not Path(source_path).exists():
        source_path = "./src"  # Fallback
    
    if not Path(source_path).exists():
        print(f"⚠️  Path not found: {source_path}")
        return
    
    print(f"\n🔍 Analyzing: {source_path}")
    
    try:
        report = creator.analyze_directory(source_path, recursive=True)
        
        print(f"\n📋 Category Statistics:")
        
        for category, stats in sorted(report.category_stats.items(), 
                                      key=lambda x: x[1]['count'], reverse=True):
            print(f"\n  {category.upper()}:")
            print(f"    File Count: {stats['count']}")
            print(f"    Total Size: {creator._format_size(stats['total_size'])}")
            print(f"    Average Size: {creator._format_size(stats['avg_size'])}")
            print(f"    Extensions: {', '.join(stats['extensions'])}")
            
            # Show optimal settings for this category
            from intelligent_vertical_creator import FILE_CATEGORIES
            if category in FILE_CATEGORIES:
                cat_info = FILE_CATEGORIES[category]
                print(f"    Optimal Chunk Size: {cat_info['optimal_chunk_size']} chars")
                print(f"    Overlap: {cat_info['overlap']} chars")
        
        print("\n💡 Understanding Categories:")
        print("   - Different file types need different chunking strategies")
        print("   - Code files benefit from larger chunks (preserve function context)")
        print("   - Structured files need minimal/no overlap (avoid breaking syntax)")
        print("   - Documents use standard chunking (paragraph boundaries)")
        
    except Exception as e:
        print(f"❌ Error: {e}")


def main():
    """Run all examples."""
    print("\n" + "="*80)
    print("🚀 INTELLIGENT VERTICAL CREATOR - EXAMPLES")
    print("="*80)
    print("\nThese examples demonstrate how to use the Intelligent Vertical Creator")
    print("to analyze files and create optimized search verticals.\n")
    
    examples = [
        ("Analyze Code Corpus", example_analyze_code_corpus),
        ("Create Vertical Structure", example_create_vertical_structure),
        ("Programmatic Usage", example_programmatic_usage),
        ("Category Breakdown", example_category_breakdown),
    ]
    
    print("Available examples:")
    for i, (name, _) in enumerate(examples, 1):
        print(f"  {i}. {name}")
    
    print("\n" + "-"*80)
    
    # Check if user specified an example
    if len(sys.argv) > 1:
        try:
            choice = int(sys.argv[1])
            if 1 <= choice <= len(examples):
                name, func = examples[choice - 1]
                print(f"\nRunning: {name}\n")
                func()
                return
            else:
                print(f"❌ Invalid choice: {choice}")
                return
        except ValueError:
            print(f"❌ Invalid argument: {sys.argv[1]}")
            return
    
    # Run all examples
    print("\nRunning all examples...\n")
    for name, func in examples:
        try:
            func()
        except Exception as e:
            print(f"\n❌ Example '{name}' failed: {e}")
        print("\n" + "-"*80)
    
    print("\n✅ Examples completed!")
    print("\nTo run a specific example:")
    print("  python example_intelligent_vertical_workflow.py [1-4]")
    print("\nFor full documentation:")
    print("  See INTELLIGENT_VERTICALS.md")


if __name__ == '__main__':
    main()
