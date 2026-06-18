import json
import os
from pathlib import Path

def main():
    pipelines_path = Path("src/data_platform/pipelines.json")
    with open(pipelines_path, "r", encoding="utf-8") as f:
        pipelines = json.load(f)
        
    master_file_descriptions = {}
    
    # Check if there is an existing file_descriptions to merge with or overwrite
    # Let's overwrite entirely with the new AI-generated descriptions
    
    for p in pipelines:
        name = p["name"]
        analysis_dir = Path(f"src/data_platform/temp_analysis/{name}")
        
        # 1. Merge Architecture
        arch_file = analysis_dir / "architecture.json"
        if arch_file.exists():
            with open(arch_file, "r", encoding="utf-8") as f:
                arch_data = json.load(f)
                
            # It could be {"architecture_description": "..."} or just a string or dict
            if isinstance(arch_data, dict):
                # Try to get the longest string or the "architecture_description" key
                desc = arch_data.get("architecture_description", "")
                if not desc:
                    desc = json.dumps(arch_data, indent=2)
                p["metadata"]["architecture"] = desc
            else:
                p["metadata"]["architecture"] = str(arch_data)
                
        # 2. Merge File Descriptions
        fd_file = analysis_dir / "file_descriptions.json"
        if fd_file.exists():
            with open(fd_file, "r", encoding="utf-8") as f:
                fd_data = json.load(f)
                
            for k, v in fd_data.items():
                # Ensure the key starts with the project name to maintain consistency
                # If the subagent returned "dags/some_dag.py", we prefix it with "airflow-cloud/"
                if not k.startswith(f"{name}/"):
                    k = f"{name}/{k}"
                master_file_descriptions[k] = v

    # Write back pipelines.json
    with open(pipelines_path, "w", encoding="utf-8") as f:
        json.dump(pipelines, f, indent=2, ensure_ascii=False)
        
    # Write back file_descriptions.json
    with open("src/data_platform/file_descriptions.json", "w", encoding="utf-8") as f:
        json.dump(master_file_descriptions, f, indent=2, ensure_ascii=False)
        
    print(f"Successfully merged architectures for {len(pipelines)} projects.")
    print(f"Successfully merged {len(master_file_descriptions)} file descriptions.")

if __name__ == "__main__":
    main()
