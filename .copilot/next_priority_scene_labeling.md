# 🔖 Scene Labeling + Bookmarking System

## 🎯 Goals
- Add support for optional `scene_label` field in scene logger
- Enable timeline view or export with labeled chapters
- Provide story navigation and organization capabilities
- Foundation for advanced story management features

## 📋 Implementation Plan

### Phase 1: Database Schema Enhancement
- [ ] Add `scene_label` field to scenes table
- [ ] Create bookmarks table for user-defined story markers
- [ ] Add migration support for existing stories
- [ ] Update database utilities for label management

### Phase 2: Scene Logger Integration
- [ ] Modify `scene_logger.py` to support optional scene labels
- [ ] Add label validation and sanitization
- [ ] Implement automatic label suggestions based on content
- [ ] Add bookmark creation and management functions

### Phase 3: Timeline and Navigation
- [ ] Create timeline view utilities
- [ ] Add chapter/section organization
- [ ] Implement label-based scene filtering
- [ ] Add story navigation helpers

### Phase 4: Export and Visualization
- [ ] Timeline export to structured formats (JSON, Markdown)
- [ ] Chapter-based story organization
- [ ] Bookmark-based navigation menu
- [ ] Scene label analytics and reporting

## 🔧 Technical Details

### Database Schema Updates
```sql
-- Add scene_label column to scenes table
ALTER TABLE scenes ADD COLUMN scene_label TEXT;

-- Create bookmarks table
CREATE TABLE bookmarks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    story_id TEXT NOT NULL,
    scene_id TEXT NOT NULL,
    label TEXT NOT NULL,
    description TEXT,
    bookmark_type TEXT DEFAULT 'user', -- 'user', 'auto', 'chapter'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata TEXT -- JSON for additional bookmark data
);

-- Create index for efficient label queries
CREATE INDEX idx_scenes_label ON scenes(scene_label);
CREATE INDEX idx_bookmarks_story ON bookmarks(story_id);
```

### File Structure
```
core/
├── scene_logger.py        # Enhanced with label support
├── bookmark_manager.py    # New: Bookmark management system
├── timeline_builder.py    # New: Timeline and navigation utilities
└── database.py           # Updated with bookmark schema

utilities/
├── story_timeline.py     # New: Timeline export utilities
└── label_suggestions.py  # New: Auto-labeling system

tests/
├── test_scene_labeling.py    # New: Scene label tests
├── test_bookmark_manager.py  # New: Bookmark system tests
└── test_timeline_builder.py  # New: Timeline utilities tests
```

## 🏗️ Implementation Benefits

### User Experience
- **Story Organization**: Users can create meaningful chapter breaks
- **Navigation**: Easy jumping between story sections
- **Progress Tracking**: Visual timeline of story development
- **Content Discovery**: Find specific scenes or story beats

### Developer Benefits
- **Foundation**: Sets up infrastructure for advanced story management
- **Testing**: Comprehensive test coverage for navigation features
- **Extensibility**: Bookmark system can support future features
- **Integration**: Works with existing rollback and memory systems

## 🎯 Success Criteria
- [ ] Scene labels can be added, edited, and removed
- [ ] Bookmarks provide reliable story navigation
- [ ] Timeline export generates useful story overviews
- [ ] System integrates seamlessly with existing scene logger
- [ ] Comprehensive test coverage for all labeling features
- [ ] Performance remains good with large story databases

## 🚀 Next Steps After Completion
This system will provide the foundation for:
- Publisher-friendly export features
- Advanced story management tools
- Story analytics and progression tracking
- Enhanced user interface development
- CLI time machine tooling

## 📊 Estimated Effort
- **Phase 1**: 1-2 days (Database schema and migration)
- **Phase 2**: 2-3 days (Scene logger integration)
- **Phase 3**: 2-3 days (Timeline and navigation)
- **Phase 4**: 1-2 days (Export and visualization)
- **Total**: ~6-10 days of development time

Ready to begin implementation!
