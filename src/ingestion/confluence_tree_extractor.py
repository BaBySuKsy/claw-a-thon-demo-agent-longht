import os
import json
import asyncio
import logging
import base64
from pathlib import Path
from bs4 import BeautifulSoup
import aiohttp
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ConfluenceTreeExtractor:
    def __init__(self):
        self.url = os.getenv("CONFLUENCE_URL")
        self.user = os.getenv("CONFLUENCE_USER")
        self.token = os.getenv("CONFLUENCE_API_TOKEN")
        self.cache_dir = Path("src/data_platform/cache/confluence_tree")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Async HTTP session
        self.session = None
        self.concurrency_limit = asyncio.Semaphore(15) # Confluence API rate limit safety
        
    def get_headers(self):
        auth_str = f"{self.user}:{self.token}"
        b64_auth = base64.b64encode(auth_str.encode()).decode()
        return {
            "Authorization": f"Basic {b64_auth}",
            "Accept": "application/json"
        }

    async def init_session(self):
        if not self.session:
            self.session = aiohttp.ClientSession(headers=self.get_headers())

    async def close_session(self):
        if self.session:
            await self.session.close()

    async def fetch_page(self, page_id: str):
        """Fetches the page content and metadata."""
        async with self.concurrency_limit:
            endpoint = f"{self.url}/rest/api/content/{page_id}?expand=body.storage,space,version"
            try:
                async with self.session.get(endpoint) as res:
                    if res.status == 200:
                        return await res.json()
                    logger.error(f"Failed to fetch page {page_id}: {res.status}")
            except Exception as e:
                logger.error(f"Error fetching page {page_id}: {e}")
            return None

    async def fetch_children(self, page_id: str):
        """Fetches the immediate child pages."""
        async with self.concurrency_limit:
            endpoint = f"{self.url}/rest/api/content/{page_id}/child/page?limit=100"
            try:
                async with self.session.get(endpoint) as res:
                    if res.status == 200:
                        data = await res.json()
                        return data.get("results", [])
            except Exception as e:
                logger.error(f"Error fetching children for {page_id}: {e}")
            return []

    def parse_html_to_schema(self, html_content: str) -> dict:
        """
        Parses Confluence HTML into a highly structured JSON semantic schema.
        NO RAW MARKDOWN ALLOWED.
        """
        soup = BeautifulSoup(html_content, 'lxml')
        
        # 1. Extract Links (Jira, Code, Wiki)
        links = []
        for a in soup.find_all("a", href=True):
            links.append(a['href'])
            
        # 2. Extract Tables
        tables_data = []
        for table in soup.find_all("table"):
            rows = []
            for tr in table.find_all("tr"):
                cells = [td.get_text(strip=True) for td in tr.find_all(["th", "td"])]
                if any(cells):
                    rows.append(cells)
            if rows:
                tables_data.append(rows)
                
        # 3. Extract Images & Diagrams
        images = []
        for img in soup.find_all("ac:image"):
            att = img.find("ri:attachment")
            if att:
                filename = att.get("ri:filename", "unknown.png")
                images.append(f"[Vision AI Mock: Diagram {filename} showing data flow]")
                
        # 4. Extract Structured Sections
        sections = []
        current_heading = "Overview"
        current_body = []
        
        for element in soup.body.children if soup.body else soup.children:
            if element.name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
                # Save previous section
                if current_body:
                    sections.append({
                        "heading": current_heading,
                        "body": " ".join(current_body).strip()
                    })
                current_heading = element.get_text(strip=True)
                current_body = []
            elif element.name:
                text = element.get_text(separator=' ', strip=True)
                if text:
                    current_body.append(text)
                    
        # Add last section
        if current_body:
            sections.append({
                "heading": current_heading,
                "body": " ".join(current_body).strip()
            })

        return {
            "sections": sections,
            "extracted_entities": {
                "links_and_references": list(set(links)),
                "tables": tables_data,
                "images": images
            }
        }

    async def process_node(self, page_id: str, level: int = 1) -> dict:
        """Recursively process a node and all its children to build the JSON tree."""
        page_data = await self.fetch_page(page_id)
        if not page_data:
            return {"page_id": page_id, "error": "Not Found"}
            
        title = page_data.get("title", "Unknown")
        version = page_data.get("version", {}).get("number", 1)
        space_key = page_data.get("space", {}).get("key", "UNKNOWN")
        html_content = page_data.get("body", {}).get("storage", {}).get("value", "")
        
        logger.info(f"{'  '*level}Processing Level {level}: {title} ({page_id})")
        
        content_structure = self.parse_html_to_schema(html_content)
        
        # Recursively fetch children
        child_refs = await self.fetch_children(page_id)
        
        # Concurrency limit for child processing
        child_tasks = [self.process_node(child["id"], level + 1) for child in child_refs]
        child_pages = await asyncio.gather(*child_tasks) if child_tasks else []
        
        return {
            "page_id": page_id,
            "title": title,
            "level": level,
            "metadata": {
                "space": space_key,
                "version": version
            },
            "content_structure": content_structure,
            "child_pages": child_pages
        }

    async def run(self, root_id: str):
        await self.init_session()
        
        logger.info(f"Starting tree extraction from Root Space ID: {root_id}")
        
        # Step 1: Fetch Top-Level Pages (Children of root)
        top_level_refs = await self.fetch_children(root_id)
        logger.info(f"Found {len(top_level_refs)} Top-Level Pages. Generating {len(top_level_refs)} JSON files.")
        
        # Process each top level tree concurrently
        for ref in top_level_refs:
            top_page_id = ref["id"]
            top_title = ref["title"]
            safe_title = "".join(c if c.isalnum() else "_" for c in top_title)
            
            logger.info(f"\n=========================================")
            logger.info(f"Extracting Top-Level Tree: {top_title}")
            logger.info(f"=========================================\n")
            
            tree_data = await self.process_node(top_page_id, level=1)
            
            filename = f"{safe_title}_{top_page_id}.json"
            filepath = self.cache_dir / filename
            
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(tree_data, f, indent=2, ensure_ascii=False)
                
            logger.info(f"Saved complete tree to {filename}")
            
        await self.close_session()
        logger.info("All Top-Level Trees extracted successfully!")

if __name__ == "__main__":
    extractor = ConfluenceTreeExtractor()
    # 5983249 is the main DataServices root page ID
    asyncio.run(extractor.run("5983249"))
