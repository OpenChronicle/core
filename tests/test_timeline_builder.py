"""
Test suite for Timeline Builder

Tests timeline creation, event sequencing, and narrative flow management.
"""

import pytest
import tempfile
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, patch

from core.timeline_builder import (
    TimelineBuilder,
    TimelineEvent,
    build_timeline,
    validate_timeline,
    merge_timelines,
    export_timeline
)


@pytest.fixture
def sample_events():
    """Sample timeline events for testing."""
    return [
        {
            "id": "event_001",
            "timestamp": "2024-01-01T08:00:00Z",
            "type": "story_start",
            "title": "Adventure Begins",
            "description": "Alice starts her journey",
            "characters": ["Alice"],
            "location": "village",
            "scene_id": "scene_001"
        },
        {
            "id": "event_002", 
            "timestamp": "2024-01-01T10:00:00Z",
            "type": "encounter",
            "title": "Meeting Bob",
            "description": "Alice meets the wise Bob",
            "characters": ["Alice", "Bob"],
            "location": "forest_entrance",
            "scene_id": "scene_002"
        },
        {
            "id": "event_003",
            "timestamp": "2024-01-01T14:00:00Z", 
            "type": "conflict",
            "title": "Forest Challenge",
            "description": "Alice faces mysterious creatures",
            "characters": ["Alice"],
            "location": "deep_forest",
            "scene_id": "scene_003"
        }
    ]


@pytest.fixture
def timeline_builder():
    """Create TimelineBuilder instance for testing."""
    return TimelineBuilder()


class TestTimelineEvent:
    """Test TimelineEvent data structure."""
    
    def test_timeline_event_creation(self, sample_events):
        """Test creating TimelineEvent from data."""
        event_data = sample_events[0]
        event = TimelineEvent.from_dict(event_data)
        
        assert event.id == "event_001"
        assert event.title == "Adventure Begins"
        assert "Alice" in event.characters
        assert event.location == "village"
    
    def test_timeline_event_to_dict(self, sample_events):
        """Test converting TimelineEvent to dictionary."""
        event_data = sample_events[0]
        event = TimelineEvent.from_dict(event_data)
        event_dict = event.to_dict()
        
        assert event_dict["id"] == event_data["id"]
        assert event_dict["title"] == event_data["title"]
        assert event_dict["characters"] == event_data["characters"]
    
    def test_timeline_event_validation(self):
        """Test TimelineEvent validation."""
        valid_data = {
            "id": "test_event",
            "timestamp": "2024-01-01T12:00:00Z",
            "type": "test",
            "title": "Test Event"
        }
        
        event = TimelineEvent.from_dict(valid_data)
        assert event.id == "test_event"
        
        # Test with missing required field
        invalid_data = {
            "id": "test_event",
            # Missing timestamp
            "type": "test"
        }
        
        with pytest.raises(KeyError):
            TimelineEvent.from_dict(invalid_data)
    
    def test_timeline_event_ordering(self, sample_events):
        """Test TimelineEvent ordering by timestamp."""
        events = [TimelineEvent.from_dict(data) for data in sample_events]
        
        # Events should be orderable by timestamp
        sorted_events = sorted(events, key=lambda e: e.timestamp)
        
        assert sorted_events[0].id == "event_001"
        assert sorted_events[-1].id == "event_003"


