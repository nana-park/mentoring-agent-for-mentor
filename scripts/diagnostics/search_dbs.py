# Direct-file execution support; prefer python -m scripts.<group>.<name>.
if __package__ in (None, ""):
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import os
import asyncio
from mentoring.config import load_environment
from mentoring.integrations.notion import NotionAPIClient
import httpx

async def main():
    load_environment()
    token = os.getenv("NOTION_TOKEN")
    
    url = "https://api.notion.com/v1/search"
    headers = {
        "Authorization": f"Bearer {token}",
        "Notion-Version": "2022-06-28"
    }
    payload = {
        "filter": {
            "value": "database",
            "property": "object"
        }
    }
    
    async with httpx.AsyncClient() as http:
        r = await http.post(url, headers=headers, json=payload)
        data = r.json()
        
        for db in data.get("results", []):
            title = db.get("title", [{}])[0].get("plain_text", "Unknown") if db.get("title") else "Unknown"
            print(f"ID: {db['id'].replace('-', '')} | Title: {title}")
            print("  Properties:", list(db.get("properties", {}).keys()))
            print("-" * 40)

if __name__ == "__main__":
    asyncio.run(main())
