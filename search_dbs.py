import os
import asyncio
from dotenv import load_dotenv
from notion_api import NotionAPIClient
import httpx

async def main():
    load_dotenv(r"C:\Users\user\Documents\antigravity\mysterious-lavoisier\tools\mentoring\.env")
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
