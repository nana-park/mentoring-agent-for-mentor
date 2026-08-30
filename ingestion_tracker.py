import json
import os
from datetime import datetime
from notion_api import NotionAPIClient

class IngestionTracker:
    def __init__(self, notion_client: NotionAPIClient, db_id: str):
        self.notion = notion_client
        self.db_id = db_id

    async def is_processed(self, source_id: str) -> bool:
        """
        Check if a given source_id (e.g. email ID or filename) has already been processed successfully.
        """
        if not self.db_id:
            return False
            
        try:
            response = await self.notion.query_database(
                database_id=self.db_id,
                filter_payload={
                    "and": [
                        {
                            "property": "Source ID",
                            "rich_text": {
                                "equals": source_id
                            }
                        },
                        {
                            "property": "Status",
                            "select": {
                                "equals": "Success"
                            }
                        }
                    ]
                }
            )
            return len(response.get("results", [])) > 0
        except Exception as e:
            print(f"Warning: Could not query Ingestion History DB. Error: {e}")
            return False

    async def record_ingestion(self, source_id: str, subject: str, student_name: str, type_val: str, status: str):
        """
        Record the result of processing a source into the Ingestion History DB.
        """
        if not self.db_id:
            return
            
        now_str = datetime.now().isoformat()
        prefix = f"[{student_name}] " if student_name else "[매칭 실패] "
        display_title = f"{prefix}{subject}"
        
        try:
            await self.notion.create_page(
                parent_db_id=self.db_id,
                properties={
                    "Source Title": {
                        "title": [{"text": {"content": display_title[:100]}}]
                    },
                    "Source ID": {
                        "rich_text": [{"text": {"content": source_id}}]
                    },
                    "Type": {
                        "select": {
                            "name": type_val
                        }
                    },
                    "Status": {
                        "select": {
                            "name": status
                        }
                    },
                    "Processed At": {
                        "date": {
                            "start": now_str
                        }
                    }
                }
            )
        except Exception as e:
            print(f"Error recording ingestion history for {source_id}: {e}")
