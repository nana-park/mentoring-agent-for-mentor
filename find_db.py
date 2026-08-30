import asyncio
import os
import json
from dotenv import load_dotenv
from notion_api import NotionAPIClient

async def main():
    load_dotenv()
    token = os.getenv("NOTION_TOKEN")
    mcp = NotionAPIClient(token)
    
    payload = {
        "query": "Email Anaylsis Error Queue",
        "filter": {
            "value": "database",
            "property": "object"
        }
    }
    
    response = await mcp.client.post("/search", json=payload)
    data = response.json()
    
    for res in data.get("results", []):
        title = res.get("title", [{}])[0].get("plain_text", "")
        print(f"Found DB: {title} | ID: {res['id']}")

if __name__ == "__main__":
    asyncio.run(main())
