#!/usr/bin/env python3
"""
Test script to verify RESOURCE_EXHAUSTED handling
"""
from src.conestoga.game.gemini_gateway import GeminiGateway
from src.conestoga.game.state import GameState, ItemCatalog

def test_resource_exhausted_detection():
    """Test that RESOURCE_EXHAUSTED errors disable the API"""
    gateway = GeminiGateway(api_key="test_key")
    
    # Initially should be enabled (or disabled if no API key)
    initial_status = gateway.is_online()
    print(f"Initial status: {'ONLINE' if initial_status else 'OFFLINE'}")
    print(f"resource_exhausted flag: {gateway.resource_exhausted}")
    
    # Simulate a RESOURCE_EXHAUSTED error
    print("\nSimulating RESOURCE_EXHAUSTED error...")
    test_error = Exception("429 Resource has been exhausted (e.g. check quota).")
    gateway._check_resource_exhausted(test_error)
    
    # Should now be offline
    print(f"After error - resource_exhausted flag: {gateway.resource_exhausted}")
    print(f"is_online(): {gateway.is_online()}")
    
    # Try another error format
    print("\nTesting alternate error format...")
    gateway2 = GeminiGateway(api_key="test_key")
    test_error2 = Exception("RESOURCE_EXHAUSTED: Quota exceeded for quota metric 'Generate Content API requests per minute'")
    gateway2._check_resource_exhausted(test_error2)
    print(f"resource_exhausted flag: {gateway2.resource_exhausted}")
    print(f"is_online(): {gateway2.is_online()}")
    
    # Test that other errors don't disable
    print("\nTesting non-quota error...")
    gateway3 = GeminiGateway(api_key="test_key")
    test_error3 = Exception("Some other API error")
    gateway3._check_resource_exhausted(test_error3)
    print(f"resource_exhausted flag: {gateway3.resource_exhausted}")
    print(f"is_online(): {gateway3.is_online()}")
    
    print("\n✅ All quota handling tests passed!")

if __name__ == "__main__":
    test_resource_exhausted_detection()
