#!/usr/bin/env python3
"""
Intelligent Vertical Creator

Analyzes source files and automatically suggests/creates optimal vertical configurations:
1. Analyzes file characteristics (types, sizes, content)
2. Suggests chunking strategies and index splitting
3. Creates organized folder structures
4. Generates vertical configurations
"""

import os
import sys
import json
import logging
import mimetypes
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional
from dataclasses import dataclass, asdict
from collections import defaultdict
import click

# Add project root to path
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

from config.settings import config

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# File type categories and characteristics
FILE_CATEGORIES = {
    'code': {
        'extensions': ['.py', '.js', '.ts', '.java', '.cpp', '.cs', '.go', '.rb', '.php', '.html', '.css', '.scss'],
        'optimal_chunk_size': 3000,
        'overlap': 200,
        'description': 'Source code files'
    },
    'documents': {
        'extensions': ['.pdf', '.docx', '.pptx', '.txt', '.md', '.rtf'],
        'optimal_chunk_size': 2000,
        'overlap': 100,
        'description': 'Office documents and text files'
    },
    'structured': {
        'extensions': ['.json', '.xml', '.yaml', '.yml', '.toml', '.ini', '.csv'],
        'optimal_chunk_size': 5000,
        'overlap': 0,
        'description': 'Structured data files'
    },
    'spreadsheets': {
        'extensions': ['.xlsx', '.xls', '.csv'],
        'optimal_chunk_size': 4000,
        'overlap': 50,
        'description': 'Spreadsheet files'
    },
    'media': {
        'extensions': ['.png', '.jpg', '.jpeg', '.gif', '.svg', '.mp4', '.mp3'],
        'optimal_chunk_size': 0,
        'overlap': 0,
        'description': 'Media files (images, video, audio)'
    }
}

@dataclass
class FileAnalysis:
    """Analysis result for a single file."""
    path: str
    size: int
    extension: str
    category: str
    mime_type: Optional[str]
    estimated_text_length: Optional[int] = None
    
@dataclass
class VerticalSuggestion:
    """Suggested vertical configuration."""
    name: str
    prefix: str
    category: str
    file_extensions: List[str]
    chunk_size: int
    overlap: int
    file_count: int
    total_size: int
    container_path: str
    description: str

@dataclass
class AnalysisReport:
    """Complete analysis report."""
    total_files: int
    total_size: int
    file_analyses: List[FileAnalysis]
    category_stats: Dict[str, Dict[str, Any]]
    vertical_suggestions: List[VerticalSuggestion]
    warnings: List[str]


