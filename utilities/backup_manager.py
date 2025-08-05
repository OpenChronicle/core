#!/usr/bin/env python3
"""
OpenChronicle Backup Manager Utility
Centralized backup management for configurations, databases, and other critical files.
"""

import os
import sys
import shutil
import sqlite3
import json
import argparse
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from logging_system import log_maintenance_action, log_system_event, log_info, log_error

# Add the parent directory to the path so we can import core modules
sys.path.insert(0, str(Path(__file__).parent.parent))

class BackupManager:
    """Centralized backup management for OpenChronicle."""
    
    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run
        self.root_dir = Path(__file__).parent.parent
        self.backup_dir = self.root_dir / "storage" / "backups"
        self.config_dir = self.root_dir / "config"
        self.storage_dir = self.root_dir / "storage"
        self.logs_dir = self.root_dir / "logs"
        
        # Backup subdirectories
        self.config_backup_dir = self.backup_dir / "config"
        self.database_backup_dir = self.backup_dir / "databases"
        self.log_backup_dir = self.backup_dir / "logs"
        self.story_backup_dir = self.backup_dir / "stories"
        
        # Statistics
        self.backed_up_files = []
        self.total_backup_size = 0
        
    def ensure_backup_directories(self) -> None:
        """Ensure all backup directories exist."""
        for backup_dir in [self.config_backup_dir, self.database_backup_dir, 
                          self.log_backup_dir, self.story_backup_dir]:
            if not self.dry_run:
                backup_dir.mkdir(parents=True, exist_ok=True)
            log_info(f"Ensured backup directory: {backup_dir}")
    
    def backup_config(self, config_file: str = "model_registry.json") -> Optional[Path]:
        """Backup configuration files."""
        config_path = self.config_dir / config_file
        if not config_path.exists():
            log_error(f"Configuration file not found: {config_path}")
            return None
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"{config_file}.backup.{timestamp}"
        backup_path = self.config_backup_dir / backup_filename
        
        if not self.dry_run:
            shutil.copy2(config_path, backup_path)
        
        file_size = config_path.stat().st_size
        self.backed_up_files.append(str(backup_path))
        self.total_backup_size += file_size
        
        log_info(f"Backed up config: {config_file} -> {backup_filename}")
        log_maintenance_action("backup_config", "success", {
            "file": config_file,
            "backup_path": str(backup_path),
            "size": file_size
        })
        
        return backup_path
    
    def backup_models_directory(self) -> Optional[Path]:
        """Backup the entire models directory with all provider configurations."""
        models_dir = self.config_dir / "models"
        if not models_dir.exists():
            log_error(f"Models directory not found: {models_dir}")
            return None
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_dirname = f"models_backup_{timestamp}"
        backup_path = self.config_backup_dir / backup_dirname
        
        if not self.dry_run:
            shutil.copytree(models_dir, backup_path)
        
        # Calculate total size of all files
        total_size = 0
        model_files = []
        for model_file in models_dir.glob("*.json"):
            if model_file.is_file():
                model_files.append(model_file.name)
                total_size += model_file.stat().st_size
        
        self.backed_up_files.append(str(backup_path))
        self.total_backup_size += total_size
        
        log_info(f"Backed up models directory: {len(model_files)} model configs -> {backup_dirname}")
        log_maintenance_action("backup_models_directory", "success", {
            "models_count": len(model_files),
            "models": model_files,
            "backup_path": str(backup_path),
            "total_size": total_size
        })
        
        return backup_path
    
    def backup_full_config(self) -> Dict[str, Optional[Path]]:
        """Backup all configuration files including model registry and models directory."""
        results = {}
        
        # Backup model registry
        results["model_registry"] = self.backup_config("model_registry.json")
        
        # Backup models directory
        results["models_directory"] = self.backup_models_directory()
        
        return results
    
    def backup_database(self, db_path: Path) -> Optional[Path]:
        """Backup a database file."""
        if not db_path.exists():
            log_error(f"Database file not found: {db_path}")
            return None
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"{db_path.stem}_{timestamp}.db"
        backup_path = self.database_backup_dir / backup_filename
        
        if not self.dry_run:
            # Use SQLite backup for database files
            try:
                with sqlite3.connect(str(db_path)) as src_conn:
                    with sqlite3.connect(str(backup_path)) as dst_conn:
                        src_conn.backup(dst_conn)
            except Exception as e:
                log_error(f"Database backup failed: {e}")
                # Fallback to file copy
                shutil.copy2(db_path, backup_path)
        
        file_size = db_path.stat().st_size
        self.backed_up_files.append(str(backup_path))
        self.total_backup_size += file_size
        
        log_info(f"Backed up database: {db_path.name} -> {backup_filename}")
        log_maintenance_action("backup_database", "success", {
            "file": str(db_path),
            "backup_path": str(backup_path),
            "size": file_size
        })
        
        return backup_path
    
    def backup_story(self, story_name: str) -> Optional[Path]:
        """Backup an entire story directory."""
        story_path = self.storage_dir / story_name
        if not story_path.exists() or not story_path.is_dir():
            log_error(f"Story directory not found: {story_path}")
            return None
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"{story_name}_{timestamp}"
        backup_path = self.story_backup_dir / backup_filename
        
        if not self.dry_run:
            shutil.copytree(story_path, backup_path)
        
        # Calculate directory size
        total_size = sum(f.stat().st_size for f in story_path.rglob("*") if f.is_file())
        file_count = len(list(story_path.rglob("*")))
        
        self.backed_up_files.append(str(backup_path))
        self.total_backup_size += total_size
        
        log_info(f"Backed up story: {story_name} -> {backup_filename}")
        log_maintenance_action("backup_story", "success", {
            "story": story_name,
            "backup_path": str(backup_path),
            "size": total_size,
            "file_count": file_count
        })
        
        return backup_path
    
    def backup_logs(self, max_age_days: int = 30) -> List[Path]:
        """Backup and archive old log files."""
        if not self.logs_dir.exists():
            log_info("No logs directory found")
            return []
        
        cutoff_date = datetime.now() - timedelta(days=max_age_days)
        backed_up_logs = []
        
        for log_file in self.logs_dir.glob("*.log*"):
            if log_file.is_file():
                modified_time = datetime.fromtimestamp(log_file.stat().st_mtime)
                if modified_time < cutoff_date:
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    backup_filename = f"{log_file.name}_{timestamp}"
                    backup_path = self.log_backup_dir / backup_filename
                    
                    if not self.dry_run:
                        shutil.copy2(log_file, backup_path)
                    
                    file_size = log_file.stat().st_size
                    self.backed_up_files.append(str(backup_path))
                    self.total_backup_size += file_size
                    backed_up_logs.append(backup_path)
                    
                    log_info(f"Backed up log: {log_file.name} -> {backup_filename}")
        
        if backed_up_logs:
            log_maintenance_action("backup_logs", "success", {
                "logs_backed_up": len(backed_up_logs),
                "total_size": sum(f.stat().st_size for f in backed_up_logs if f.exists())
            })
        
        return backed_up_logs
    
    def cleanup_old_backups(self, backup_type: str = "all", keep_count: int = 10) -> Dict[str, int]:
        """Clean up old backup files, keeping only the most recent ones."""
        cleanup_stats = {"config": 0, "databases": 0, "logs": 0, "stories": 0}
        
        backup_dirs = {
            "config": self.config_backup_dir,
            "databases": self.database_backup_dir,
            "logs": self.log_backup_dir,
            "stories": self.story_backup_dir
        }
        
        if backup_type == "all":
            dirs_to_clean = backup_dirs
        else:
            dirs_to_clean = {backup_type: backup_dirs.get(backup_type)}
        
        for backup_category, backup_dir in dirs_to_clean.items():
            if not backup_dir or not backup_dir.exists():
                continue
            
            # Get all backup files, sorted by modification time (newest first)
            backup_files = sorted(
                [f for f in backup_dir.iterdir() if f.is_file()],
                key=lambda x: x.stat().st_mtime,
                reverse=True
            )
            
            if len(backup_files) > keep_count:
                files_to_remove = backup_files[keep_count:]
                
                for backup_file in files_to_remove:
                    file_size = backup_file.stat().st_size
                    if not self.dry_run:
                        backup_file.unlink()
                    
                    cleanup_stats[backup_category] += 1
                    log_info(f"Removed old backup: {backup_file.name}")
                
                log_maintenance_action("cleanup_old_backups", "success", {
                    "category": backup_category,
                    "files_removed": len(files_to_remove),
                    "files_kept": keep_count
                })
        
        return cleanup_stats
    
    def get_backup_statistics(self) -> Dict[str, Any]:
        """Get comprehensive backup statistics."""
        stats = {
            "directories": {},
            "total_files": 0,
            "total_size": 0
        }
        
        for category, backup_dir in [
            ("config", self.config_backup_dir),
            ("databases", self.database_backup_dir),
            ("logs", self.log_backup_dir),
            ("stories", self.story_backup_dir)
        ]:
            if backup_dir.exists():
                files = list(backup_dir.rglob("*"))
                file_count = len([f for f in files if f.is_file()])
                total_size = sum(f.stat().st_size for f in files if f.is_file())
                
                stats["directories"][category] = {
                    "file_count": file_count,
                    "total_size": total_size,
                    "latest_backup": None
                }
                
                # Find latest backup
                if file_count > 0:
                    latest_file = max(
                        [f for f in files if f.is_file()],
                        key=lambda x: x.stat().st_mtime
                    )
                    stats["directories"][category]["latest_backup"] = {
                        "file": latest_file.name,
                        "timestamp": datetime.fromtimestamp(latest_file.stat().st_mtime).isoformat()
                    }
                
                stats["total_files"] += file_count
                stats["total_size"] += total_size
        
        return stats
    
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
    
    def run_full_backup(self) -> None:
        """Run a comprehensive backup of all critical files."""
        log_system_event("backup_start", "Full backup started")
        log_info("Starting comprehensive backup")
        
        if self.dry_run:
            log_info("DRY RUN MODE - No files will be actually backed up")
        
        self.ensure_backup_directories()
        
        # Backup configurations
        log_info("Backing up configurations...")
        config_results = self.backup_full_config()
        
        # Log configuration backup results
        for config_type, result in config_results.items():
            if result:
                log_info(f"  [OK] {config_type}: {result.name}")
            else:
                log_info(f"  [SKIP] {config_type}: Not found or failed")
        
        # Backup databases
        log_info("Backing up databases...")
        for story_dir in self.storage_dir.iterdir():
            if story_dir.is_dir() and story_dir.name not in ["backups"]:
                db_files = list(story_dir.glob("*.db"))
                for db_file in db_files:
                    self.backup_database(db_file)
        
        # Backup logs
        log_info("Backing up old logs...")
        self.backup_logs()
        
        # Clean up old backups
        log_info("Cleaning up old backups...")
        cleanup_stats = self.cleanup_old_backups()
        
        # Summary
        log_info("Backup Summary:")
        log_info(f"  Files backed up: {len(self.backed_up_files)}")
        log_info(f"  Total backup size: {self._format_size(self.total_backup_size)}")
        log_info(f"  Old backups cleaned: {sum(cleanup_stats.values())}")
        
        if self.dry_run:
            log_info("Run without --dry-run to actually perform backups")
        
        log_system_event("backup_complete", f"Full backup completed - {len(self.backed_up_files)} files backed up")
    
    def restore_config(self, backup_path: str, config_type: str = "model_registry") -> bool:
        """Restore configuration from backup."""
        backup_file = Path(backup_path)
        if not backup_file.exists():
            log_error(f"Backup file not found: {backup_path}")
            return False
        
        if config_type == "model_registry":
            restore_path = self.config_dir / "model_registry.json"
        elif config_type == "models_directory":
            restore_path = self.config_dir / "models"
            # Remove existing models directory if it exists
            if restore_path.exists() and not self.dry_run:
                shutil.rmtree(restore_path)
        else:
            log_error(f"Unknown config type: {config_type}")
            return False
        
        try:
            if not self.dry_run:
                if config_type == "models_directory":
                    shutil.copytree(backup_file, restore_path)
                else:
                    shutil.copy2(backup_file, restore_path)
            
            log_info(f"Restored {config_type} from {backup_file.name}")
            log_maintenance_action("restore_config", "success", {
                "config_type": config_type,
                "backup_path": str(backup_file),
                "restore_path": str(restore_path)
            })
            return True
            
        except Exception as e:
            log_error(f"Failed to restore {config_type}: {e}")
            return False
    
    def list_config_backups(self) -> Dict[str, List[Dict[str, Any]]]:
        """List available configuration backups."""
        backups = {
            "model_registry": [],
            "models_directory": [],
            "legacy_models": []
        }
        
        if not self.config_backup_dir.exists():
            return backups
        
        for backup_file in self.config_backup_dir.iterdir():
            if backup_file.is_file():
                if backup_file.name.startswith("model_registry.json.backup"):
                    backups["model_registry"].append({
                        "file": backup_file.name,
                        "path": str(backup_file),
                        "timestamp": backup_file.stat().st_mtime,
                        "size": backup_file.stat().st_size
                    })
                elif backup_file.name.startswith("models.json.backup"):
                    backups["legacy_models"].append({
                        "file": backup_file.name,
                        "path": str(backup_file),
                        "timestamp": backup_file.stat().st_mtime,
                        "size": backup_file.stat().st_size
                    })
            elif backup_file.is_dir() and backup_file.name.startswith("models_backup_"):
                model_count = len(list(backup_file.glob("*.json")))
                total_size = sum(f.stat().st_size for f in backup_file.glob("*.json"))
                backups["models_directory"].append({
                    "directory": backup_file.name,
                    "path": str(backup_file),
                    "timestamp": backup_file.stat().st_mtime,
                    "model_count": model_count,
                    "total_size": total_size
                })
        
        # Sort by timestamp (newest first)
        for backup_type in backups:
            backups[backup_type].sort(key=lambda x: x["timestamp"], reverse=True)
        
        return backups


