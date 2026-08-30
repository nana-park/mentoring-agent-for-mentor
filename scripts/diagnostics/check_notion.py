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
    
    with open(diagnostic_output("db_schema_output.txt"), "w", encoding="utf-8") as f:
        f.write("Finding DBs in Course Page 374c919e34d1808d9cb3f3031085e440\n")
        children = await mcp.get_block_children("374c919e34d1808d9cb3f3031085e440")
        
        mentor_db_id = None
        for block in children.get("results", []):
            if block["type"] == "child_database":
                title = block["child_database"]["title"]
                f.write(f"Found DB: {title} ({block['id']})\n")
                if "Mentoring Sessions" in title or "멘토링" in title:
                    mentor_db_id = block["id"]
                    
        if mentor_db_id:
            f.write(f"\nQuerying Mentoring Sessions DB schema: {mentor_db_id}\n")
            response = await mcp.client.get(f"/databases/{mentor_db_id}")
            response.raise_for_status()
            props = response.json().get("properties", {})
            for prop_name, prop_data in props.items():
                f.write(f"Property: '{prop_name}' | Type: {prop_data['type']}\n")
                if prop_data['type'] == 'title':
                    f.write(f"  -> THIS IS THE TITLE PROPERTY: '{prop_name}'\n")

if __name__ == "__main__":
    asyncio.run(main())
