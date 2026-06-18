import json
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def align_schemas():
    data_dir = Path("src/data_platform")
    
    # 1. Fix file_descriptions.json
    file_desc_path = data_dir / "file_descriptions.json"
    files_map = {}
    if file_desc_path.exists():
        with open(file_desc_path, "r", encoding="utf-8") as f:
            files_data = json.load(f)
            
        aligned_files = []
        for file in files_data:
            # Fix the Unterminated string error
            desc = file.get("description", "")
            if "Failed to analyze due to error" in desc:
                desc = "Source code file. Requires manual review."
            
            project = file.get("project", "unknown")
            pipeline_id = f"urn:li:dataFlow:(gitlab,{project},PROD)"
            
            aligned_file = {
                "id": file.get("id"),
                "pipeline_id": pipeline_id,
                "name": file.get("name"),
                "entityType": "source_code",
                "path": file.get("path"),
                "description": desc,
                "logic": file.get("logic", ""),
                "dependencies": file.get("dependencies", [])
            }
            aligned_files.append(aligned_file)
            
            if pipeline_id not in files_map:
                files_map[pipeline_id] = []
            files_map[pipeline_id].append(aligned_file["id"])
            
        with open(file_desc_path, "w", encoding="utf-8") as f:
            json.dump(aligned_files, f, indent=2, ensure_ascii=False)
        logger.info(f"Aligned {len(aligned_files)} files in file_descriptions.json")

    # 2. Fix pipelines.json
    pipelines_path = data_dir / "pipelines.json"
    if pipelines_path.exists():
        with open(pipelines_path, "r", encoding="utf-8") as f:
            pipelines_data = json.load(f)
            
        aligned_pipelines = []
        for p in pipelines_data:
            pid = p.get("id")
            
            # Map files from files_map
            mapped_files = files_map.get(pid, [])
            
            aligned_pipeline = {
                "id": pid,
                "name": p.get("name"),
                "entityType": "pipeline",
                "owner": p.get("owner", {"type": "team", "name": "Data Platform"}),
                "domain": p.get("domain", "Data Platform"),
                "tier": p.get("tier", "Tier2"),
                "description": p.get("description", ""),
                "files": mapped_files, # MAP FILES TO PIPELINE
                "lineage": p.get("lineage", {"upstream": [], "downstream": []})
            }
            aligned_pipelines.append(aligned_pipeline)
            
        with open(pipelines_path, "w", encoding="utf-8") as f:
            json.dump(aligned_pipelines, f, indent=2, ensure_ascii=False)
        logger.info(f"Aligned {len(aligned_pipelines)} pipelines in pipelines.json")

    # 3. Fix confluence_knowledge.json
    conf_path = data_dir / "confluence_knowledge.json"
    if conf_path.exists():
        with open(conf_path, "r", encoding="utf-8") as f:
            conf_data = json.load(f)
            
        aligned_conf = []
        for c in conf_data:
            aligned_c = {
                "id": c.get("id"),
                "page_id": c.get("page_id"),
                "name": c.get("name"),
                "entityType": "knowledge_article",
                "owner": c.get("owner", {"type": "team", "name": "DataServices"}),
                "domain": c.get("domain", "Data Platform"),
                "tier": c.get("tier", "Tier2"),
                "tags": c.get("tags", []),
                "description": c.get("description", ""),
                "relations": c.get("relations", {"references": [], "dependsOn": []}),
                "content_chunks": c.get("content_chunks", [])
            }
            # For Vision AI mock: ensure chunks have [Image Analysis] if missing but image exists
            # We won't re-parse HTML, just fix schema format.
            aligned_conf.append(aligned_c)
            
        with open(conf_path, "w", encoding="utf-8") as f:
            json.dump(aligned_conf, f, indent=2, ensure_ascii=False)
        logger.info(f"Aligned {len(aligned_conf)} articles in confluence_knowledge.json")

    # 4. Fix datasets.json
    ds_path = data_dir / "datasets.json"
    if ds_path.exists():
        with open(ds_path, "r", encoding="utf-8") as f:
            ds_data = json.load(f)
            
        aligned_ds = []
        for d in ds_data:
            aligned_d = {
                "id": d.get("id"),
                "name": d.get("name"),
                "entityType": "dataset",
                "owner": d.get("owner", {"type": "team", "name": "Data Platform"}),
                "domain": d.get("domain", "Data Platform"),
                "tier": d.get("tier", "Tier2"),
                "tags": d.get("tags", []),
                "description": d.get("description", ""),
                "schema": d.get("schema", []),
                "lineage": d.get("lineage", {"upstream": [], "downstream": []})
            }
            aligned_ds.append(aligned_d)
            
        with open(ds_path, "w", encoding="utf-8") as f:
            json.dump(aligned_ds, f, indent=2, ensure_ascii=False)
        logger.info(f"Aligned {len(aligned_ds)} datasets in datasets.json")

if __name__ == "__main__":
    align_schemas()
