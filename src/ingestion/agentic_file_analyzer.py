import json
import os
import asyncio
import logging
from pathlib import Path
from dotenv import load_dotenv
from openai import AsyncOpenAI
from tenacity import retry, wait_exponential, stop_after_attempt, retry_if_exception_type
import httpx

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

LLM_MODEL = os.getenv("LLM_MODEL", "minimax/minimax-m2.5")
# Strictly limit concurrency to avoid GreenNode 429 Rate Limits
CONCURRENCY_LIMIT = 2

# Rate limit handling decorator
@retry(
    retry=retry_if_exception_type((Exception)),
    wait=wait_exponential(multiplier=2, min=10, max=60),
    stop=stop_after_attempt(5)
)
async def analyze_with_llm(client: AsyncOpenAI, prompt: str):
    res = await client.chat.completions.create(
        model=LLM_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1,
        max_tokens=500
    )
    content = res.choices[0].message.content
    if not content or content.strip() == "":
        raise ValueError("Empty response from LLM")
    return content.strip()

async def analyze_file(client: AsyncOpenAI, project_name: str, filepath: Path, sem: asyncio.Semaphore) -> dict:
    async with sem:
        relative_path = "/".join(filepath.relative_to(Path("src/data_platform/cache/gitlab")).parts)
        
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
                
            if len(content.strip()) == 0:
                return None
                
            # Truncate content to avoid token limits
            max_chars = 8000
            if len(content) > max_chars:
                content = content[:max_chars] + "\n...[TRUNCATED]"
                
            prompt = f"""
You are an expert Data Engineer. Analyze the following source code file and extract its deep logic.
Respond ONLY with a valid JSON object matching this structure (no markdown tags, no extra text):
{{
  "description": "A detailed 2-3 sentence description of exactly what this file does.",
  "structure": "What classes/functions are defined here?",
  "logic": "What is the core business/data logic or validation rule implemented?",
  "dependencies": ["list of imported modules or frameworks"]
}}

File path: {relative_path}
Code:
{content}
"""         
            logger.info(f"Analyzing {relative_path}...")
            response_text = await analyze_with_llm(client, prompt)
            
            # Clean response
            response_text = response_text.replace("```json", "").replace("```", "").strip()
            data = json.loads(response_text)
            
            return {
                "id": f"urn:li:dataFlow:(gitlab,{project_name},PROD)/{filepath.name}",
                "name": filepath.name,
                "project": project_name,
                "path": relative_path,
                "type": "source_code",
                "description": data.get("description", ""),
                "structure": data.get("structure", ""),
                "logic": data.get("logic", ""),
                "dependencies": data.get("dependencies", [])
            }
        except Exception as e:
            logger.error(f"Failed to analyze {relative_path}: {e}")
            return {
                "id": f"urn:li:dataFlow:(gitlab,{project_name},PROD)/{filepath.name}",
                "name": filepath.name,
                "project": project_name,
                "path": relative_path,
                "type": "source_code",
                "description": f"Failed to analyze due to error: {e}",
                "structure": "",
                "logic": "",
                "dependencies": []
            }

async def main():
    client = AsyncOpenAI(
        api_key=os.getenv("LLM_API_KEY"),
        base_url=os.getenv("LLM_BASE_URL", "https://maas-llm-aiplatform-hcm.api.vngcloud.vn/v1"),
    )
    
    base_cache_dir = Path("src/data_platform/cache/gitlab")
    allowed_exts = {".py", ".scala", ".java", ".yaml", ".yml", ".md", ".json", ".txt", ".sh", ".xml"}
    
    tasks = []
    sem = asyncio.Semaphore(CONCURRENCY_LIMIT)
    
    # We will only analyze a batch of the most important files first, to avoid waiting 3 hours
    # The user asked for "toàn bộ script từng file 1", so we will queue them all!
    files_to_process = []
    for root, _, files in os.walk(base_cache_dir):
        if ".git" in root:
            continue
        for file in files:
            fp = Path(root) / file
            if fp.suffix.lower() in allowed_exts or fp.name in ["Dockerfile", "Makefile"]:
                rel_parts = fp.relative_to(base_cache_dir).parts
                if len(rel_parts) >= 2:
                    project_name = rel_parts[0]
                    files_to_process.append((project_name, fp))
                    
    logger.info(f"Found {len(files_to_process)} files to deeply analyze.")
    
    # Optional: For hackathon time limits, if > 100 files, we might want to inform the user it takes long
    
    for project_name, fp in files_to_process:
        tasks.append(asyncio.create_task(analyze_file(client, project_name, fp, sem)))
        
    results = await asyncio.gather(*tasks)
    
    # Filter out empty files
    final_results = [r for r in results if r is not None]
    
    with open("src/data_platform/file_descriptions.json", "w", encoding="utf-8") as f:
        json.dump(final_results, f, indent=2, ensure_ascii=False)
        
    logger.info(f"Saved {len(final_results)} rich file descriptions to file_descriptions.json")

if __name__ == "__main__":
    asyncio.run(main())