class TestTimelineBuilder:
    """Test TimelineBuilder functionality."""
    
    def test_timeline_builder_init(self, timeline_builder):
        """Test TimelineBuilder initialization."""
        assert hasattr(timeline_builder, 'events')
        assert len(timeline_builder.events) == 0
    
    def test_add_event(self, timeline_builder, sample_events):
        """Test adding events to timeline."""
        event_data = sample_events[0]
        
        result = timeline_builder.add_event(event_data)
        
        assert result is True
        assert len(timeline_builder.events) == 1
        assert timeline_builder.events[0].id == "event_001"
    
    def test_add_multiple_events(self, timeline_builder, sample_events):
        """Test adding multiple events."""
        for event_data in sample_events:
            timeline_builder.add_event(event_data)
        
        assert len(timeline_builder.events) == 3
        # Events should be sorted by timestamp
        assert timeline_builder.events[0].id == "event_001"
        assert timeline_builder.events[-1].id == "event_003"
    
    def test_add_duplicate_event(self, timeline_builder, sample_events):
        """Test adding duplicate event ID."""
        event_data = sample_events[0]
        
        # Add event first time
        result1 = timeline_builder.add_event(event_data)
        assert result1 is True
        
        # Try to add same event ID again
        result2 = timeline_builder.add_event(event_data, allow_duplicate=False)
        assert result2 is False
        assert len(timeline_builder.events) == 1
    
    def test_remove_event(self, timeline_builder, sample_events):
        """Test removing events from timeline."""
        # Add events
        for event_data in sample_events:
            timeline_builder.add_event(event_data)
        
        # Remove middle event
        result = timeline_builder.remove_event("event_002")
        
        assert result is True
        assert len(timeline_builder.events) == 2
        event_ids = [event.id for event in timeline_builder.events]
        assert "event_002" not in event_ids
    
    def test_get_event(self, timeline_builder, sample_events):
        """Test getting specific event."""
        timeline_builder.add_event(sample_events[0])
        
        event = timeline_builder.get_event("event_001")
        
        assert event is not None
        assert event.title == "Adventure Begins"
    
    def test_get_event_not_found(self, timeline_builder):
        """Test getting non-existent event."""
        event = timeline_builder.get_event("nonexistent_event")
        
        assert event is None
    
    def test_update_event(self, timeline_builder, sample_events):
        """Test updating existing event."""
        timeline_builder.add_event(sample_events[0])
        
        updated_data = {
            "id": "event_001",
            "title": "Updated Adventure Begins",
            "description": "Updated description"
        }
        
        result = timeline_builder.update_event("event_001", updated_data)
        
        assert result is True
        event = timeline_builder.get_event("event_001")
        assert event.title == "Updated Adventure Begins"
    
    def test_get_events_by_character(self, timeline_builder, sample_events):
        """Test getting events by character involvement."""
        for event_data in sample_events:
            timeline_builder.add_event(event_data)
        
        alice_events = timeline_builder.get_events_by_character("Alice")
        bob_events = timeline_builder.get_events_by_character("Bob")
        
        assert len(alice_events) == 3  # Alice in all events
        assert len(bob_events) == 1    # Bob only in one event
    
    def test_get_events_by_location(self, timeline_builder, sample_events):
        """Test getting events by location."""
        for event_data in sample_events:
            timeline_builder.add_event(event_data)
        
        village_events = timeline_builder.get_events_by_location("village")
        forest_events = timeline_builder.get_events_by_location("forest_entrance")
        
        assert len(village_events) == 1
        assert len(forest_events) == 1
    
    def test_get_events_by_type(self, timeline_builder, sample_events):
        """Test getting events by type."""
        for event_data in sample_events:
            timeline_builder.add_event(event_data)
        
        encounter_events = timeline_builder.get_events_by_type("encounter")
        conflict_events = timeline_builder.get_events_by_type("conflict")
        
        assert len(encounter_events) == 1
        assert len(conflict_events) == 1
    
    def test_get_events_in_timeframe(self, timeline_builder, sample_events):
        """Test getting events within specific timeframe."""
        for event_data in sample_events:
            timeline_builder.add_event(event_data)
        
        # Get events between 9 AM and 1 PM
        start_time = "2024-01-01T09:00:00Z"
        end_time = "2024-01-01T13:00:00Z"
        
        timeframe_events = timeline_builder.get_events_in_timeframe(start_time, end_time)
        
        assert len(timeframe_events) == 1  # Only event_002 in this range
        assert timeframe_events[0].id == "event_002"


class TestTimelineAnalysis:
    """Test timeline analysis functionality."""
    
    def test_timeline_continuity_check(self, timeline_builder, sample_events):
        """Test timeline continuity analysis."""
        for event_data in sample_events:
            timeline_builder.add_event(event_data)
        
        continuity_report = timeline_builder.check_continuity()
        
        assert isinstance(continuity_report, dict)
        assert "gaps" in continuity_report
        assert "overlaps" in continuity_report
        assert "consistency_score" in continuity_report
    
    def test_character_arc_analysis(self, timeline_builder, sample_events):
        """Test character arc analysis."""
        for event_data in sample_events:
            timeline_builder.add_event(event_data)
        
        alice_arc = timeline_builder.analyze_character_arc("Alice")
        
        assert isinstance(alice_arc, dict)
        assert "event_count" in alice_arc
        assert "locations_visited" in alice_arc
        assert "timeline_span" in alice_arc
        assert alice_arc["event_count"] == 3
    
    def test_location_timeline(self, timeline_builder, sample_events):
        """Test location-based timeline analysis."""
        for event_data in sample_events:
            timeline_builder.add_event(event_data)
        
        location_timeline = timeline_builder.get_location_timeline()
        
        assert isinstance(location_timeline, dict)
        assert "village" in location_timeline
        assert "forest_entrance" in location_timeline
        assert "deep_forest" in location_timeline
    
    def test_timeline_statistics(self, timeline_builder, sample_events):
        """Test timeline statistics generation."""
        for event_data in sample_events:
            timeline_builder.add_event(event_data)
        
        stats = timeline_builder.get_statistics()
        
        assert isinstance(stats, dict)
        assert "total_events" in stats
        assert "unique_characters" in stats
        assert "unique_locations" in stats
        assert "timeline_duration" in stats
        assert stats["total_events"] == 3