class IntelligentVerticalCreator:
    """Analyzes files and creates optimized vertical configurations."""
    
    def __init__(self):
        self.config = config
        mimetypes.init()
    
    def analyze_directory(self, directory: str, recursive: bool = True) -> AnalysisReport:
        """
        Analyze all files in a directory.
        
        Args:
            directory: Path to directory to analyze
            recursive: Whether to recurse into subdirectories
            
        Returns:
            AnalysisReport with complete analysis
        """
        logger.info(f"Analyzing directory: {directory}")
        
        path = Path(directory)
        if not path.exists():
            raise ValueError(f"Directory does not exist: {directory}")
        
        files: List[FileAnalysis] = []
        warnings: List[str] = []
        
        # Collect all files
        if recursive:
            file_paths = list(path.rglob('*'))
        else:
            file_paths = list(path.glob('*'))
        
        # Filter to files only
        file_paths = [f for f in file_paths if f.is_file()]
        
        logger.info(f"Found {len(file_paths)} files to analyze")
        
        for file_path in file_paths:
            try:
                analysis = self._analyze_file(file_path)
                files.append(analysis)
            except Exception as e:
                warning = f"Could not analyze {file_path}: {e}"
                warnings.append(warning)
                logger.warning(warning)
        
        # Calculate category statistics
        category_stats = self._calculate_category_stats(files)
        
        # Generate vertical suggestions
        vertical_suggestions = self._generate_vertical_suggestions(files, directory)
        
        total_size = sum(f.size for f in files)
        
        return AnalysisReport(
            total_files=len(files),
            total_size=total_size,
            file_analyses=files,
            category_stats=category_stats,
            vertical_suggestions=vertical_suggestions,
            warnings=warnings
        )
    
    def _analyze_file(self, file_path: Path) -> FileAnalysis:
        """Analyze a single file."""
        stat = file_path.stat()
        extension = file_path.suffix.lower()
        
        # Determine category
        category = self._categorize_file(extension)
        
        # Get mime type
        mime_type, _ = mimetypes.guess_type(str(file_path))
        
        # Estimate text length for text-based files
        estimated_text_length = None
        if category in ['code', 'documents', 'structured']:
            try:
                # Try to read as text and estimate
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    estimated_text_length = len(content)
            except:
                # Binary file or read error
                pass
        
        return FileAnalysis(
            path=str(file_path),
            size=stat.st_size,
            extension=extension,
            category=category,
            mime_type=mime_type,
            estimated_text_length=estimated_text_length
        )
    
    def _categorize_file(self, extension: str) -> str:
        """Determine file category based on extension."""
        for category, info in FILE_CATEGORIES.items():
            if extension in info['extensions']:
                return category
        return 'unknown'
    
    def _calculate_category_stats(self, files: List[FileAnalysis]) -> Dict[str, Dict[str, Any]]:
        """Calculate statistics per category."""
        stats = defaultdict(lambda: {
            'count': 0,
            'total_size': 0,
            'extensions': set(),
            'avg_size': 0
        })
        
        for file in files:
            cat = file.category
            stats[cat]['count'] += 1
            stats[cat]['total_size'] += file.size
            stats[cat]['extensions'].add(file.extension)
        
        # Calculate averages and convert sets to lists
        for cat in stats:
            if stats[cat]['count'] > 0:
                stats[cat]['avg_size'] = stats[cat]['total_size'] / stats[cat]['count']
            stats[cat]['extensions'] = sorted(list(stats[cat]['extensions']))
        
        return dict(stats)
    
    def _generate_vertical_suggestions(self, files: List[FileAnalysis], base_dir: str) -> List[VerticalSuggestion]:
        """Generate optimal vertical configuration suggestions."""
        suggestions = []
        
        # Group files by category
        by_category = defaultdict(list)
        for file in files:
            by_category[file.category].append(file)
        
        # Create suggestions for each significant category
        for category, cat_files in by_category.items():
            if category == 'unknown':
                continue
            
            file_count = len(cat_files)
            if file_count == 0:
                continue
            
            # Get optimal settings for this category
            category_info = FILE_CATEGORIES.get(category, {})
            chunk_size = category_info.get('optimal_chunk_size', 2000)
            overlap = category_info.get('overlap', 100)
            
            # Calculate total size
            total_size = sum(f.size for f in cat_files)
            
            # Get unique extensions
            extensions = sorted(list(set(f.extension for f in cat_files)))
            
            # Generate prefix and name
            prefix = f"{category[:3]}"
            name = f"{category.title()} Vertical"
            
            # Determine container path
            container_path = f"verticals/{category}"
            
            # Create description
            description = (
                f"{category_info.get('description', category)} - "
                f"{file_count} files, {self._format_size(total_size)}"
            )
            
            suggestion = VerticalSuggestion(
                name=name,
                prefix=prefix,
                category=category,
                file_extensions=extensions,
                chunk_size=chunk_size,
                overlap=overlap,
                file_count=file_count,
                total_size=total_size,
                container_path=container_path,
                description=description
            )
            
            suggestions.append(suggestion)
        
        # Sort by file count (most files first)
        suggestions.sort(key=lambda s: s.file_count, reverse=True)
        
        # Add combined suggestion if multiple categories
        if len(suggestions) > 1:
            all_files = [f for f in files if f.category != 'unknown']
            all_extensions = sorted(list(set(f.extension for f in all_files)))
            
            combined = VerticalSuggestion(
                name="Combined Vertical",
                prefix="all",
                category="combined",
                file_extensions=all_extensions,
                chunk_size=2000,
                overlap=100,
                file_count=len(all_files),
                total_size=sum(f.size for f in all_files),
                container_path="verticals/combined",
                description=f"All content types - {len(all_files)} files"
            )
            suggestions.insert(0, combined)
        
        return suggestions
    
    def _format_size(self, size_bytes: int) -> str:
        """Format byte size in human-readable format."""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} TB"
    
    def print_report(self, report: AnalysisReport):
        """Print a formatted analysis report."""
        print("\n" + "="*80)
        print("📊 INTELLIGENT VERTICAL ANALYSIS REPORT")
        print("="*80)
        
        print(f"\n📁 Total Files: {report.total_files}")
        print(f"💾 Total Size: {self._format_size(report.total_size)}")
        
        # Category breakdown
        print("\n📋 Category Breakdown:")
        print("-" * 80)
        for category, stats in sorted(report.category_stats.items(), 
                                      key=lambda x: x[1]['count'], reverse=True):
            print(f"\n  {category.upper()}")
            print(f"    Files: {stats['count']}")
            print(f"    Total Size: {self._format_size(stats['total_size'])}")
            print(f"    Avg Size: {self._format_size(stats['avg_size'])}")
            print(f"    Extensions: {', '.join(stats['extensions'])}")
        
        # Vertical suggestions
        print("\n🎯 VERTICAL SUGGESTIONS:")
        print("="*80)
        
        for i, suggestion in enumerate(report.vertical_suggestions, 1):
            print(f"\n{i}. {suggestion.name}")
            print(f"   Prefix: {suggestion.prefix}")
            print(f"   Category: {suggestion.category}")
            print(f"   Files: {suggestion.file_count}")
            print(f"   Size: {self._format_size(suggestion.total_size)}")
            print(f"   Extensions: {', '.join(suggestion.file_extensions[:10])}")
            if len(suggestion.file_extensions) > 10:
                print(f"                + {len(suggestion.file_extensions) - 10} more")
            print(f"   Chunking: {suggestion.chunk_size} chars (overlap: {suggestion.overlap})")
            print(f"   Container: {suggestion.container_path}")
            print(f"   {suggestion.description}")
        
        # Warnings
        if report.warnings:
            print(f"\n⚠️  Warnings ({len(report.warnings)}):")
            for warning in report.warnings[:10]:
                print(f"   - {warning}")
            if len(report.warnings) > 10:
                print(f"   ... and {len(report.warnings) - 10} more")
        
        print("\n" + "="*80)
    
    def create_vertical_structure(self, report: AnalysisReport, 
                                  output_base: str,
                                  selected_suggestions: Optional[List[int]] = None) -> Dict[str, Any]:
        """
        Create folder structure and organize files for selected verticals.
        
        Args:
            report: Analysis report
            output_base: Base directory for organized files
            selected_suggestions: Indices of suggestions to implement (None = all)
            
        Returns:
            Dictionary with created structure info
        """
        output_path = Path(output_base)
        output_path.mkdir(parents=True, exist_ok=True)
        
        if selected_suggestions is None:
            suggestions_to_create = report.vertical_suggestions
        else:
            suggestions_to_create = [report.vertical_suggestions[i] for i in selected_suggestions]
        
        created = {}
        
        for suggestion in suggestions_to_create:
            logger.info(f"Creating vertical structure: {suggestion.name}")
            
            # Create vertical directory
            vertical_dir = output_path / suggestion.container_path
            vertical_dir.mkdir(parents=True, exist_ok=True)
            
            # Create config file
            config_file = vertical_dir / "vertical_config.json"
            config_data = {
                'name': suggestion.name,
                'prefix': suggestion.prefix,
                'category': suggestion.category,
                'chunk_size': suggestion.chunk_size,
                'overlap': suggestion.overlap,
                'file_extensions': suggestion.file_extensions,
                'indexed_extensions': ','.join(suggestion.file_extensions),
                'description': suggestion.description
            }
            
            with open(config_file, 'w') as f:
                json.dump(config_data, f, indent=2)
            
            # Copy/organize matching files
            matching_files = [
                f for f in report.file_analyses 
                if f.extension in suggestion.file_extensions
            ]
            
            # Create a file list
            file_list_path = vertical_dir / "file_list.txt"
            with open(file_list_path, 'w') as f:
                for file_info in matching_files:
                    f.write(f"{file_info.path}\n")
            
            created[suggestion.prefix] = {
                'directory': str(vertical_dir),
                'config': str(config_file),
                'file_list': str(file_list_path),
                'file_count': len(matching_files),
                'suggestion': asdict(suggestion)
            }
            
            logger.info(f"  Created: {vertical_dir}")
            logger.info(f"  Files: {len(matching_files)}")
        
        # Create master index
        master_index = output_path / "vertical_index.json"
        with open(master_index, 'w') as f:
            json.dump({
                'created_at': str(Path.cwd()),
                'verticals': created,
                'analysis_summary': {
                    'total_files': report.total_files,
                    'total_size': report.total_size,
                    'categories': list(report.category_stats.keys())
                }
            }, f, indent=2)
        
        logger.info(f"Created vertical index: {master_index}")
        
        return created


