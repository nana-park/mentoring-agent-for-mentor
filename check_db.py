import os
import asyncio
from dotenv import load_dotenv
import httpx

async def main():
    token = os.getenv('NOTION_TOKEN')
    url = "https://api.notion.com/v1/databases/358c919e-34d1-80f0-9573-edb4e42a261a/query"
    headers = {
        "Authorization": f"Bearer {token}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json"
    }
    async with httpx.AsyncClient(timeout=30.0) as client:
        res = await client.post(url, headers=headers)
        data = res.json()
        print(f"Status: {res.status_code}")
        for page in data.get("results", []):
            props = page["properties"]
            title = props.get("강의명", {}).get("title", [{}])[0].get("plain_text", "Unknown")
            url_prop = props.get("과제제출 여부 URL", {}).get("url", "No URL")
            print(f"Course: {title}")
            print(f"URL: {url_prop}")

if __name__ == "__main__":
    asyncio.run(main())
