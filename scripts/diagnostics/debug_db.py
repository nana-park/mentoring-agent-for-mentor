# Direct-file execution support; prefer python -m scripts.<group>.<name>.
if __package__ in (None, ""):
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import os
import asyncio
from mentoring.config import load_environment
from mentoring.integrations.notion import NotionAPIClient

async def main():
    load_environment()
    token = os.getenv("NOTION_TOKEN")
    client = NotionAPIClient(token)
    
    # Courses DB ID from config
    db_id = "372c919e34d180bbaa44d7254b69bb71"
    
    try:
        # Get DB properties
        import httpx
        url = f"https://api.notion.com/v1/databases/{db_id}"
        headers = {
            "Authorization": f"Bearer {token}",
            "Notion-Version": "2022-06-28"
        }
        async with httpx.AsyncClient() as http:
            r = await http.get(url, headers=headers)
            db_info = r.json()
            print("DB Title:", db_info.get("title", [{}])[0].get("plain_text", "Unknown"))
            print("Properties:", list(db_info.get("properties", {}).keys()))
            
        # Query rows
        res = await client.query_database(db_id)
        print("\nRows in Courses DB:")
        for row in res.get("results", []):
            props = row["properties"]
            title_prop = next((p for p in props.values() if p["type"] == "title"), None)
            if title_prop and title_prop["title"]:
                print("-", title_prop["title"][0]["plain_text"])
            else:
                print("- Unknown Title")
    except Exception as e:
        print("Error:", e)
        
if __name__ == "__main__":
    asyncio.run(main())
