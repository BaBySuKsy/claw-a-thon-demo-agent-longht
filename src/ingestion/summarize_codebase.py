import json
import os
from pathlib import Path
import re

def extract_summary(filepath: Path) -> str:
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
            
        # Try to find a docstring or class/def name
        if filepath.name.endswith(".scala"):
            match = re.search(r'class\s+([A-Za-z0-9_]+)', content)
            if match:
                return f"Scala validator class: {match.group(1)}."
        elif filepath.name.endswith(".py"):
            match = re.search(r'"""(.*?)"""', content, re.DOTALL)
            if match:
                return match.group(1).strip().split('\n')[0]
            match = re.search(r'def\s+([A-Za-z0-9_]+)', content)
            if match:
                return f"Python script containing: {match.group(1)}."
        elif filepath.name.endswith(".yaml") or filepath.name.endswith(".yml"):
            if "testsuite" in filepath.name:
                return f"Data quality test suite configuration for {filepath.stem}."
            return "YAML configuration file."
            
        return f"Source code file: {filepath.name}"
    except Exception as e:
        return f"Error reading file: {e}"

def main():
    file_descriptions = {}
    base_cache_dir = Path("src/data_platform/cache/gitlab")
    
    # Allowed extensions to avoid reading binaries
    allowed_exts = {".py", ".scala", ".java", ".yaml", ".yml", ".md", ".json", ".txt", ".sh", ".xml"}
    
    for root, _, files in os.walk(base_cache_dir):
        if ".git" in root:
            continue
            
        for file in files:
            fp = Path(root) / file
            if fp.suffix.lower() in allowed_exts or fp.name in ["Dockerfile", "Makefile"]:
                # Extract project name from the path: src/data_platform/cache/gitlab/<project_name>/...
                rel_parts = fp.relative_to(base_cache_dir).parts
                if len(rel_parts) < 2:
                    continue
                
                project_name = rel_parts[0]
                relative_key = "/".join(rel_parts) # e.g. airflow-cloud/dags/job.py
                
                file_descriptions[relative_key] = extract_summary(fp)
                
    with open("src/data_platform/file_descriptions.json", "w", encoding="utf-8") as f:
        json.dump(file_descriptions, f, indent=2, ensure_ascii=False)
        
    print(f"Summarized {len(file_descriptions)} files across all projects.")

if __name__ == "__main__":
    main()
