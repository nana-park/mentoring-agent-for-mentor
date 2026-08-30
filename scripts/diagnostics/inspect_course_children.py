# Direct-file execution support; prefer python -m scripts.<group>.<name>.
if __package__ in (None, ""):
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import os
import asyncio
from mentoring.config import load_environment
from mentoring.integrations.notion import NotionAPIClient

async def run():
    load_environment()
    client = NotionAPIClient(os.getenv('NOTION_TOKEN'))
    # Course Schedule DB
    res = await client.query_database('358c919e34d180f09573edb4e42a261a')
    for row in res.get('results', []):
        try:
            title = row['properties']['강의명']['title'][0]['plain_text']
            page_id = row['id']
            print(f"Course: {title} | Page ID: {page_id}")
            # get children of the course page
            children = await client.get_block_children(page_id)
            print("Children blocks:")
            for child in children.get('results', []):
                print(f" - {child['type']} | ID: {child['id']}")
                if child['type'] == 'child_database':
                    print(f"   -> DB Title: {child['child_database']['title']}")
        except Exception as e:
            print(f"Error reading row: {e}")

if __name__ == "__main__":
    asyncio.run(run())
