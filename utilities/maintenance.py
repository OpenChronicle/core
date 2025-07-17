#!/usr/bin/env python3
"""
OpenChronicle Maintenance Utility
Comprehensive maintenance tool that combines cleanup, optimization, and health checks.
"""

import os
import sys
import json
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Dict, Any

# Add the parent directory to the path so we can import core modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from cleanup_storage import StorageCleanup
from optimize_database import DatabaseOptimizer
from logging_system import get_logger, log_maintenance_action, log_system_event, log_error_with_context

class MaintenanceManager:
    """Manages comprehensive maintenance tasks for OpenChronicle."""
    
    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run
        self.root_dir = Path(__file__).parent.parent
        self.maintenance_log = []
        self.logger = get_logger()
        
        # Log maintenance start
        log_system_event("maintenance_start", f"Maintenance utility started (dry_run: {dry_run})")
        
    def log_action(self, action: str, details: Dict[str, Any] = None):
        """Log maintenance action."""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "action": action,
            "details": details or {}
        }
        self.maintenance_log.append(log_entry)
        
        # Use centralized logging
        status = "success" if not details or not details.get("error") else "error"
        log_maintenance_action(action, details, status)
        
    def check_system_health(self) -> Dict[str, Any]:
        """Perform system health checks."""
        health_status = {
            "timestamp": datetime.now().isoformat(),
            "checks": {}
        }
        
        self.logger.info("Performing system health checks...")
        print("🏥 Performing system health checks...")
        
        # Check if main configuration files exist
        config_files = ["config/models.json", "main.py", "requirements.txt"]
        for config_file in config_files:
            file_path = self.root_dir / config_file
            exists = file_path.exists()
            health_status["checks"][config_file] = {
                "exists": exists,
                "size": file_path.stat().st_size if exists else 0,
                "last_modified": datetime.fromtimestamp(file_path.stat().st_mtime).isoformat() if exists else None
            }
            
            if not exists:
                self.logger.warning(f"Configuration file missing: {config_file}")
        
        # Check storage directory structure
        storage_dir = self.root_dir / "storage"
        if storage_dir.exists():
            story_dirs = [d for d in storage_dir.iterdir() if d.is_dir()]
            health_status["checks"]["storage"] = {
                "exists": True,
                "story_count": len(story_dirs),
                "stories": [d.name for d in story_dirs]
            }
            self.logger.info(f"Found {len(story_dirs)} story directories: {[d.name for d in story_dirs]}")
        else:
            health_status["checks"]["storage"] = {"exists": False}
            self.logger.error("Storage directory not found")
        
        # Check Python environment
        try:
            import subprocess
            result = subprocess.run([sys.executable, "--version"], capture_output=True, text=True)
            health_status["checks"]["python"] = {
                "version": result.stdout.strip(),
                "executable": sys.executable
            }
            self.logger.info(f"Python version: {result.stdout.strip()}")
        except Exception as e:
            health_status["checks"]["python"] = {"error": str(e)}
            log_error_with_context(e, {"context": "python_version_check"})
        
        # Check for required modules
        required_modules = ["sqlite3", "json", "pathlib", "datetime"]
        for module in required_modules:
            try:
                __import__(module)
                health_status["checks"][f"module_{module}"] = {"available": True}
            except ImportError as e:
                health_status["checks"][f"module_{module}"] = {"available": False}
                self.logger.error(f"Required module {module} not available")
        
        # Check disk space
        try:
            import shutil
            total, used, free = shutil.disk_usage(self.root_dir)
            free_percent = (free / total * 100) if total > 0 else 0
            health_status["checks"]["disk_space"] = {
                "total": total,
                "used": used,
                "free": free,
                "free_percent": free_percent
            }
            
            # Warn if disk space is low
            if free_percent < 10:
                self.logger.warning(f"Low disk space: {free_percent:.1f}% free")
            elif free_percent < 20:
                self.logger.info(f"Disk space: {free_percent:.1f}% free")
                
        except Exception as e:
            health_status["checks"]["disk_space"] = {"error": str(e)}
            log_error_with_context(e, {"context": "disk_space_check"})
        
        return health_status
    
    def validate_configuration(self) -> Dict[str, Any]:
        """Validate OpenChronicle configuration."""
        self.logger.info("Validating configuration...")
        print("⚙️  Validating configuration...")
        
        validation_result = {
            "timestamp": datetime.now().isoformat(),
            "valid": True,
            "issues": []
        }
        
        # Check models.json
        models_file = self.root_dir / "config" / "models.json"
        if models_file.exists():
            try:
                with open(models_file, 'r') as f:
                    models_config = json.load(f)
                
                # Check required fields
                required_fields = ["default_adapter", "adapters"]
                for field in required_fields:
                    if field not in models_config:
                        issue = f"Missing required field: {field}"
                        validation_result["issues"].append(issue)
                        validation_result["valid"] = False
                        self.logger.error(f"Configuration issue: {issue}")
                
                # Check adapters
                if "adapters" in models_config:
                    for adapter_name, adapter_config in models_config["adapters"].items():
                        if not adapter_name.startswith("//"):  # Skip comments
                            if "type" not in adapter_config:
                                issue = f"Adapter '{adapter_name}' missing type field"
                                validation_result["issues"].append(issue)
                                validation_result["valid"] = False
                                self.logger.error(f"Configuration issue: {issue}")
                
                self.logger.info(f"Configuration validation: {len(validation_result['issues'])} issues found")
                
            except json.JSONDecodeError as e:
                issue = f"Invalid JSON in models.json: {e}"
                validation_result["issues"].append(issue)
                validation_result["valid"] = False
                log_error_with_context(e, {"context": "models.json_validation"})
        else:
            issue = "models.json not found"
            validation_result["issues"].append(issue)
            validation_result["valid"] = False
            self.logger.error(f"Configuration issue: {issue}")
        
        return validation_result
    
    def generate_maintenance_report(self) -> Dict[str, Any]:
        """Generate comprehensive maintenance report."""
        print("📋 Generating maintenance report...")
        
        report = {
            "timestamp": datetime.now().isoformat(),
            "dry_run": self.dry_run,
            "sections": {}
        }
        
        # System health
        report["sections"]["health"] = self.check_system_health()
        
        # Configuration validation
        report["sections"]["configuration"] = self.validate_configuration()
        
        # Storage analysis
        cleanup = StorageCleanup(dry_run=True)  # Always dry run for analysis
        cleanup_items = cleanup.scan_for_cleanup()
        
        total_cleanup_size = 0
        total_cleanup_files = 0
        
        for category, items in cleanup_items.items():
            for item in items:
                total_cleanup_size += item['size']
                total_cleanup_files += 1
        
        report["sections"]["storage"] = {
            "cleanup_opportunities": cleanup_items,
            "total_files": total_cleanup_files,
            "total_size": total_cleanup_size
        }
        
        # Database analysis
        optimizer = DatabaseOptimizer(dry_run=True)
        databases = optimizer.find_databases()
        
        db_stats = []
        for db_path in databases:
            analysis = optimizer.analyze_database(db_path)
            db_stats.append({
                "path": str(db_path.relative_to(self.root_dir)),
                "size": analysis.get("file_size", 0),
                "fragmentation": analysis.get("fragmentation_ratio", 0),
                "needs_vacuum": analysis.get("needs_vacuum", False),
                "tables": len(analysis.get("tables", [])),
                "error": analysis.get("error")
            })
        
        report["sections"]["databases"] = {
            "count": len(databases),
            "databases": db_stats
        }
        
        # Maintenance log
        report["sections"]["maintenance_log"] = self.maintenance_log
        
        return report
    
    def save_report(self, report: Dict[str, Any], filename: str = None) -> Path:
        """Save maintenance report to file."""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"maintenance_report_{timestamp}.json"
        
        report_path = self.root_dir / "utilities" / filename
        
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        return report_path
    
    def run_full_maintenance(self) -> Dict[str, Any]:
        """Run comprehensive maintenance routine."""
        print("🔧 Starting OpenChronicle Full Maintenance")
        print("=" * 50)
        
        if self.dry_run:
            print("🔍 DRY RUN MODE - No changes will be made")
            print()
        
        maintenance_results = {
            "timestamp": datetime.now().isoformat(),
            "dry_run": self.dry_run,
            "results": {}
        }
        
        # Step 1: Health Check
        print("1️⃣  System Health Check")
        health_status = self.check_system_health()
        maintenance_results["results"]["health_check"] = health_status
        self.log_action("health_check", health_status)
        
        # Check critical issues
        critical_issues = []
        if not health_status["checks"].get("config/models.json", {}).get("exists", False):
            critical_issues.append("models.json missing")
        if not health_status["checks"].get("storage", {}).get("exists", False):
            critical_issues.append("storage directory missing")
        
        if critical_issues:
            print(f"❌ Critical issues found: {', '.join(critical_issues)}")
            maintenance_results["results"]["critical_issues"] = critical_issues
            return maintenance_results
        
        print("✅ System health check passed")
        
        # Step 2: Configuration Validation
        print("\n2️⃣  Configuration Validation")
        config_validation = self.validate_configuration()
        maintenance_results["results"]["configuration_validation"] = config_validation
        self.log_action("configuration_validation", config_validation)
        
        if not config_validation["valid"]:
            print(f"⚠️  Configuration issues found: {len(config_validation['issues'])}")
            for issue in config_validation["issues"]:
                print(f"  - {issue}")
        else:
            print("✅ Configuration validation passed")
        
        # Step 3: Storage Cleanup
        print("\n3️⃣  Storage Cleanup")
        cleanup = StorageCleanup(dry_run=self.dry_run)
        cleanup.run_full_cleanup()
        maintenance_results["results"]["storage_cleanup"] = {
            "files_cleaned": len(cleanup.cleaned_files),
            "space_saved": cleanup.cleaned_size
        }
        self.log_action("storage_cleanup", maintenance_results["results"]["storage_cleanup"])
        
        # Step 4: Database Optimization
        print("\n4️⃣  Database Optimization")
        optimizer = DatabaseOptimizer(dry_run=self.dry_run)
        optimizer.run_optimization()
        maintenance_results["results"]["database_optimization"] = {
            "databases_optimized": len(optimizer.optimized_dbs),
            "space_saved": optimizer.total_space_saved
        }
        self.log_action("database_optimization", maintenance_results["results"]["database_optimization"])
        
        # Step 5: Generate Report
        print("\n5️⃣  Generating Maintenance Report")
        report = self.generate_maintenance_report()
        
        if not self.dry_run:
            report_path = self.save_report(report)
            print(f"📄 Maintenance report saved: {report_path.name}")
            maintenance_results["results"]["report_path"] = str(report_path)
        
        # Summary
        total_space_saved = cleanup.cleaned_size + optimizer.total_space_saved
        total_files_processed = len(cleanup.cleaned_files) + len(optimizer.optimized_dbs)
        
        print(f"\n🎉 Maintenance Complete!")
        print(f"  📁 Files/databases processed: {total_files_processed}")
        print(f"  💾 Total space saved: {self._format_size(total_space_saved)}")
        
        if self.dry_run:
            print("\n💡 Run without --dry-run to actually perform maintenance")
        
        return maintenance_results
    
    def _format_size(self, size_bytes: int) -> str:
        """Format file size in human readable format."""
        if size_bytes == 0:
            return "0 B"
        
        units = ['B', 'KB', 'MB', 'GB', 'TB']
        i = 0
        while size_bytes >= 1024 and i < len(units) - 1:
            size_bytes /= 1024
            i += 1
        
        return f"{size_bytes:.1f} {units[i]}"


