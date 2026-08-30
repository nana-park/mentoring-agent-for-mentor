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
    notion_mcp = NotionAPIClient(os.getenv("NOTION_TOKEN"))
    try:
        props = {
            "One Sentence": {
                "rich_text": [
                    {
                        "text": {
                            "content": "Test summary update"
                        }
                    }
                ]
            }
        }
        res = await notion_mcp.update_page("379c919e-34d1-8165-8d76-f2b434ad3e12", props)
        print("Success:", res)
    except Exception as e:
        print(e)
        if hasattr(e, 'response'):
            print(e.response.text)

if __name__ == "__main__":
    asyncio.run(main())