class TestTimelineFunctions:
    """Test standalone timeline functions."""
    
    def test_build_timeline_from_scenes(self, sample_events):
        """Test building timeline from scene data."""
        scene_data = [
            {
                "scene_id": "scene_001",
                "timestamp": "2024-01-01T08:00:00Z",
                "characters_involved": ["Alice"],
                "location": "village",
                "summary": "Adventure begins"
            },
            {
                "scene_id": "scene_002", 
                "timestamp": "2024-01-01T10:00:00Z",
                "characters_involved": ["Alice", "Bob"],
                "location": "forest",
                "summary": "Meeting Bob"
            }
        ]
        
        timeline = build_timeline(scene_data)
        
        assert isinstance(timeline, TimelineBuilder)
        assert len(timeline.events) == 2
    
    def test_validate_timeline_valid(self, timeline_builder, sample_events):
        """Test timeline validation with valid timeline."""
        for event_data in sample_events:
            timeline_builder.add_event(event_data)
        
        validation_result = validate_timeline(timeline_builder)
        
        assert validation_result["valid"] is True
        assert len(validation_result["errors"]) == 0
    
    def test_validate_timeline_invalid(self, timeline_builder):
        """Test timeline validation with invalid timeline."""
        # Add events with inconsistent data
        invalid_events = [
            {
                "id": "event_001",
                "timestamp": "2024-01-01T10:00:00Z",
                "type": "test",
                "title": "Event 1",
                "characters": ["Alice"],
                "location": "location_a"
            },
            {
                "id": "event_002",
                "timestamp": "2024-01-01T09:00:00Z",  # Earlier timestamp but later event
                "type": "test", 
                "title": "Event 2",
                "characters": ["Alice"],
                "location": "location_b"  # Character teleported
            }
        ]
        
        for event_data in invalid_events:
            timeline_builder.add_event(event_data)
        
        validation_result = validate_timeline(timeline_builder)
        
        assert validation_result["valid"] is False
        assert len(validation_result["errors"]) > 0
    
    def test_merge_timelines(self, sample_events):
        """Test merging multiple timelines."""
        # Create two timelines
        timeline1 = TimelineBuilder()
        timeline2 = TimelineBuilder()
        
        timeline1.add_event(sample_events[0])
        timeline1.add_event(sample_events[1])
        
        timeline2.add_event(sample_events[2])
        timeline2.add_event({
            "id": "event_004",
            "timestamp": "2024-01-01T16:00:00Z",
            "type": "resolution",
            "title": "Victory",
            "characters": ["Alice"]
        })
        
        merged_timeline = merge_timelines([timeline1, timeline2])
        
        assert isinstance(merged_timeline, TimelineBuilder)
        assert len(merged_timeline.events) == 4
        # Should be sorted by timestamp
        assert merged_timeline.events[0].id == "event_001"
        assert merged_timeline.events[-1].id == "event_004"
    
    def test_export_timeline_json(self, timeline_builder, sample_events):
        """Test exporting timeline as JSON."""
        for event_data in sample_events:
            timeline_builder.add_event(event_data)
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            export_file = f.name
        
        result = export_timeline(timeline_builder, export_file, format="json")
        
        assert result is True
        
        # Verify export content
        import json
        with open(export_file, 'r') as f:
            exported_data = json.load(f)
        
        assert len(exported_data) == 3
        assert exported_data[0]["id"] == "event_001"
        
        # Cleanup
        Path(export_file).unlink()
    
    def test_export_timeline_csv(self, timeline_builder, sample_events):
        """Test exporting timeline as CSV."""
        for event_data in sample_events:
            timeline_builder.add_event(event_data)
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            export_file = f.name
        
        result = export_timeline(timeline_builder, export_file, format="csv")
        
        assert result is True
        
        # Verify export content
        with open(export_file, 'r') as f:
            content = f.read()
        
        assert "event_001" in content
        assert "Adventure Begins" in content
        
        # Cleanup
        Path(export_file).unlink()


class TestTimelineVisualization:
    """Test timeline visualization functionality."""
    
    def test_generate_timeline_html(self, timeline_builder, sample_events):
        """Test generating HTML timeline visualization."""
        for event_data in sample_events:
            timeline_builder.add_event(event_data)
        
        html_content = timeline_builder.generate_html_timeline()
        
        assert isinstance(html_content, str)
        assert "<html>" in html_content
        assert "Adventure Begins" in html_content
        assert "Meeting Bob" in html_content
    
    def test_generate_character_timeline(self, timeline_builder, sample_events):
        """Test generating character-specific timeline."""
        for event_data in sample_events:
            timeline_builder.add_event(event_data)
        
        alice_timeline = timeline_builder.generate_character_timeline("Alice")
        
        assert isinstance(alice_timeline, str)
        assert "Alice" in alice_timeline
        # Should include all Alice's events
        assert len(alice_timeline.split('\n')) >= 3
    
    def test_generate_location_timeline(self, timeline_builder, sample_events):
        """Test generating location-based timeline."""
        for event_data in sample_events:
            timeline_builder.add_event(event_data)
        
        location_timeline = timeline_builder.generate_location_timeline()
        
        assert isinstance(location_timeline, dict)
        assert "village" in location_timeline
        assert "forest_entrance" in location_timeline


