import json
import os
import asyncio
import logging
from pathlib import Path
from dotenv import load_dotenv
from openai import AsyncOpenAI
from tenacity import retry, wait_exponential, stop_after_attempt, retry_if_exception_type

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

LLM_MODEL = os.getenv("LLM_MODEL", "minimax/minimax-m2.5")
CONCURRENCY_LIMIT = 3

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
        max_tokens=2048 # INCREASED TO AVOID TRUNCATION
    )
    content = res.choices[0].message.content
    if not content or content.strip() == "":
        raise ValueError("Empty response from LLM")
    return content.strip()

async def fix_file(client: AsyncOpenAI, file_entry: dict, sem: asyncio.Semaphore) -> dict:
    async with sem:
        filepath = Path("src/data_platform/cache/gitlab") / file_entry["path"]
        
        try:
            if not filepath.exists():
                return file_entry
                
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
                
            if len(content.strip()) == 0:
                return file_entry
                
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

File path: {file_entry['path']}
Code:
{content}
"""         
            logger.info(f"Fixing {file_entry['path']}...")
            response_text = await analyze_with_llm(client, prompt)
            
            # Clean response
            response_text = response_text.replace("```json", "").replace("```", "").strip()
            data = json.loads(response_text)
            
            file_entry["description"] = data.get("description", "")
            file_entry["structure"] = data.get("structure", "")
            file_entry["logic"] = data.get("logic", "")
            file_entry["dependencies"] = data.get("dependencies", [])
            
            return file_entry
        except Exception as e:
            logger.error(f"Failed to fix {file_entry['path']}: {e}")
            return file_entry

async def main():
    client = AsyncOpenAI(
        api_key=os.getenv("LLM_API_KEY"),
        base_url=os.getenv("LLM_BASE_URL", "https://maas-llm-aiplatform-hcm.api.vngcloud.vn/v1"),
    )
    
    file_desc_path = Path("src/data_platform/file_descriptions.json")
    with open(file_desc_path, "r", encoding="utf-8") as f:
        files = json.load(f)
        
    failed_files = [f for f in files if "Requires manual review" in f.get("description", "")]
    logger.info(f"Found {len(failed_files)} failed files to fix.")
    
    tasks = []
    sem = asyncio.Semaphore(CONCURRENCY_LIMIT)
    
    for f in failed_files:
        tasks.append(asyncio.create_task(fix_file(client, f, sem)))
        
    fixed_results = await asyncio.gather(*tasks)
    
    # Update original list
    for fixed in fixed_results:
        for i, original in enumerate(files):
            if original["id"] == fixed["id"]:
                files[i] = fixed
                break
                
    with open(file_desc_path, "w", encoding="utf-8") as f:
        json.dump(files, f, indent=2, ensure_ascii=False)
        
    logger.info(f"Fixed and saved file_descriptions.json")

if __name__ == "__main__":
    asyncio.run(main())
