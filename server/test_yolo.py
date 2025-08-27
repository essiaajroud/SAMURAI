#!/usr/bin/env python3
"""
test_yolo.py - Test script for YOLO integration and server endpoints.
Runs health, model, video list, and streaming status checks.
"""

import os
import sys
import requests
import json
import time

# --- Test Server Health ---
def test_server_health():
    """Test server health endpoint."""
    try:
        response = requests.get('http://localhost:5000/api/health')
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Server online: {data}")
            return data.get('yolo_available', False)
        else:
            print(f"❌ Server not accessible: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Connection error: {e}")
        return False

# --- Test YOLO Model ---
def test_yolo_model():
    """Test YOLO model endpoint."""
    try:
        response = requests.get('http://localhost:5000/api/yolo/model')
        if response.status_code == 200:
            data = response.json()
            print(f"✅ YOLO model: {data}")
            return True
        else:
            print(f"❌ YOLO model error: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ YOLO model test error: {e}")
        return False

# --- Test Videos List ---
def test_videos_list():
    """Test available videos endpoint."""
    try:
        response = requests.get('http://localhost:5000/api/yolo/videos')
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Available videos: {data}")
            return data.get('videos', [])
        else:
            print(f"❌ Videos list error: {response.status_code}")
            return []
    except Exception as e:
        print(f"❌ Videos test error: {e}")
        return []

# --- Test Streaming Status ---
def test_streaming_status():
    """Test streaming status endpoint."""
    try:
        response = requests.get('http://localhost:5000/api/yolo/stream/status')
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Streaming status: {data}")
            return data
        else:
            print(f"❌ Streaming status error: {response.status_code}")
            return None
    except Exception as e:
        print(f"❌ Streaming test error: {e}")
        return None

# --- Main Test Runner ---
def main():
    """Main test function."""
    print("🧪 YOLO Integration Test")
    print("=" * 50)
    # Test 1: Server health
    print("\n1. Testing server health...")
    yolo_available = test_server_health()
    if not yolo_available:
        print("⚠️ YOLO is not available on the server.")
        return
    # Test 2: YOLO model
    print("\n2. Testing YOLO model...")
    test_yolo_model()
    
    # Test 4: Streaming status
    print("\n3. Testing streaming status...")
    test_streaming_status()
    print("\n✅ Tests completed.")

if __name__ == "__main__":
    main() 