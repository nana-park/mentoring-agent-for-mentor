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
    
    # 1. Test Ingestion History Query
    ing_db_id = "374c919e-34d1-803b-8154-c00394102eb2"
    print("Testing Ingestion History query...")
    try:
        response = await mcp.query_database(
            database_id=ing_db_id,
            filter_payload={
                "and": [
                    {
                        "property": "Source ID",
                        "rich_text": {
                            "equals": "test_id"
                        }
                    }
                ]
            }
        )
        print("Ingestion History query SUCCESS")
    except Exception as e:
        print(f"Ingestion History query FAILED: {e}")
        
    # 2. Test Error Recovery Query
    print("\nTesting Error Recovery query...")
    queue_id = "374c919e-34d1-8040-ab19-d3ac7d73e526"
    try:
        response = await mcp.query_database(
            queue_id,
            filter_payload={
                "and": [
                    {
                        "property": "Human Feedback",
                        "rich_text": {"is_not_empty": True}
                    },
                    {
                        "property": "Error Fix Trial",
                        "checkbox": {"equals": False}
                    }
                ]
            }
        )
        print("Error Recovery query SUCCESS")
    except Exception as e:
        print(f"Error Recovery query FAILED: {e}")

if __name__ == "__main__":
    asyncio.run(main())