def main():
    """Main function with command line interface."""
    parser = argparse.ArgumentParser(description="OpenChronicle Backup Manager")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be backed up without actually doing it")
    parser.add_argument("--config", action="store_true", help="Backup configuration files only")
    parser.add_argument("--databases", action="store_true", help="Backup database files only")
    parser.add_argument("--logs", action="store_true", help="Backup log files only")
    parser.add_argument("--stories", action="store_true", help="Backup story files only")
    parser.add_argument("--story", type=str, help="Backup specific story directory")
    parser.add_argument("--cleanup", action="store_true", help="Clean up old backups only")
    parser.add_argument("--stats", action="store_true", help="Show backup statistics")
    parser.add_argument("--keep", type=int, default=10, help="Number of backups to keep during cleanup (default: 10)")
    
    args = parser.parse_args()
    
    backup_manager = BackupManager(dry_run=args.dry_run)
    
    if args.stats:
        log_info("Backup Statistics:")
        stats = backup_manager.get_backup_statistics()
        print(json.dumps(stats, indent=2, default=str))
        return
    
    if args.cleanup:
        log_info("Cleaning up old backups...")
        cleanup_stats = backup_manager.cleanup_old_backups(keep_count=args.keep)
        log_info(f"Cleanup completed: {sum(cleanup_stats.values())} files removed")
        return
    
    backup_manager.ensure_backup_directories()
    
    if args.config:
        log_info("Backing up configuration files...")
        backup_manager.backup_config()
    elif args.databases:
        log_info("Backing up database files...")
        for story_dir in backup_manager.storage_dir.iterdir():
            if story_dir.is_dir() and story_dir.name not in ["backups"]:
                db_files = list(story_dir.glob("*.db"))
                for db_file in db_files:
                    backup_manager.backup_database(db_file)
    elif args.logs:
        log_info("Backing up log files...")
        backup_manager.backup_logs()
    elif args.stories:
        log_info("Backing up all story files...")
        for story_dir in backup_manager.storage_dir.iterdir():
            if story_dir.is_dir() and story_dir.name not in ["backups"]:
                backup_manager.backup_story(story_dir.name)
    elif args.story:
        log_info(f"Backing up story: {args.story}")
        backup_manager.backup_story(args.story)
    else:
        # Full backup
        backup_manager.run_full_backup()


if __name__ == "__main__":
    main()
