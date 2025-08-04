"""
Debug the specific legacy compatibility issue
"""

import sys
import traceback

def debug_legacy_compatibility():
    """Debug the legacy compatibility test to find the exact issue."""
    try:
        print("🔍 Debugging Legacy Compatibility...")
        
        from core.character_management import CharacterData
        
        # Test with legacy-style data (simplified)
        legacy_data = {
            'character_id': 'legacy_001',
            'name': 'Legacy Character',
            'description': 'A character from the old system',
            'stats': {
                'strength': 14,
                'intelligence': 16,
                'charisma': 12,
                'perception': 15
            },
            'relationships': {
                'ally_001': {'type': 'friend', 'trust_level': 0.8},
                'enemy_001': {'type': 'rival', 'trust_level': 0.2}
            }
        }
        
        print(f"   📋 Legacy data structure: {list(legacy_data.keys())}")
        
        # Create CharacterData from legacy format
        character = CharacterData(
            character_id=legacy_data['character_id'],
            name=legacy_data['name'],
            description=legacy_data['description']
        )
        
        print(f"   ✅ CharacterData created: {character.name}")
        
        # Set component data from legacy structure (step by step)
        print("   🔧 Setting component data...")
        
        # Stats
        character.set_component_data('stats', legacy_data['stats'])
        print(f"   ✅ Stats set: {legacy_data['stats']}")
        
        # Interactions
        interactions_data = {'relationships': legacy_data['relationships']}
        character.set_component_data('interactions', interactions_data)
        print(f"   ✅ Interactions set: {len(legacy_data['relationships'])} relationships")
        
        # Test serialization
        print("   🔧 Testing serialization...")
        exported_data = character.to_dict()
        print(f"   ✅ Exported data keys: {list(exported_data.keys())}")
        
        # Test deserialization
        print("   🔧 Testing deserialization...")
        imported_character = CharacterData.from_dict(exported_data)
        print(f"   ✅ Imported character: {imported_character.name}")
        
        # Test component data preservation (step by step)
        print("   🔧 Testing component data preservation...")
        
        imported_stats = imported_character.get_component_data('stats')
        print(f"   📊 Imported stats: {imported_stats}")
        
        imported_relationships = imported_character.get_component_data('interactions')
        print(f"   📊 Imported relationships: {imported_relationships}")
        
        # Check specific data access that was failing
        if imported_stats and 'strength' in imported_stats:
            strength_value = imported_stats['strength']
            print(f"   ✅ Strength value: {strength_value}")
            assert strength_value == 14
        else:
            print(f"   ⚠️  Stats structure: {imported_stats}")
        
        if imported_relationships and 'relationships' in imported_relationships:
            relationships = imported_relationships['relationships']
            print(f"   📊 Relationships structure: {relationships}")
            
            if 'ally_001' in relationships:
                ally_data = relationships['ally_001']
                print(f"   📊 Ally data: {ally_data}")
                
                if 'trust_level' in ally_data:
                    trust_level = ally_data['trust_level']
                    print(f"   ✅ Trust level: {trust_level}")
                    assert trust_level == 0.8
                else:
                    print(f"   ⚠️  Ally data keys: {list(ally_data.keys())}")
            else:
                print(f"   ⚠️  Available relationships: {list(relationships.keys())}")
        else:
            print(f"   ⚠️  Relationships structure: {imported_relationships}")
        
        print("   ✅ Legacy compatibility debugging complete!")
        return True
        
    except Exception as e:
        print(f"   ❌ Legacy compatibility error: {e}")
        traceback.print_exc()
        return False

if __name__ == "__main__":
    debug_legacy_compatibility()
