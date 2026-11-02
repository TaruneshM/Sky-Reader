import asyncio
from backend.agent.executor import execute_tool


async def main():
    latitude = 30.32443
    longitude = 78.03392

    current = await execute_tool(
        "get_current_weather",
        {
            "latitude": latitude,
            "longitude": longitude
        }
    )

    print("CURRENT WEATHER:")
    print(current)

    forecast = await execute_tool(
        "get_hourly_forecast",
        {
            "latitude": latitude,
            "longitude": longitude
        }
    )

    print("HOURLY FORECAST:")
    print(forecast)


if __name__ == "__main__":
    asyncio.run(main())