import os
import asyncio
from dotenv import load_dotenv
from notion_api import NotionAPIClient

async def main():
    load_dotenv()
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