# CLI Commands
@click.group()
def cli():
    """Intelligent Vertical Creator - Analyze and create optimized search verticals."""
    pass


@cli.command('analyze')
@click.argument('directory', type=click.Path(exists=True))
@click.option('--recursive/--no-recursive', default=True, help='Recurse into subdirectories')
@click.option('--output', '-o', type=click.Path(), help='Save report to JSON file')
def analyze_command(directory: str, recursive: bool, output: Optional[str]):
    """Analyze a directory and suggest optimal vertical configurations."""
    creator = IntelligentVerticalCreator()
    
    try:
        report = creator.analyze_directory(directory, recursive=recursive)
        creator.print_report(report)
        
        if output:
            output_path = Path(output)
            report_data = {
                'total_files': report.total_files,
                'total_size': report.total_size,
                'category_stats': report.category_stats,
                'vertical_suggestions': [asdict(s) for s in report.vertical_suggestions],
                'warnings': report.warnings
            }
            with open(output_path, 'w') as f:
                json.dump(report_data, f, indent=2)
            print(f"\n✅ Report saved to: {output_path}")
    
    except Exception as e:
        logger.error(f"Analysis failed: {e}")
        sys.exit(1)


@cli.command('create-structure')
@click.argument('directory', type=click.Path(exists=True))
@click.argument('output_base', type=click.Path())
@click.option('--select', '-s', multiple=True, type=int, 
              help='Select specific vertical suggestions by number (can specify multiple)')
