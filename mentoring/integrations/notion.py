import httpx

class NotionAPIClient:
    def __init__(self, access_token: str):
        self.headers = {
            "Authorization": f"Bearer {access_token}",
            "Notion-Version": "2022-06-28",
            "Content-Type": "application/json"
        }
        self.base_url = "https://api.notion.com/v1"
        self.client = httpx.AsyncClient(headers=self.headers, base_url=self.base_url)
        
    async def connect(self):
        # HTTPX client is ready
        pass
        
    async def close(self):
        await self.client.aclose()
        
    async def query_database(self, database_id: str, filter_payload: dict = None, sorts: list = None, page_size: int = 100, start_cursor: str = None):
        payload = {}
        if filter_payload: payload["filter"] = filter_payload
        if sorts: payload["sorts"] = sorts
        payload["page_size"] = page_size
        if start_cursor: payload["start_cursor"] = start_cursor
        
        response = await self.client.post(f"/databases/{database_id}/query", json=payload)
        response.raise_for_status()
        return response.json()
        
    async def create_page(self, parent_db_id: str, properties: dict):
        payload = {
            "parent": {"database_id": parent_db_id},
            "properties": properties
        }
        response = await self.client.post("/pages", json=payload)
        response.raise_for_status()
        return response.json()
        
    async def update_page(self, page_id: str, properties: dict):
        payload = {"properties": properties}
        response = await self.client.patch(f"/pages/{page_id}", json=payload)
        response.raise_for_status()
        return response.json()
        
    async def get_block_children(self, block_id: str):
        response = await self.client.get(f"/blocks/{block_id}/children")
        response.raise_for_status()
        return response.json()
        
    async def append_block_children(self, block_id: str, children: list):
        payload = {"children": children}
        response = await self.client.patch(f"/blocks/{block_id}/children", json=payload)
        response.raise_for_status()
        return response.json()
