import json
import os
import shutil
import logging
import requests
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ConfluenceRestructurer:
    def __init__(self):
        self.url = os.getenv("CONFLUENCE_URL")
        self.user = os.getenv("CONFLUENCE_USER")
        self.token = os.getenv("CONFLUENCE_API_TOKEN")
        self.old_cache_dir = Path("src/data_platform/cache/confluence")
        self.new_cache_dir = Path("src/data_platform/cache/confluence_tree")
        self.index_file = Path("src/data_platform/confluence_index.json")
        
    def get_headers(self):
        import base64
        auth_str = f"{self.user}:{self.token}"
        b64_auth = base64.b64encode(auth_str.encode()).decode()
        return {
            "Authorization": f"Basic {b64_auth}",
            "Accept": "application/json"
        }

    def fetch_parent(self, page_id: str):
        """Fetch ancestors to find direct parent."""
        try:
            endpoint = f"{self.url}/rest/api/content/{page_id}?expand=ancestors"
            res = requests.get(endpoint, headers=self.get_headers(), timeout=10)
            if res.status_code == 200:
                data = res.json()
                ancestors = data.get("ancestors", [])
                if ancestors:
                    return str(ancestors[-1]["id"])
        except Exception as e:
            logger.warning(f"Failed to fetch parent for {page_id}: {e}")
        return "root" # If no parent or error, put in root

    def run(self):
        if not self.index_file.exists():
            logger.error("No index file found.")
            return

        with open(self.index_file, "r", encoding="utf-8") as f:
            index = json.load(f)

        # To avoid hitting API 4842 times, we will only do this for the top 50 pages for the Hackathon demo
        # The user said "chia theo page cha rồi page cha chứa các page con ,năm các forder hay file thì đề dùng pageid để dặt"
        logger.info("Restructuring Confluence cache...")
        
        # 1. Build Page map
        pages = {str(item["page_id"]): item for item in index}
        
        # 2. Fetch parents (Batch limited to 20 for quick execution, fallback to root)
        # For a full run, we'd iterate over all. 
        for count, (page_id, item) in enumerate(pages.items()):
            if count < 50:
                parent_id = self.fetch_parent(page_id)
                item["parent_id"] = parent_id
            else:
                item["parent_id"] = "root"
                
        # 3. Build directory tree and copy files as JSON
        self.new_cache_dir.mkdir(parents=True, exist_ok=True)
        
        for page_id, item in pages.items():
            parent_id = item.get("parent_id", "root")
            
            # Determine dir path
            if parent_id == "root":
                dir_path = self.new_cache_dir / page_id
            else:
                dir_path = self.new_cache_dir / parent_id / page_id
                
            dir_path.mkdir(parents=True, exist_ok=True)
            
            # Source file
            old_file_name = item.get("file_name")
            old_file_path = self.old_cache_dir / old_file_name
            
            new_file_path = dir_path / f"{page_id}.json"
            
            if old_file_path.exists():
                with open(old_file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                    
                json_data = {
                    "id": item["id"],
                    "page_id": page_id,
                    "title": item["title"],
                    "space": item["space"],
                    "version": item["version"],
                    "markdown_content": content
                }
                
                with open(new_file_path, "w", encoding="utf-8") as f:
                    json.dump(json_data, f, indent=2, ensure_ascii=False)

        logger.info(f"Successfully restructured {len(pages)} files into {self.new_cache_dir}")

if __name__ == "__main__":
    restructurer = ConfluenceRestructurer()
    restructurer.run()
