import httpx
import asyncio

async def test_cors():
    async with httpx.AsyncClient() as client:
        # Test preflight OPTIONS request
        print("Testing CORS preflight...")
        try:
            response = await client.options(
                "https://mpg-mart-buried-displayed.trycloudflare.com/health",
                headers={
                    "Origin": "https://ed-sensor-dashboard.vercel.app",
                    "Access-Control-Request-Method": "GET",
                    "Access-Control-Request-Headers": "content-type"
                }
            )
            print(f"OPTIONS Status: {response.status_code}")
            print(f"Headers: {dict(response.headers)}")
        except Exception as e:
            print(f"OPTIONS Error: {e}")
        
        # Test actual GET request
        print("\nTesting GET request...")
        try:
            response = await client.get(
                "https://mpg-mart-buried-displayed.trycloudflare.com/health",
                headers={
                    "Origin": "https://ed-sensor-dashboard.vercel.app"
                }
            )
            print(f"GET Status: {response.status_code}")
            print(f"CORS Headers:")
            for k, v in response.headers.items():
                if "access-control" in k.lower() or "origin" in k.lower():
                    print(f"  {k}: {v}")
            print(f"Body: {response.text}")
        except Exception as e:
            print(f"GET Error: {e}")

asyncio.run(test_cors())
