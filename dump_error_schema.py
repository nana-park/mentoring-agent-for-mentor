import asyncio
import os
import json
from dotenv import load_dotenv
from notion_api import NotionAPIClient

async def main():
    load_dotenv()
    token = os.getenv("NOTION_TOKEN")
    mcp = NotionAPIClient(token)
    
    db_id = "374c919e-34d1-8040-ab19-d3ac7d73e526"
    
    response = await mcp.client.get(f"/databases/{db_id}")
    props = response.json().get("properties", {})
    
    with open("error_queue_schema.txt", "w", encoding="utf-8") as f:
        for prop_name, prop_data in props.items():
            f.write(f"Property: '{prop_name}' | Type: {prop_data['type']}\n")

if __name__ == "__main__":
    asyncio.run(main())
