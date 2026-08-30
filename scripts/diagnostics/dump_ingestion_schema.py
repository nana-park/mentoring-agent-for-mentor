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
    
    # We need to find the Ingestion History DB ID first.
    # It's a child of the Course page. Let's just find the first course.
    global_course_db_id = "358c919e-34d1-80f0-9573-edb4e42a261a" 
    
    response = await mcp.client.post(f"/databases/{global_course_db_id}/query")
    courses = response.json().get("results", [])
    if not courses:
        print("No courses found.")
        return
        
    course_page_id = courses[0]["id"]
    
    blocks_response = await mcp.client.get(f"/blocks/{course_page_id}/children")
    blocks = blocks_response.json().get("results", [])
    
    ingestion_db_id = None
    for b in blocks:
        if b["type"] == "child_database":
            title = b["child_database"]["title"]
            if "Ingestion History" in title:
                ingestion_db_id = b["id"]
                break
                
    if not ingestion_db_id:
        print("Ingestion History DB not found.")
        return
        
    print(f"Found Ingestion History DB ID: {ingestion_db_id}")
    
    db_response = await mcp.client.get(f"/databases/{ingestion_db_id}")
    props = db_response.json().get("properties", {})
    
    with open(diagnostic_output("ingestion_schema.txt"), "w", encoding="utf-8") as f:
        for prop_name, prop_data in props.items():
            f.write(f"Property: '{prop_name}' | Type: {prop_data['type']}\n")

if __name__ == "__main__":
    asyncio.run(main())