@click.option('--recursive/--no-recursive', default=True, help='Recurse into subdirectories')
def create_structure_command(directory: str, output_base: str, select: Tuple[int], recursive: bool):
    """Analyze directory and create vertical folder structure."""
    creator = IntelligentVerticalCreator()
    
    try:
        # Analyze first
        print("🔍 Analyzing directory...")
        report = creator.analyze_directory(directory, recursive=recursive)
        creator.print_report(report)
        
        # Adjust indices (user provides 1-based, we need 0-based)
        selected_indices = [i - 1 for i in select] if select else None
        
        # Create structure
        print(f"\n🏗️  Creating vertical structure in: {output_base}")
        created = creator.create_vertical_structure(
            report, 
            output_base,
            selected_suggestions=selected_indices
        )
        
        print("\n✅ Vertical structure created!")
        print("\n📂 Created Verticals:")
        for prefix, info in created.items():
            print(f"  • {prefix}: {info['directory']} ({info['file_count']} files)")
        
        print(f"\n📋 Next steps:")
        print(f"1. Review the vertical configs in: {output_base}")
        print(f"2. Copy/move files to blob storage containers")
        print(f"3. Create verticals using:")
        for prefix in created.keys():
            print(f"   python main.py create_vertical --prefix {prefix}")
    
    except Exception as e:
        logger.error(f"Failed to create structure: {e}")
        sys.exit(1)


@cli.command('interactive')
@click.argument('directory', type=click.Path(exists=True))
@click.argument('output_base', type=click.Path())
def interactive_command(directory: str, output_base: str):
    """Interactive mode: analyze, review, and create verticals."""
    creator = IntelligentVerticalCreator()
    
    try:
        # Analyze
        print("🔍 Analyzing directory...")
        report = creator.analyze_directory(directory, recursive=True)
        creator.print_report(report)
        
        # Ask for confirmation
        print("\n" + "="*80)
        response = input("\n❓ Create vertical structures based on these suggestions? [y/N]: ")
        
        if response.lower() not in ['y', 'yes']:
            print("❌ Cancelled.")
            return
        
        # Ask which ones
        print("\n📝 Select verticals to create:")
        print("   Enter numbers separated by spaces (e.g., '1 2 3')")
        print("   Or press Enter to create all")
        selection = input("\n   Selection: ").strip()
        
        selected_indices = None
        if selection:
            try:
                selected_indices = [int(x) - 1 for x in selection.split()]
            except ValueError:
                print("❌ Invalid selection. Exiting.")
                return
        
        # Create
        print(f"\n🏗️  Creating vertical structure...")
        created = creator.create_vertical_structure(
            report,
            output_base,
            selected_suggestions=selected_indices
        )
        
        print("\n✅ Done!")
        print(f"\n📂 Created {len(created)} vertical(s) in: {output_base}")
        
    except KeyboardInterrupt:
        print("\n❌ Cancelled by user.")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Interactive mode failed: {e}")
        sys.exit(1)


if __name__ == '__main__':
    cli()
