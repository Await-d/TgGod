#!/usr/bin/env python3
"""
Test script to simulate monthly sync progress updates
"""
import asyncio
import aiohttp
import json
import time

async def test_monthly_sync():
    """Test monthly sync by calling the API and monitoring progress"""
    
    # Prepare the monthly sync request
    group_id = 1  # From the groups list we retrieved
    months_data = [
        {"year": 2025, "month": 5},
        {"year": 2025, "month": 6},
        {"year": 2025, "month": 7}
    ]
    
    print(f"🔄 Testing monthly sync for group {group_id}")
    print(f"📅 Months to sync: {months_data}")
    
    # Call the monthly sync API
    url = f"http://localhost:8000/api/telegram/groups/{group_id}/sync-monthly"
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(url, json={"months": months_data}) as response:
                if response.status == 200:
                    result = await response.json()
                    print(f"✅ Monthly sync started: {result}")
                    return True
                else:
                    error_text = await response.text()
                    print(f"❌ Monthly sync failed: {response.status} - {error_text}")
                    return False
        except Exception as e:
            print(f"❌ API call failed: {e}")
            return False

if __name__ == "__main__":
    success = asyncio.run(test_monthly_sync())
    if success:
        print("✅ Monthly sync test initiated - check WebSocket for progress updates")
    else:
        print("❌ Monthly sync test failed")