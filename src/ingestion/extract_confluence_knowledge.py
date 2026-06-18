import os
import json
import asyncio
import logging
import re
from pathlib import Path
from dotenv import load_dotenv
from openai import AsyncOpenAI
from tenacity import retry, wait_exponential, stop_after_attempt, retry_if_exception_type

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

LLM_MODEL = os.getenv("LLM_MODEL", "minimax/minimax-m2.5")
CONCURRENCY_LIMIT = 2

@retry(
    retry=retry_if_exception_type((Exception)),
    wait=wait_exponential(multiplier=2, min=5, max=30),
    stop=stop_after_attempt(3)
)
async def ask_llm_json(client: AsyncOpenAI, prompt: str):
    res = await client.chat.completions.create(
        model=LLM_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1,
        max_tokens=800
    )
    content = res.choices[0].message.content
    if not content:
        raise ValueError("Empty LLM response")
    
    # Clean code block backticks
    content = content.replace("```json", "").replace("```", "").strip()
    return json.loads(content)

def chunk_markdown(text: str) -> list:
    """RAGFlow strategy: Semantic chunking based on headings."""
    chunks = []
    # Split by ## or #
    sections = re.split(r'\n##+ ', text)
    
    # The first part might just be # Title, add it as first chunk
    if sections:
        chunks.append({"chunk_id": "c0", "heading": "Overview", "content": sections[0][:2000]}) # Limit size
        
    for i, sec in enumerate(sections[1:]):
        lines = sec.split('\n', 1)
        heading = lines[0].strip()
        content = lines[1] if len(lines) > 1 else ""
        if len(content.strip()) > 50:
            chunks.append({
                "chunk_id": f"c{i+1}",
                "heading": heading,
                "content": content[:2000] # truncate large chunks
            })
    return chunks[:5] # Max 5 chunks per document to save tokens

async def extract_knowledge(client: AsyncOpenAI, filepath: Path, sem: asyncio.Semaphore) -> dict:
    async with sem:
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                raw_text = f.read()
                
            # Extract basic info from the top comment if exists
            # Example: # Data Platform Overview
            # **Space:** DataServices | **Page ID:** 93407387 | **Version:** 2
            
            page_id = "unknown"
            match = re.search(r'\*\*Page ID:\*\* (\d+)', raw_text)
            if match:
                page_id = match.group(1)
                
            chunks = chunk_markdown(raw_text)
            
            # Combine chunks for LLM to read and extract metadata
            context_text = "\n\n".join([f"[{c['heading']}]\n{c['content']}" for c in chunks])
            
            prompt = f"""
You are an expert Data Architect. We are adopting the OpenMetadata and Backstage schema standard.
Read the following Confluence Wiki page content and extract its structured metadata.

Rules:
- entityType MUST BE "knowledge_article"
- owner MUST BE a dictionary: {{"type": "team"|"person", "name": "..."}} (Guess based on context, default to Data Platform)
- tier MUST BE "Tier1", "Tier2", or "Tier3" (Guess based on criticality)
- domain MUST BE string (e.g. "Data Platform", "Data Infra", "CDP", "Payment")
- relations MUST BE a dictionary with lists of entity names: {{"references": [], "dependsOn": []}}
- tags MUST BE an array of strings

Respond ONLY with a valid JSON object:
{{
  "name": "Title of the document",
  "entityType": "knowledge_article",
  "owner": {{"type": "team", "name": "..."}},
  "domain": "...",
  "tier": "Tier2",
  "tags": ["..."],
  "status": "active",
  "description": "Short summary...",
  "relations": {{"references": [], "dependsOn": []}}
}}

Content to analyze:
{context_text[:5000]}
"""
            logger.info(f"Extracting Knowledge from {filepath.name}...")
            meta = await ask_llm_json(client, prompt)
            
            # Assemble the final knowledge object
            return {
                "id": f"urn:li:knowledge:(confluence,{page_id},PROD)",
                "page_id": page_id,
                "name": meta.get("name", filepath.stem),
                "entityType": meta.get("entityType", "knowledge_article"),
                "owner": meta.get("owner", {"type": "team", "name": "Data Platform"}),
                "domain": meta.get("domain", "Data Platform"),
                "tier": meta.get("tier", "Tier2"),
                "tags": meta.get("tags", []),
                "status": meta.get("status", "active"),
                "description": meta.get("description", ""),
                "relations": meta.get("relations", {"references": [], "dependsOn": []}),
                "content_chunks": chunks
            }
        except Exception as e:
            logger.error(f"Failed to process {filepath.name}: {e}")
            return None

async def main():
    client = AsyncOpenAI(
        api_key=os.getenv("LLM_API_KEY"),
        base_url=os.getenv("LLM_BASE_URL", "https://maas-llm-aiplatform-hcm.api.vngcloud.vn/v1"),
    )
    
    confluence_dir = Path("src/data_platform/cache/confluence")
    md_files = list(confluence_dir.glob("*.md"))
    
    logger.info(f"Found {len(md_files)} markdown files.")
    
    # [HACKATHON DEMO LIMIT]
    # To allow fast review, we will only extract the 5 most important/largest files first.
    # In production, we remove this slice.
    md_files.sort(key=lambda x: x.stat().st_size, reverse=True)
    sample_files = md_files[:5]
    
    sem = asyncio.Semaphore(CONCURRENCY_LIMIT)
    tasks = [asyncio.create_task(extract_knowledge(client, fp, sem)) for fp in sample_files]
    
    results = await asyncio.gather(*tasks)
    final_results = [r for r in results if r is not None]
    
    output_path = "src/data_platform/confluence_knowledge.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(final_results, f, indent=2, ensure_ascii=False)
        
    logger.info(f"Saved {len(final_results)} knowledge entities to {output_path}")

if __name__ == "__main__":
    asyncio.run(main())
