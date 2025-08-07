#!/usr/bin/env python3
"""
OpenChronicle Modular Storypack Import CLI

Command-line interface for the new modular storypack import system.
Replaces the monolithic storypack_importer.py functionality.
"""

import asyncio
import argparse
import sys
from pathlib import Path
from typing import Optional

from utilities.storypack_import import StorypackOrchestrator
from utilities.storypack_import.parsers import ContentParser, MetadataExtractor, StructureAnalyzer
from utilities.storypack_import.processors import AIProcessor, ContentClassifier, ValidationEngine
from utilities.storypack_import.generators import StorypackBuilder, TemplateEngine, OutputFormatter
from utilities.logging_system import get_logger, log_system_event


class ModularStorypackImportCLI:
    """Command-line interface for the modular storypack import system."""
    
    def __init__(self):
        """Initialize the CLI."""
        self.logger = get_logger()
        self.orchestrator: Optional[StorypackOrchestrator] = None
    
    def create_parser(self) -> argparse.ArgumentParser:
        """Create and configure the argument parser."""
        parser = argparse.ArgumentParser(
            description="OpenChronicle Modular Storypack Import System",
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog="""
Examples:
  # Basic import with auto-detection
  python storypack_import_cli.py /path/to/content MyStorypack
  
  # Import with AI processing enabled
  python storypack_import_cli.py /path/to/content MyStorypack --ai-enabled
  
  # Import with specific template
  python storypack_import_cli.py /path/to/content MyStorypack --template fantasy_adventure
  
  # Import with detailed reporting
  python storypack_import_cli.py /path/to/content MyStorypack --report-type detailed --save-report
            """
        )
        
        # Required arguments
        parser.add_argument(
            'source_path',
            type=Path,
            help='Path to the source content directory'
        )
        
        parser.add_argument(
            'storypack_name',
            help='Name for the generated storypack'
        )
        
        # Optional arguments
        parser.add_argument(
            '--output-dir',
            type=Path,
            default=Path('storage/storypacks'),
            help='Output directory for the storypack (default: storage/storypacks)'
        )
        
        parser.add_argument(
            '--import-mode',
            choices=['auto', 'manual', 'ai_assisted'],
            default='auto',
            help='Import mode (default: auto)'
        )
        
        parser.add_argument(
            '--ai-enabled',
            action='store_true',
            help='Enable AI processing for content analysis'
        )
        
        parser.add_argument(
            '--template',
            help='Specific template to use for the storypack'
        )
        
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Perform a dry run without creating files'
        )
        
        parser.add_argument(
            '--report-type',
            choices=['summary', 'standard', 'detailed', 'technical'],
            default='summary',
            help='Type of report to generate (default: summary)'
        )
        
        parser.add_argument(
            '--save-report',
            action='store_true',
            help='Save detailed report to file'
        )
        
        parser.add_argument(
            '--report-format',
            choices=['json', 'txt', 'html'],
            default='json',
            help='Format for saved report (default: json)'
        )
        
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Enable verbose output'
        )
        
        parser.add_argument(
            '--quiet',
            action='store_true',
            help='Suppress output (except errors)'
        )
        
        return parser
    
    def setup_orchestrator(self, args: argparse.Namespace) -> StorypackOrchestrator:
        """Set up the orchestrator with configured components."""
        # Initialize components
        content_parser = ContentParser()
        metadata_extractor = MetadataExtractor()
        structure_analyzer = StructureAnalyzer()
        
        ai_processor = AIProcessor() if args.ai_enabled else None
        content_classifier = ContentClassifier()
        validation_engine = ValidationEngine()
        
        storypack_builder = StorypackBuilder()
        template_engine = TemplateEngine()
        output_formatter = OutputFormatter()
        
        # Create orchestrator with dependency injection
        orchestrator = StorypackOrchestrator(
            content_parser=content_parser,
            metadata_extractor=metadata_extractor,
            structure_analyzer=structure_analyzer,
            ai_processor=ai_processor,
            content_classifier=content_classifier,
            validation_engine=validation_engine,
            storypack_builder=storypack_builder,
            template_engine=template_engine,
            output_formatter=output_formatter
        )
        
        return orchestrator
    
    async def run_import(self, args: argparse.Namespace) -> int:
        """Run the import process."""
        try:
            # Validate inputs
            if not args.source_path.exists():
                self.logger.error(f"Source path does not exist: {args.source_path}")
                return 1
            
            if not args.source_path.is_dir():
                self.logger.error(f"Source path is not a directory: {args.source_path}")
                return 1
            
            # Setup orchestrator
            self.orchestrator = self.setup_orchestrator(args)
            
            # Calculate target path
            target_path = args.output_dir / args.storypack_name
            
            # Configure verbosity
            if args.verbose:
                print(f"🔧 Starting import of '{args.storypack_name}'")
                print(f"   Source: {args.source_path}")
                print(f"   Target: {target_path}")
                print(f"   Mode: {args.import_mode}")
                print(f"   AI: {'Enabled' if args.ai_enabled else 'Disabled'}")
                if args.template:
                    print(f"   Template: {args.template}")
                print()
            
            # Run the import
            result = await self.orchestrator.import_storypack(
                source_path=args.source_path,
                storypack_name=args.storypack_name,
                target_dir=args.output_dir,
                import_mode=args.import_mode
            )
            
            # Handle results
            return await self.handle_results(result, args)
            
        except KeyboardInterrupt:
            if not args.quiet:
                print("\n❌ Import cancelled by user")
            return 130
        
        except Exception as e:
            self.logger.error(f"Import failed with error: {e}")
            if not args.quiet:
                print(f"❌ Import failed: {e}")
            return 1
    
    async def handle_results(self, result, args: argparse.Namespace) -> int:
        """Handle and display import results."""
        if not self.orchestrator:
            return 1
        
        # Format and display results
        if not args.quiet:
            if args.report_type == 'summary':
                output = self.orchestrator.output_formatter.format_import_result(
                    result, 'summary'
                )
                print(output)
            else:
                output = self.orchestrator.output_formatter.format_import_result(
                    result, 'detailed'
                )
                print(output)
        
        # Save detailed report if requested
        if args.save_report:
            await self.save_detailed_report(result, args)
        
        # Log completion
        log_system_event("storypack_import_cli", "Import completed", {
            "storypack_name": result.storypack_name,
            "success": result.success,
            "files_processed": result.files_processed,
            "processing_time": result.processing_time,
            "errors": len(result.errors),
            "warnings": len(result.warnings)
        })
        
        return 0 if result.success else 1
    
    async def save_detailed_report(self, result, args: argparse.Namespace):
        """Save a detailed report to file."""
        if not self.orchestrator:
            return
        
        try:
            # Generate report
            report_type = args.report_type if args.report_type != 'summary' else 'standard'
            report = self.orchestrator.output_formatter.generate_report(result, report_type)
            
            # Determine output path
            report_filename = f"{result.storypack_name}_import_report.{args.report_format}"
            report_path = Path('logs') / report_filename
            
            # Save report
            success = self.orchestrator.output_formatter.save_report(
                report, report_path, args.report_format
            )
            
            if success and not args.quiet:
                print(f"📄 Report saved to: {report_path}")
            elif not success:
                self.logger.error(f"Failed to save report to {report_path}")
                
        except Exception as e:
            self.logger.error(f"Failed to save report: {e}")
    
    def main(self) -> int:
        """Main CLI entry point."""
        parser = self.create_parser()
        args = parser.parse_args()
        
        # Validate argument combinations
        if args.quiet and args.verbose:
            parser.error("--quiet and --verbose cannot be used together")
        
        # Run the import
        try:
            return asyncio.run(self.run_import(args))
        except Exception as e:
            if not args.quiet:
                print(f"❌ Fatal error: {e}")
            return 1


def main():
    """Entry point for the CLI."""
    cli = ModularStorypackImportCLI()
    sys.exit(cli.main())


if __name__ == '__main__':
    main()