class TestTimelineConflictResolution:
    """Test timeline conflict resolution."""
    
    def test_detect_temporal_conflicts(self, timeline_builder):
        """Test detecting temporal conflicts in timeline."""
        # Create conflicting events
        conflicting_events = [
            {
                "id": "event_001",
                "timestamp": "2024-01-01T10:00:00Z",
                "type": "action",
                "title": "Alice in Village",
                "characters": ["Alice"],
                "location": "village"
            },
            {
                "id": "event_002",
                "timestamp": "2024-01-01T10:05:00Z",  # Only 5 minutes later
                "type": "action",
                "title": "Alice in Forest",
                "characters": ["Alice"],
                "location": "distant_forest"  # Too far to travel in 5 minutes
            }
        ]
        
        for event_data in conflicting_events:
            timeline_builder.add_event(event_data)
        
        conflicts = timeline_builder.detect_conflicts()
        
        assert isinstance(conflicts, list)
        assert len(conflicts) > 0
        assert "temporal" in conflicts[0]["type"].lower()
    
    def test_auto_resolve_conflicts(self, timeline_builder):
        """Test automatic conflict resolution."""
        # Create events with minor timing conflicts
        events_with_conflicts = [
            {
                "id": "event_001",
                "timestamp": "2024-01-01T10:00:00Z",
                "type": "dialogue",
                "title": "Conversation Start",
                "characters": ["Alice", "Bob"],
                "location": "tavern"
            },
            {
                "id": "event_002",
                "timestamp": "2024-01-01T10:00:00Z",  # Same timestamp
                "type": "dialogue",
                "title": "Conversation Continue", 
                "characters": ["Alice", "Bob"],
                "location": "tavern"
            }
        ]
        
        for event_data in events_with_conflicts:
            timeline_builder.add_event(event_data)
        
        resolved_count = timeline_builder.auto_resolve_conflicts()
        
        assert isinstance(resolved_count, int)
        assert resolved_count >= 0
        
        # Check that events now have different timestamps
        events = timeline_builder.get_all_events()
        timestamps = [event.timestamp for event in events]
        assert len(set(timestamps)) == len(timestamps)  # All unique


class TestTimelineIntegration:
    """Test timeline integration with other components."""
    
    def test_timeline_from_memory(self, timeline_builder):
        """Test building timeline from memory data."""
        memory_data = {
            "recent_events": [
                {
                    "scene": "scene_001",
                    "timestamp": "2024-01-01T08:00:00Z",
                    "description": "Alice begins her adventure",
                    "characters_involved": ["Alice"],
                    "location": "village"
                },
                {
                    "scene": "scene_002",
                    "timestamp": "2024-01-01T10:00:00Z", 
                    "description": "Alice meets Bob",
                    "characters_involved": ["Alice", "Bob"],
                    "location": "forest"
                }
            ]
        }
        
        timeline_builder.build_from_memory(memory_data)
        
        assert len(timeline_builder.events) == 2
        assert timeline_builder.events[0].characters == ["Alice"]
    
    def test_timeline_to_memory_context(self, timeline_builder, sample_events):
        """Test converting timeline to memory context."""
        for event_data in sample_events:
            timeline_builder.add_event(event_data)
        
        memory_context = timeline_builder.to_memory_context(limit=2)
        
        assert isinstance(memory_context, dict)
        assert "recent_events" in memory_context
        assert len(memory_context["recent_events"]) <= 2
    
    def test_timeline_scene_integration(self, timeline_builder):
        """Test timeline integration with scene data."""
        scene_sequence = [
            {"scene_id": "scene_001", "timestamp": "2024-01-01T08:00:00Z"},
            {"scene_id": "scene_002", "timestamp": "2024-01-01T10:00:00Z"},
            {"scene_id": "scene_003", "timestamp": "2024-01-01T12:00:00Z"}
        ]
        
        timeline_builder.integrate_scene_sequence(scene_sequence)
        
        assert len(timeline_builder.events) == 3
        # Should maintain chronological order
        assert timeline_builder.events[0].scene_id == "scene_001"
        assert timeline_builder.events[-1].scene_id == "scene_003"


if __name__ == "__main__":
    pytest.main([__file__])
