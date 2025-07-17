"""
Timeline Builder for OpenChronicle.
Creates timeline views and navigation utilities for stories.
"""

import json
from datetime import datetime
from typing import Dict, List, Optional, Any
from .database import execute_query, init_database
from .bookmark_manager import BookmarkManager
from .scene_logger import list_scenes, get_labeled_scenes

class TimelineBuilder:
    """Builds story timelines and navigation structures."""
    
    def __init__(self, story_id: str):
        self.story_id = story_id
        self.bookmark_manager = BookmarkManager(story_id)
        init_database(story_id)
    
    def get_full_timeline(self) -> Dict[str, Any]:
        """Get complete story timeline with scenes and bookmarks."""
        # Get all scenes
        scenes = execute_query(self.story_id, '''
            SELECT scene_id, timestamp, input, output, memory_snapshot, flags, canon_refs, scene_label
            FROM scenes ORDER BY timestamp ASC
        ''')
        
        # Get all bookmarks with scene info
        bookmarks = self.bookmark_manager.get_timeline_bookmarks()
        
        # Organize timeline entries
        timeline_entries = []
        
        for scene in scenes:
            entry = {
                'type': 'scene',
                'scene_id': scene[0],
                'timestamp': scene[1],
                'input': scene[2],
                'output': scene[3],
                'memory_snapshot': json.loads(scene[4] or '{}'),
                'flags': json.loads(scene[5] or '[]'),
                'canon_refs': json.loads(scene[6] or '[]'),
                'scene_label': scene[7],
                'bookmarks': []
            }
            
            # Add associated bookmarks
            scene_bookmarks = [b for b in bookmarks if b['scene_id'] == scene[0]]
            entry['bookmarks'] = scene_bookmarks
            
            timeline_entries.append(entry)
        
        return {
            'story_id': self.story_id,
            'total_scenes': len(scenes),
            'total_bookmarks': len(bookmarks),
            'timeline': timeline_entries
        }
    
    def get_chapter_timeline(self) -> Dict[str, Any]:
        """Get timeline organized by chapters (bookmarks with type 'chapter')."""
        chapters = self.bookmark_manager.get_chapter_structure()
        
        # Get scenes between chapter markers
        timeline = []
        
        # Sort chapters by timestamp
        all_chapters = []
        for level, chapter_list in chapters.items():
            for chapter in chapter_list:
                chapter['level'] = level
                all_chapters.append(chapter)
        
        all_chapters.sort(key=lambda x: x['created_at'])
        
        for i, chapter in enumerate(all_chapters):
            chapter_scenes = self._get_scenes_in_chapter(chapter, 
                                                       all_chapters[i+1] if i+1 < len(all_chapters) else None)
            
            timeline.append({
                'chapter': chapter,
                'scenes': chapter_scenes,
                'scene_count': len(chapter_scenes)
            })
        
        return {
            'story_id': self.story_id,
            'chapters': timeline,
            'total_chapters': len(timeline)
        }
    
    def get_labeled_timeline(self) -> Dict[str, Any]:
        """Get timeline showing only labeled scenes."""
        labeled_scenes = get_labeled_scenes(self.story_id)
        
        # Group by label
        grouped = {}
        for scene in labeled_scenes:
            label = scene['scene_label']
            if label not in grouped:
                grouped[label] = []
            grouped[label].append(scene)
        
        return {
            'story_id': self.story_id,
            'labeled_scenes': grouped,
            'total_labels': len(grouped),
            'total_labeled_scenes': len(labeled_scenes)
        }
    
    def get_navigation_menu(self) -> Dict[str, Any]:
        """Get navigation menu structure for story browsing."""
        # Get chapter bookmarks
        chapters = self.bookmark_manager.list_bookmarks(bookmark_type="chapter")
        
        # Get user bookmarks
        user_bookmarks = self.bookmark_manager.list_bookmarks(bookmark_type="user")
        
        # Get labeled scenes
        labeled_scenes = get_labeled_scenes(self.story_id)
        
        # Get recent scenes (last 10)
        recent_scenes = execute_query(self.story_id, '''
            SELECT scene_id, timestamp, scene_label, input
            FROM scenes ORDER BY timestamp DESC LIMIT 10
        ''')
        
        return {
            'story_id': self.story_id,
            'chapters': chapters,
            'user_bookmarks': user_bookmarks,
            'labeled_scenes': labeled_scenes,
            'recent_scenes': [{
                'scene_id': row[0],
                'timestamp': row[1],
                'scene_label': row[2],
                'input': row[3]
            } for row in recent_scenes]
        }
    
    def export_timeline_json(self, include_content: bool = True) -> str:
        """Export timeline as JSON string."""
        if include_content:
            timeline = self.get_full_timeline()
        else:
            # Minimal export without scene content
            timeline = self.get_chapter_timeline()
        
        return json.dumps(timeline, indent=2, ensure_ascii=False)
    
    def export_timeline_markdown(self) -> str:
        """Export timeline as Markdown."""
        timeline = self.get_full_timeline()
        
        md_lines = [
            f"# Story Timeline: {self.story_id}",
            f"",
            f"**Total Scenes:** {timeline['total_scenes']}",
            f"**Total Bookmarks:** {timeline['total_bookmarks']}",
            f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"",
            f"---",
            f""
        ]
        
        for i, entry in enumerate(timeline['timeline'], 1):
            # Scene header
            scene_label = entry['scene_label'] or f"Scene {i}"
            md_lines.append(f"## {scene_label}")
            md_lines.append(f"**Scene ID:** `{entry['scene_id']}`")
            md_lines.append(f"**Timestamp:** {entry['timestamp']}")
            
            # Bookmarks
            if entry['bookmarks']:
                md_lines.append(f"**Bookmarks:**")
                for bookmark in entry['bookmarks']:
                    md_lines.append(f"- {bookmark['label']} ({bookmark['bookmark_type']})")
            
            # Scene content
            md_lines.append(f"")
            md_lines.append(f"**Input:** {entry['input']}")
            md_lines.append(f"")
            md_lines.append(f"**Output:**")
            md_lines.append(f"```")
            md_lines.append(entry['output'])
            md_lines.append(f"```")
            
            # Flags if any
            if entry['flags']:
                md_lines.append(f"**Flags:** {', '.join(entry['flags'])}")
            
            md_lines.append(f"")
            md_lines.append(f"---")
            md_lines.append(f"")
        
        return "\n".join(md_lines)
    
    def get_scene_context(self, scene_id: str, context_window: int = 2) -> Dict[str, Any]:
        """Get scene with surrounding context for navigation."""
        # Get all scenes in chronological order
        scenes = execute_query(self.story_id, '''
            SELECT scene_id, timestamp, input, output, scene_label
            FROM scenes ORDER BY timestamp ASC
        ''')
        
        # Find target scene index
        target_index = None
        for i, scene in enumerate(scenes):
            if scene[0] == scene_id:
                target_index = i
                break
        
        if target_index is None:
            return {'error': f'Scene {scene_id} not found'}
        
        # Get context window
        start_idx = max(0, target_index - context_window)
        end_idx = min(len(scenes), target_index + context_window + 1)
        
        context_scenes = []
        for i in range(start_idx, end_idx):
            scene = scenes[i]
            context_scenes.append({
                'scene_id': scene[0],
                'timestamp': scene[1],
                'input': scene[2],
                'output': scene[3],
                'scene_label': scene[4],
                'is_target': i == target_index,
                'position': i - target_index  # Relative position
            })
        
        return {
            'story_id': self.story_id,
            'target_scene_id': scene_id,
            'context_window': context_window,
            'scenes': context_scenes,
            'total_scenes': len(scenes),
            'target_position': target_index
        }
    
    def _get_scenes_in_chapter(self, chapter: Dict[str, Any], next_chapter: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Get scenes between chapter markers."""
        # Get scene info for chapter start
        chapter_scene = execute_query(self.story_id, '''
            SELECT timestamp FROM scenes WHERE scene_id = ?
        ''', (chapter['scene_id'],))
        
        if not chapter_scene:
            return []
        
        start_timestamp = chapter_scene[0][0]
        
        # Determine end timestamp
        if next_chapter:
            next_scene = execute_query(self.story_id, '''
                SELECT timestamp FROM scenes WHERE scene_id = ?
            ''', (next_chapter['scene_id'],))
            end_timestamp = next_scene[0][0] if next_scene else None
        else:
            end_timestamp = None
        
        # Get scenes in range
        if end_timestamp:
            scenes = execute_query(self.story_id, '''
                SELECT scene_id, timestamp, input, output, scene_label
                FROM scenes 
                WHERE timestamp >= ? AND timestamp < ?
                ORDER BY timestamp ASC
            ''', (start_timestamp, end_timestamp))
        else:
            scenes = execute_query(self.story_id, '''
                SELECT scene_id, timestamp, input, output, scene_label
                FROM scenes 
                WHERE timestamp >= ?
                ORDER BY timestamp ASC
            ''', (start_timestamp,))
        
        return [{
            'scene_id': scene[0],
            'timestamp': scene[1],
            'input': scene[2],
            'output': scene[3],
            'scene_label': scene[4]
        } for scene in scenes]
    
    def get_stats(self) -> Dict[str, Any]:
        """Get timeline statistics."""
        # Scene stats
        scene_stats = execute_query(self.story_id, '''
            SELECT 
                COUNT(*) as total_scenes,
                COUNT(scene_label) as labeled_scenes,
                MIN(timestamp) as first_scene,
                MAX(timestamp) as last_scene
            FROM scenes
        ''')[0]
        
        # Bookmark stats
        bookmark_stats = self.bookmark_manager.get_stats()
        
        return {
            'story_id': self.story_id,
            'scenes': {
                'total': scene_stats[0],
                'labeled': scene_stats[1],
                'unlabeled': scene_stats[0] - scene_stats[1],
                'first_timestamp': scene_stats[2],
                'last_timestamp': scene_stats[3]
            },
            'bookmarks': bookmark_stats,
            'timeline_coverage': {
                'has_chapters': bookmark_stats['by_type'].get('chapter', 0) > 0,
                'has_user_bookmarks': bookmark_stats['by_type'].get('user', 0) > 0,
                'labeling_percentage': (scene_stats[1] / scene_stats[0] * 100) if scene_stats[0] > 0 else 0
            }
        }
