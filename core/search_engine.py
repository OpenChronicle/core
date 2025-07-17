"""
OpenChronicle Full-Text Search Engine with FTS5 Integration

This module provides comprehensive full-text search capabilities for OpenChronicle stories
using SQLite FTS5 virtual tables. It supports advanced query operators, relevance ranking,
and seamless integration with existing scene labeling and bookmark systems.

Features:
- Fast full-text search across scenes and memory
- Advanced query operators (AND, OR, NOT, quotes, wildcards)
- Relevance ranking and scoring
- Search result highlighting and snippets
- Query sanitization and validation
- Integration with scene labels and bookmarks
- Search statistics and analytics
"""

import sqlite3
import json
import re
from typing import Dict, List, Optional, Tuple, Union
from datetime import datetime
from dataclasses import dataclass, field

from .database import get_connection, check_fts_support, optimize_fts_index


@dataclass
class SearchResult:
    """Represents a search result with metadata."""
    id: str
    content_type: str  # 'scene' or 'memory'
    title: str
    content: str
    snippet: str
    score: float
    timestamp: Optional[str] = None
    scene_label: Optional[str] = None
    metadata: Dict = field(default_factory=dict)


@dataclass
class SearchQuery:
    """Represents a parsed search query."""
    original: str
    sanitized: str
    terms: List[str]
    operators: List[str]
    quoted_phrases: List[str]
    filters: Dict[str, str]
    content_types: List[str]


