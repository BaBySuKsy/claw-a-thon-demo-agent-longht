import os
import json
import logging
import requests
from bs4 import BeautifulSoup
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

class ConfluenceClient:
    def __init__(self):
        self.url = os.getenv("CONFLUENCE_URL")
        self.user = os.getenv("CONFLUENCE_USER")
        self.token = os.getenv("CONFLUENCE_API_TOKEN")
        self.cache_dir = Path("src/data_platform/cache/confluence")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        if not self.url or not self.token:
            logger.warning("Confluence credentials not fully set.")

    def get_headers(self):
        # Depending on Confluence setup, this could be Bearer or Basic.
        # We will use Basic auth with token as requested.
        import base64
        auth_str = f"{self.user}:{self.token}"
        b64_auth = base64.b64encode(auth_str.encode()).decode()
        return {
            "Authorization": f"Basic {b64_auth}",
            "Accept": "application/json"
        }

    def fetch_page(self, page_id: str):
        """Fetches the page content including its storage XML."""
        endpoint = f"{self.url}/rest/api/content/{page_id}?expand=body.storage,space,version"
        res = requests.get(endpoint, headers=self.headers, timeout=10)
        if res.status_code == 200:
            return res.json()
        logger.error(f"Failed to fetch page {page_id}: {res.text}")
        return None

    def fetch_children(self, page_id: str):
        """Fetches the immediate child pages."""
        endpoint = f"{self.url}/rest/api/content/{page_id}/child/page?limit=100"
        res = requests.get(endpoint, headers=self.headers, timeout=10)
        if res.status_code == 200:
            return res.json().get("results", [])
        return []

    async def _vision_analyze_image(self, image_url: str, filename: str) -> str:
        """
        Mock for Multimodal Vision LLM.
        In reality, this would download the image bytes and send to Gemini 1.5 Pro or GPT-4o.
        """
        # TODO: Integrate actual Vision Model (e.g. MiniMax Vision or Gemini)
        logger.info(f"Vision AI analyzing image: {filename}")
        return f"\n> [Image Analysis by Vision AI: Diagram '{filename}' shows data flow architecture.]\n"

    async def convert_html_to_markdown(self, html_content: str, page_id: str) -> str:
        """
        Advanced parser that handles Macros, Code blocks, and Images.
        """
        soup = BeautifulSoup(html_content, 'lxml') # or html.parser
        
        # 1. Extract Macros (PlantUML, Draw.io)
        for macro in soup.find_all("ac:structured-macro"):
            macro_name = macro.get("ac:name", "")
            if macro_name in ["plantuml", "mermaid", "drawio"]:
                # Try to find plain-text-body
                body = macro.find("ac:plain-text-body")
                if body and body.string:
                    diagram_code = body.string
                    # Replace macro with Markdown code block
                    new_tag = soup.new_tag("pre")
                    new_tag.string = f"```{macro_name}\n{diagram_code}\n```"
                    macro.replace_with(new_tag)
                else:
                    new_tag = soup.new_tag("p")
                    new_tag.string = f"[Diagram Macro: {macro_name}]"
                    macro.replace_with(new_tag)
                    
        # 2. Extract Code Blocks
        for code in soup.find_all("ac:structured-macro", {"ac:name": "code"}):
            body = code.find("ac:plain-text-body")
            if body and body.string:
                new_tag = soup.new_tag("pre")
                new_tag.string = f"```\n{body.string}\n```"
                code.replace_with(new_tag)
                
        # 3. Vision Image Replacement
        for image in soup.find_all("ac:image"):
            # Extract ri:filename
            attachment = image.find("ri:attachment")
            if attachment:
                filename = attachment.get("ri:filename", "unknown.png")
                # Simulate Vision AI extraction
                ai_desc = await self._vision_analyze_image("mock_url", filename)
                new_tag = soup.new_tag("p")
                new_tag.string = ai_desc
                image.replace_with(new_tag)
                
        # Get raw text
        # Using get_text with newlines helps preserve some formatting
        markdown_text = soup.get_text(separator="\n")
        # Clean up excessive newlines
        import re
        markdown_text = re.sub(r'\n{3,}', '\n\n', markdown_text)
        return markdown_text

    async def process_tree(self, root_id: str):
        """Recursively fetches and caches all pages starting from root_id."""
        queue = [root_id]
        processed = set()
        wiki_index = []
        
        self.headers = self.get_headers()
        
        while queue:
            current_id = queue.pop(0)
            if current_id in processed:
                continue
                
            page_data = self.fetch_page(current_id)
            if not page_data:
                continue
                
            title = page_data["title"]
            version = page_data.get("version", {}).get("number", 1)
            space_key = page_data.get("space", {}).get("key", "UNKNOWN")
            
            logger.info(f"Processing Confluence Page: {title} (ID: {current_id})")
            html_content = page_data.get("body", {}).get("storage", {}).get("value", "")
            
            markdown_content = await self.convert_html_to_markdown(html_content, current_id)
            
            # Save to cache
            safe_title = "".join(c if c.isalnum() else "_" for c in title)
            file_name = f"{current_id}_{safe_title}.md"
            file_path = self.cache_dir / file_name
            
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(f"# {title}\n")
                f.write(f"**Space:** {space_key} | **Page ID:** {current_id} | **Version:** {version}\n\n")
                f.write(markdown_content)
                
            wiki_index.append({
                "id": f"urn:li:dataset:(urn:li:dataPlatform:confluence,{current_id},PROD)",
                "page_id": current_id,
                "title": title,
                "space": space_key,
                "file_name": file_name,
                "version": version
            })
            
            processed.add(current_id)
            
            # Fetch children
            children = self.fetch_children(current_id)
            for child in children:
                queue.append(child["id"])
                
        # Save Index
        with open("src/data_platform/confluence_index.json", "w", encoding="utf-8") as f:
            json.dump(wiki_index, f, indent=2, ensure_ascii=False)
            
        logger.info(f"Confluence extraction complete. {len(wiki_index)} pages indexed.")

if __name__ == "__main__":
    import asyncio
    logging.basicConfig(level=logging.INFO)
    client = ConfluenceClient()
    # Root Page ID from user
    asyncio.run(client.process_tree("5983249"))
