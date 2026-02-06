#!/usr/bin/env python3
"""
Test Script for Intelligent LangGraph Agent
Tests automatic tool routing with various queries
"""
import asyncio
import httpx
import sys
from typing import List, Dict


class AgentTester:
    """Test the intelligent agent with various queries"""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.test_results = []
    
    async def test_query(self, query: str, expected_tool: str = None):
        """Test a single query"""
        print(f"\n{'='*70}")
        print(f"🧪 Testing Query: {query}")
        print(f"{'='*70}")
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.post(
                    f"{self.base_url}/chat-agent",
                    json={
                        "message": query,
                        "server_name": "agricultural-server"
                    }
                )
                
                if response.status_code == 200:
                    result = response.json()
                    print(f"✅ Status: Success")
                    print(f"📊 Response Preview:")
                    print(f"   {result['response'][:200]}...")
                    
                    self.test_results.append({
                        "query": query,
                        "status": "success",
                        "expected_tool": expected_tool
                    })
                else:
                    print(f"❌ Status: {response.status_code}")
                    print(f"   {response.text}")
                    self.test_results.append({
                        "query": query,
                        "status": "failed",
                        "error": response.text
                    })
                    
            except Exception as e:
                print(f"❌ Error: {str(e)}")
                self.test_results.append({
                    "query": query,
                    "status": "error",
                    "error": str(e)
                })
    
    async def run_all_tests(self):
        """Run comprehensive test suite"""
        print("\n" + "="*70)
        print("🚀 INTELLIGENT AGENT TEST SUITE")
        print("="*70)
        
        # Test 1: Agricultural Queries
        print("\n📦 Category: AGRICULTURAL QUERIES")
        await self.test_query(
            "What pesticides should I use for organic tomato farming?",
            expected_tool="get_pesticide_seed_info"
        )
        
        await self.test_query(
            "Tell me about wheat seeds",
            expected_tool="get_pesticide_seed_info"
        )
        
        await self.test_query(
            "How to deal with pests in my garden?",
            expected_tool="get_pesticide_seed_info"
        )
        
        await self.test_query(
            "Best fertilizer for corn crops",
            expected_tool="get_pesticide_seed_info"
        )
        
        # Test 2: Weather Queries
        print("\n📦 Category: WEATHER QUERIES")
        await self.test_query(
            "What's the weather in Tokyo?",
            expected_tool="get_current_weather"
        )
        
        await self.test_query(
            "Temperature in Paris today",
            expected_tool="get_current_weather"
        )
        
        await self.test_query(
            "Is it raining in London?",
            expected_tool="get_current_weather"
        )
        
        # Test 3: Blog/Content Queries
        print("\n📦 Category: BLOG/CONTENT QUERIES")
        await self.test_query(
            "Show me 5 blog posts",
            expected_tool="get_placeholder_posts"
        )
        
        await self.test_query(
            "Get me 3 articles",
            expected_tool="get_placeholder_posts"
        )
        
        # Test 4: Edge Cases
        print("\n📦 Category: EDGE CASES")
        await self.test_query(
            "Hello, how are you?",
            expected_tool="get_pesticide_seed_info"  # Should default
        )
        
        await self.test_query(
            "Tell me something interesting",
            expected_tool="get_pesticide_seed_info"  # Should default
        )
        
        # Print Summary
        self.print_summary()
    
    def print_summary(self):
        """Print test results summary"""
        print("\n" + "="*70)
        print("📊 TEST RESULTS SUMMARY")
        print("="*70)
        
        total = len(self.test_results)
        success = len([r for r in self.test_results if r["status"] == "success"])
        failed = len([r for r in self.test_results if r["status"] == "failed"])
        errors = len([r for r in self.test_results if r["status"] == "error"])
        
        print(f"\n📈 Statistics:")
        print(f"   Total Tests: {total}")
        print(f"   ✅ Successful: {success}")
        print(f"   ❌ Failed: {failed}")
        print(f"   ⚠️  Errors: {errors}")
        print(f"   Success Rate: {(success/total*100):.1f}%")
        
        if failed > 0 or errors > 0:
            print(f"\n❌ Failed/Error Tests:")
            for result in self.test_results:
                if result["status"] != "success":
                    print(f"   • {result['query']}")
                    print(f"     Reason: {result.get('error', 'Unknown')}")


async def test_api_availability():
    """Test if the API is available"""
    async with httpx.AsyncClient(timeout=5.0) as client:
        try:
            response = await client.get("http://localhost:8000/")
            if response.status_code == 200:
                data = response.json()
                print("✅ API is online")
                print(f"   Agent Type: {data.get('agent_type', 'Unknown')}")
                print(f"   Features: {', '.join(data.get('features', []))}")
                return True
            else:
                print(f"⚠️  API returned status {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Cannot connect to API: {str(e)}")
            return False


async def main():
    """Main entry point"""
    print("\n🔍 Checking API availability...")
    
    if not await test_api_availability():
        print("\n" + "="*70)
        print("❌ PREREQUISITES NOT MET")
        print("="*70)
        print("\nPlease ensure:")
        print("1. The server is running: python intelligent_mcp_server.py")
        print("2. The server is accessible at http://localhost:8000")
        print("3. config.json is properly configured")
        print("\nThen run this test script again.")
        sys.exit(1)
    
    print("\n✅ API is ready, starting tests...\n")
    
    tester = AgentTester()
    await tester.run_all_tests()
    
    print("\n" + "="*70)
    print("🎉 ALL TESTS COMPLETED")
    print("="*70)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⚠️  Tests interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Test suite failed: {str(e)}")
        sys.exit(1)