class SearchEngine:
    """Full-text search engine with FTS5 integration."""
    
    def __init__(self, story_id: str):
        """Initialize search engine for a specific story."""
        self.story_id = story_id
        self.fts_supported = check_fts_support()
        
        if not self.fts_supported:
            raise RuntimeError("FTS5 is not supported in this SQLite version")
    
    def parse_query(self, query: str) -> SearchQuery:
        """Parse and sanitize a search query."""
        original = query.strip()
        
        # Extract quoted phrases
        quoted_phrases = re.findall(r'"([^"]*)"', original)
        
        # Extract filters (e.g., type:scene, label:chapter)
        filters = {}
        filter_pattern = r'(\w+):(\w+)'
        for match in re.finditer(filter_pattern, original):
            key, value = match.groups()
            filters[key] = value
        
        # Remove quoted phrases and filters from main query
        sanitized = original
        for phrase in quoted_phrases:
            sanitized = sanitized.replace(f'"{phrase}"', '')
        for key, value in filters.items():
            sanitized = sanitized.replace(f'{key}:{value}', '')
        
        # Extract individual terms and operators
        terms = []
        operators = []
        
        # Split by common operators while preserving them
        parts = re.split(r'\s+(AND|OR|NOT)\s+', sanitized, flags=re.IGNORECASE)
        
        for i, part in enumerate(parts):
            part = part.strip()
            if part.upper() in ['AND', 'OR', 'NOT']:
                operators.append(part.upper())
            elif part:
                # Split by whitespace and filter out empty strings
                words = [word.strip() for word in part.split() if word.strip()]
                terms.extend(words)
        
        # Determine content types from filters
        content_types = []
        if 'type' in filters:
            content_types = [filters['type']]
        else:
            content_types = ['scene', 'memory']
        
        # Clean up sanitized query
        sanitized = ' '.join(terms + quoted_phrases)
        
        return SearchQuery(
            original=original,
            sanitized=sanitized,
            terms=terms,
            operators=operators,
            quoted_phrases=quoted_phrases,
            filters=filters,
            content_types=content_types
        )
    
    def search_scenes(self, query: SearchQuery, limit: int = 50) -> List[SearchResult]:
        """Search scenes using FTS5."""
        if 'scene' not in query.content_types:
            return []
        
        with get_connection(self.story_id) as conn:
            cursor = conn.cursor()
            
            # Build FTS5 query
            fts_query = self._build_fts_query(query)
            
            # Apply filters
            where_conditions = []
            params = [fts_query]
            
            if 'label' in query.filters:
                where_conditions.append("s.scene_label LIKE ?")
                params.append(f"%{query.filters['label']}%")
            
            where_clause = ""
            if where_conditions:
                where_clause = " AND " + " AND ".join(where_conditions)
            
            # Execute search with ranking
            sql = f"""
                SELECT 
                    s.scene_id,
                    s.input,
                    s.output,
                    s.scene_label,
                    s.timestamp,
                    s.flags,
                    s.analysis,
                    bm25(scenes_fts) as score,
                    snippet(scenes_fts, 1, '<mark>', '</mark>', '...', 32) as snippet_input,
                    snippet(scenes_fts, 2, '<mark>', '</mark>', '...', 32) as snippet_output
                FROM scenes_fts
                JOIN scenes s ON s.rowid = scenes_fts.rowid
                WHERE scenes_fts MATCH ?{where_clause}
                ORDER BY score
                LIMIT ?
            """
            
            params.append(limit)
            cursor.execute(sql, params)
            
            results = []
            for row in cursor.fetchall():
                # Choose best snippet
                snippet = row['snippet_input']
                if '<mark>' not in snippet and '<mark>' in row['snippet_output']:
                    snippet = row['snippet_output']
                
                result = SearchResult(
                    id=row['scene_id'],
                    content_type='scene',
                    title=row['scene_label'] or f"Scene {row['scene_id'][:8]}",
                    content=f"{row['input']}\n\n{row['output']}",
                    snippet=snippet,
                    score=row['score'],
                    timestamp=row['timestamp'],
                    scene_label=row['scene_label'],
                    metadata={
                        'flags': json.loads(row['flags'] or '[]'),
                        'analysis': json.loads(row['analysis'] or '{}')
                    }
                )
                results.append(result)
            
            return results
    
    def search_memory(self, query: SearchQuery, limit: int = 50) -> List[SearchResult]:
        """Search memory using FTS5."""
        if 'memory' not in query.content_types:
            return []
        
        with get_connection(self.story_id) as conn:
            cursor = conn.cursor()
            
            # Build FTS5 query
            fts_query = self._build_fts_query(query)
            
            # Apply filters
            where_conditions = []
            params = [fts_query]
            
            if 'memtype' in query.filters:
                where_conditions.append("m.type = ?")
                params.append(query.filters['memtype'])
            
            where_clause = ""
            if where_conditions:
                where_clause = " AND " + " AND ".join(where_conditions)
            
            # Execute search with ranking
            sql = f"""
                SELECT 
                    m.id,
                    m.type,
                    m.key,
                    m.value,
                    m.created_at,
                    m.updated_at,
                    bm25(memory_fts) as score,
                    snippet(memory_fts, 3, '<mark>', '</mark>', '...', 32) as snippet_key,
                    snippet(memory_fts, 4, '<mark>', '</mark>', '...', 32) as snippet_value
                FROM memory_fts
                JOIN memory m ON m.id = memory_fts.rowid
                WHERE memory_fts MATCH ?{where_clause}
                ORDER BY score
                LIMIT ?
            """
            
            params.append(limit)
            cursor.execute(sql, params)
            
            results = []
            for row in cursor.fetchall():
                # Choose best snippet
                snippet = row['snippet_key']
                if '<mark>' not in snippet and '<mark>' in row['snippet_value']:
                    snippet = row['snippet_value']
                
                result = SearchResult(
                    id=str(row['id']),
                    content_type='memory',
                    title=f"{row['type']}: {row['key']}",
                    content=row['value'],
                    snippet=snippet,
                    score=row['score'],
                    timestamp=row['updated_at'],
                    metadata={
                        'memory_type': row['type'],
                        'key': row['key'],
                        'created_at': row['created_at']
                    }
                )
                results.append(result)
            
            return results
    
    def search_all(self, query_string: str, limit: int = 50) -> List[SearchResult]:
        """Search across all content types."""
        query = self.parse_query(query_string)
        
        # Search scenes and memory
        scene_results = self.search_scenes(query, limit // 2)
        memory_results = self.search_memory(query, limit // 2)
        
        # Combine and sort by relevance
        all_results = scene_results + memory_results
        all_results.sort(key=lambda x: x.score)
        
        return all_results[:limit]
    
    def _build_fts_query(self, query: SearchQuery) -> str:
        """Build FTS5 query from parsed query."""
        parts = []
        
        # Add quoted phrases
        for phrase in query.quoted_phrases:
            parts.append(f'"{phrase}"')
        
        # Add terms with operators
        if query.terms:
            if query.operators:
                # Build complex query with operators
                term_parts = []
                term_idx = 0
                
                for i, op in enumerate(query.operators):
                    if term_idx < len(query.terms):
                        term_parts.append(query.terms[term_idx])
                        term_idx += 1
                    
                    term_parts.append(op)
                    
                    if term_idx < len(query.terms):
                        term_parts.append(query.terms[term_idx])
                        term_idx += 1
                
                # Add remaining terms
                while term_idx < len(query.terms):
                    term_parts.append(query.terms[term_idx])
                    term_idx += 1
                
                parts.append(' '.join(term_parts))
            else:
                # Simple term matching
                parts.extend(query.terms)
        
        # Join with AND if multiple parts
        if len(parts) > 1:
            return ' AND '.join(parts)
        elif parts:
            return parts[0]
        else:
            return '*'  # Match all if no terms
    
    def get_search_stats(self) -> Dict:
        """Get search engine statistics."""
        with get_connection(self.story_id) as conn:
            cursor = conn.cursor()
            
            stats = {
                'fts_supported': self.fts_supported,
                'story_id': self.story_id
            }
            
            # Count indexed scenes
            try:
                cursor.execute("SELECT COUNT(*) FROM scenes_fts")
                stats['indexed_scenes'] = cursor.fetchone()[0]
            except sqlite3.OperationalError:
                stats['indexed_scenes'] = 0
            
            # Count indexed memory entries
            try:
                cursor.execute("SELECT COUNT(*) FROM memory_fts")
                stats['indexed_memory'] = cursor.fetchone()[0]
            except sqlite3.OperationalError:
                stats['indexed_memory'] = 0
            
            return stats
    
    def optimize_indexes(self):
        """Optimize FTS5 indexes for better performance."""
        optimize_fts_index(self.story_id)
    
    def health_check(self) -> Dict:
        """Perform a health check on the search engine."""
        health = {
            'status': 'healthy',
            'fts_supported': self.fts_supported,
            'issues': []
        }
        
        try:
            # Test basic functionality
            test_results = self.search_all('test', limit=1)
            health['search_functional'] = True
        except Exception as e:
            health['status'] = 'unhealthy'
            health['search_functional'] = False
            health['issues'].append(f"Search test failed: {str(e)}")
        
        # Check FTS5 table integrity
        try:
            with get_connection(self.story_id) as conn:
                cursor = conn.cursor()
                cursor.execute("INSERT INTO scenes_fts(scenes_fts) VALUES('integrity-check')")
                cursor.execute("INSERT INTO memory_fts(memory_fts) VALUES('integrity-check')")
                health['fts_integrity'] = True
        except Exception as e:
            health['status'] = 'unhealthy'
            health['fts_integrity'] = False
            health['issues'].append(f"FTS5 integrity check failed: {str(e)}")
        
        return health


# Convenience functions for easy access
def search_story(story_id: str, query: str, limit: int = 50) -> List[SearchResult]:
    """Search a story with a simple query string."""
    engine = SearchEngine(story_id)
    return engine.search_all(query, limit)


def search_scenes_only(story_id: str, query: str, limit: int = 50) -> List[SearchResult]:
    """Search only scenes in a story."""
    engine = SearchEngine(story_id)
    parsed_query = engine.parse_query(query)
    return engine.search_scenes(parsed_query, limit)


def search_memory_only(story_id: str, query: str, limit: int = 50) -> List[SearchResult]:
    """Search only memory in a story."""
    engine = SearchEngine(story_id)
    parsed_query = engine.parse_query(query)
    return engine.search_memory(parsed_query, limit)
