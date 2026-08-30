# Direct-file execution support; prefer python -m scripts.<group>.<name>.
if __package__ in (None, ""):
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import asyncio
import os
import json
from mentoring.config import load_environment
from mentoring.integrations.notion import NotionAPIClient

async def main():
    load_environment()
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
