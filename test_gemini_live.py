#!/usr/bin/env python3
"""
Quick test script to verify Gemini API integration works
"""
from src.conestoga.game.gemini_gateway import GeminiGateway
from src.conestoga.game.state import GameState, ItemCatalog

def test_live_gemini():
    """Test actual Gemini API call"""
    gateway = GeminiGateway()
    
    print(f"Gateway enabled: {gateway.enabled}")
    print(f"Gateway online: {gateway.is_online()}")
    
    if not gateway.is_online():
        print("\n❌ Gemini API not available - check your GEMINI_API_KEY")
        return
    
    print("\n" + "="*60)
    print("Testing Event Generation")
    print("="*60)
    
    state = GameState()
    catalog = ItemCatalog()
    
    # Test event generation
    event = gateway.generate_event_draft(state, catalog, tier="minor")
    
    print(f"\n✓ Generated Event: {event.event_id}")
    print(f"Title: {event.title}")
    print(f"Narrative: {event.narrative}")
    print(f"\nChoices ({len(event.choices)}):")
    for choice in event.choices:
        print(f"  - [{choice.id}] {choice.text}")
    
    print("\n" + "="*60)
    print("Testing Resolution Generation")
    print("="*60)
    
    # Test resolution generation
    first_choice = event.choices[0]
    resolution = gateway.generate_event_resolution(event, first_choice.id, state)
    
    if resolution:
        print(f"\n✓ Generated Resolution for: {first_choice.text}")
        print(f"Outcome: {resolution.outcome.text}")
        print(f"\nEffects ({len(resolution.outcome.effects)}):")
        for effect in resolution.outcome.effects:
            print(f"  - {effect.operation.name}: target={effect.target}, value={effect.value}")
    else:
        print("\n✗ Failed to generate resolution")
    
    print("\n" + "="*60)
    print("✅ Gemini integration test complete!")
    print("="*60)

if __name__ == "__main__":
    test_live_gemini()
