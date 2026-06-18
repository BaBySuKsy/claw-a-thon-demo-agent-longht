import os
import json
from pathlib import Path

def get_directory_structure(root_path: Path):
    """Recursively builds a dictionary representing the directory structure."""
    result = {}
    for item in root_path.iterdir():
        if item.name == ".git":
            continue
        if item.is_dir():
            result[item.name] = get_directory_structure(item)
        else:
            result[item.name] = "file"
    return result

def main():
    base_dir = Path("src/data_platform/cache/gitlab")
    pipelines_file = Path("src/data_platform/pipelines.json")
    
    if not pipelines_file.exists():
        return
        
    with open(pipelines_file, "r", encoding="utf-8") as f:
        pipelines = json.load(f)
        
    for p in pipelines:
        project_name = p.get("name")
        project_dir = base_dir / project_name
        if project_dir.exists() and project_dir.is_dir():
            p["directory_structure"] = get_directory_structure(project_dir)
            
    with open(pipelines_file, "w", encoding="utf-8") as f:
        json.dump(pipelines, f, indent=2, ensure_ascii=False)
        
    print(f"Successfully updated directory structure for {len(pipelines)} pipelines.")

if __name__ == "__main__":
    main()
