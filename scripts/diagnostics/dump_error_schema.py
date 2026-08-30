# Direct-file execution support; prefer python -m scripts.<group>.<name>.
if __package__ in (None, ""):
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from mentoring.config import diagnostic_output
import asyncio
import os
import json
from mentoring.config import load_environment
from mentoring.integrations.notion import NotionAPIClient

async def main():
    load_environment()
    token = os.getenv("NOTION_TOKEN")
    mcp = NotionAPIClient(token)
    
    db_id = "374c919e-34d1-8040-ab19-d3ac7d73e526"
    
    response = await mcp.client.get(f"/databases/{db_id}")
    props = response.json().get("properties", {})
    
    with open(diagnostic_output("error_queue_schema.txt"), "w", encoding="utf-8") as f:
        for prop_name, prop_data in props.items():
            f.write(f"Property: '{prop_name}' | Type: {prop_data['type']}\n")

if __name__ == "__main__":
    asyncio.run(main())