def main():
    """Main function with command line interface."""
    import argparse
    
    parser = argparse.ArgumentParser(description="OpenChronicle Maintenance Utility")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be done without making changes")
    parser.add_argument("--health-check", action="store_true", help="Only perform health check")
    parser.add_argument("--cleanup-only", action="store_true", help="Only perform storage cleanup")
    parser.add_argument("--optimize-only", action="store_true", help="Only perform database optimization")
    parser.add_argument("--report-only", action="store_true", help="Only generate maintenance report")
    parser.add_argument("--save-report", type=str, help="Save report to specific filename")
    
    args = parser.parse_args()
    
    maintenance = MaintenanceManager(dry_run=args.dry_run)
    
    if args.health_check:
        health_status = maintenance.check_system_health()
        print(json.dumps(health_status, indent=2, default=str))
    elif args.cleanup_only:
        cleanup = StorageCleanup(dry_run=args.dry_run)
        cleanup.run_full_cleanup()
    elif args.optimize_only:
        optimizer = DatabaseOptimizer(dry_run=args.dry_run)
        optimizer.run_optimization()
    elif args.report_only:
        report = maintenance.generate_maintenance_report()
        if args.save_report:
            report_path = maintenance.save_report(report, args.save_report)
            print(f"📄 Report saved: {report_path}")
        else:
            print(json.dumps(report, indent=2, default=str))
    else:
        # Run full maintenance
        maintenance.run_full_maintenance()


if __name__ == "__main__":
    main()
