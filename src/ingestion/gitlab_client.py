import os
import requests
import logging
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

class GitLabClient:
    """
    Client to connect to GitLab via REST API.
    """
    def __init__(self):
        self.base_url = os.getenv("GITLAB_BASE_URL", "").rstrip('/')
        self.token = os.getenv("GITLAB_TOKEN")
        self.headers = {"PRIVATE-TOKEN": self.token} if self.token else {}

    def authenticate(self) -> bool:
        """
        Validate PAT token.
        """
        if not self.token:
            logger.error("GitLab token is missing.")
            return False
        
        try:
            res = requests.get(f"{self.base_url}/api/v4/user", headers=self.headers, timeout=10)
            if res.status_code == 200:
                user_info = res.json()
                logger.info(f"GitLab authenticated successfully as: {user_info.get('username')}")
                return True
            else:
                logger.error(f"GitLab auth failed. Status: {res.status_code}, Response: {res.text}")
                return False
        except Exception as e:
            logger.error(f"GitLab connection exception: {e}")
            return False

    def get_project_id(self, project_path: str) -> tuple:
        """Find project ID by exact path with namespace."""
        import urllib.parse
        encoded_path = urllib.parse.quote(project_path, safe='')
        url = f"{self.base_url}/api/v4/projects/{encoded_path}"
        res = requests.get(url, headers=self.headers, timeout=10)
        if res.status_code == 200:
            p = res.json()
            return p["id"], p["path_with_namespace"], p.get("description", "")
        return None, None, None

    def fetch_dags(self):
        """
        Fetch DAG files and project info from specified repositories.
        Downloads full repositories to local cache and builds detailed pipelines.json.
        """
        if not self.headers:
            if not self.authenticate():
                return []
                
        # Use exact namespace paths to avoid fetching personal forks
        target_projects = {
            "data-quality-svc": {"path": "dataeng/data-quality-svc", "branch": "main", "domain": "acme.analytics.data_quality"},
            "credit-curated-etl": {"path": "dataeng/credit-curated-etl", "branch": "main", "domain": "acme.analytics.curated.lending"},
            "fund-mapping-etl": {"path": "dataeng/fund-mapping-etl", "branch": "main", "domain": "acme.analytics.curated.fund_mapping"},
            "airflow-onprem": {"path": "dataeng/airflow-onprem", "branch": "main", "domain": "acme.analytics.airflow"},
            "airflow-cloud": {"path": "dataeng/airflow-cloud", "branch": "main", "domain": "acme.analytics.airflow"},
            "etl-lib": {"path": "dataeng/etl-lib", "branch": "main", "domain": "acme.analytics.etl_lib"}
        }
        
        import zipfile
        import io
        import shutil
        import os
        from pathlib import Path
        
        cache_base = Path("src/data_platform/cache/gitlab")
        if cache_base.exists():
            shutil.rmtree(cache_base)
        cache_base.mkdir(parents=True, exist_ok=True)
        
        pipelines = []
        for name, config in target_projects.items():
            path = config["path"]
            branch = config["branch"]
            domain = config["domain"]
            
            logger.info(f"Searching GitLab for project: {name} at {path} (Branch: {branch})")
            p_id, p_path, p_desc = self.get_project_id(path)
            if not p_id:
                logger.warning(f"Project {path} not found.")
                continue
                
            logger.info(f"Downloading archive for {name} on branch {branch}...")
            import urllib.parse
            encoded_branch = urllib.parse.quote(branch, safe='')
            archive_url = f"{self.base_url}/api/v4/projects/{p_id}/repository/archive.zip?sha={encoded_branch}"
            res = requests.get(archive_url, headers=self.headers, timeout=10)
            
            project_cache_dir = cache_base / name
            project_cache_dir.mkdir(exist_ok=True)
            
            if res.status_code == 200:
                with zipfile.ZipFile(io.BytesIO(res.content)) as z:
                    # Files are inside a root folder like 'data-quality-svc-feature-on-prem-migration-12345'
                    # We want to extract and flatten them or just keep the folder structure.
                    for member in z.infolist():
                        # Remove the top-level directory from the path
                        parts = member.filename.split("/", 1)
                        if len(parts) > 1 and parts[1]:
                            target_path = project_cache_dir / parts[1]
                            target_path.parent.mkdir(parents=True, exist_ok=True)
                            if not member.is_dir():
                                with target_path.open("wb") as f:
                                    f.write(z.read(member.filename))
            else:
                logger.error(f"Failed to download archive for {name}: {res.status_code}")
                # Try fallback to master or develop if branch failed
                logger.info(f"Retrying {name} with branch 'master'...")
                archive_url = f"{self.base_url}/api/v4/projects/{p_id}/repository/archive.zip?sha=master"
                res = requests.get(archive_url, headers=self.headers, timeout=10)
                if res.status_code != 200:
                    logger.info(f"Retrying {name} with branch 'develop'...")
                    archive_url = f"{self.base_url}/api/v4/projects/{p_id}/repository/archive.zip?sha=develop"
                    res = requests.get(archive_url, headers=self.headers, timeout=10)
                    
                if res.status_code == 200:
                    with zipfile.ZipFile(io.BytesIO(res.content)) as z:
                        for member in z.infolist():
                            parts = member.filename.split("/", 1)
                            if len(parts) > 1 and parts[1]:
                                target_path = project_cache_dir / parts[1]
                                target_path.parent.mkdir(parents=True, exist_ok=True)
                                if not member.is_dir():
                                    with target_path.open("wb") as f:
                                        f.write(z.read(member.filename))
                                            
            # Build detailed structural information from the extracted files
            dag_files = []
            validators = []
            test_suites = []
            has_ci = False
            readme_snippet = ""
            
            if project_cache_dir.exists():
                for root, _, files in os.walk(project_cache_dir):
                    rel_root = Path(root).relative_to(project_cache_dir)
                    for file in files:
                        rel_path = str(rel_root / file)
                        if rel_path.startswith("."): # avoid .git or similar if any
                            if file == ".gitlab-ci.yml":
                                has_ci = True
                            continue
                            
                        if file.endswith(".py") and ("dag" in rel_path.lower() or "/" not in rel_path):
                            dag_files.append(rel_path)
                            
                        if name == "data-quality-svc":
                            if "validator" in rel_path.lower() and file.endswith(".scala") and "test" not in file.lower():
                                validators.append(file.replace(".scala", ""))
                        
                        if name == "credit-curated-etl":
                            if "testsuite" in rel_path.lower() and (file.endswith(".yaml") or file.endswith(".yml")):
                                test_suites.append(rel_path)
                                
                        if file.lower() == "readme.md":
                            try:
                                with open(Path(root)/file, "r") as rf:
                                    # Just get the first 500 chars as a snippet
                                    readme_snippet = rf.read(500)
                            except:
                                pass
            
            # We treat the entire project as a pipeline cluster
            pipeline = {
                "id": f"urn:li:dataFlow:(airflow,{name},PROD)",
                "name": name,
                "type": "pipeline",
                "domain": domain,
                "description": p_desc or f"GitLab repository for {name}. Contains code for data processing and validation.",
                "url": f"{self.base_url}/{p_path}",
                "owner": {"type": "team", "name": "data-engineering"},
                "tier": "Tier2",
                "tags": ["airflow", "gitlab"],
                "metadata": {
                    "branch_tracked": branch,
                    "has_ci": has_ci,
                    "readme_preview": readme_snippet,
                    "dag_files": dag_files,
                }
            }
            if name == "data-quality-svc":
                pipeline["metadata"]["validators"] = validators
                pipeline["metadata"]["architecture"] = "Contains CI/CD workflows, custom validators, and unit tests."
            if name == "credit-curated-etl":
                pipeline["metadata"]["test_suites"] = test_suites
                
            pipelines.append(pipeline)
            
        return pipelines

    def fetch_pipeline_by_id(self, pipeline_urn: str) -> dict:
        """
        Fetch a single pipeline by its URN for Just-In-Time verification.
        Example URN: urn:li:dataFlow:(airflow,airflow-cloud,PROD)
        """
        if not self.headers:
            if not self.authenticate():
                return None
                
        # Extract project name from URN
        try:
            parts = pipeline_urn.split(",")
            project_name = parts[1]
        except IndexError:
            return None
            
        target_projects = {
            "data-quality-svc": "dataeng/data-quality-svc",
            "credit-curated-etl": "dataeng/credit-curated-etl",
            "fund-mapping-etl": "dataeng/fund-mapping-etl",
            "airflow-onprem": "dataeng/airflow-onprem",
            "airflow-cloud": "dataeng/airflow-cloud",
            "etl-lib": "dataeng/etl-lib"
        }
        
        project_path = target_projects.get(project_name)
        if not project_path:
            return None
            
        p_id, p_path, p_desc = self.get_project_id(project_path)
        if not p_id:
            return None
            
        tree_url = f"{self.base_url}/api/v4/projects/{p_id}/repository/tree?recursive=true&per_page=100"
        res = requests.get(tree_url, headers=self.headers, timeout=10)
        dag_files = []
        if res.status_code == 200:
            for item in res.json():
                if item["type"] == "blob" and item["path"].endswith(".py"):
                    if "dag" in item["path"].lower() or "/" not in item["path"]:
                        dag_files.append(item["path"])
                        
        return {
            "id": pipeline_urn,
            "name": project_name,
            "type": "pipeline",
            "description": p_desc or f"GitLab repository for {project_name}",
            "url": f"{self.base_url}/{p_path}",
            "owner": {"type": "team", "name": "data-engineering"},
            "tier": "Tier2",
            "tags": ["airflow", "gitlab"],
            "metadata": {
                "dag_files": dag_files
            }
        }

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    client = GitLabClient()
    dags = client.fetch_dags()
    import json
    with open("src/data_platform/pipelines.json", "w", encoding="utf-8") as f:
        json.dump(dags, f, indent=2, ensure_ascii=False)
    print("Done writing to pipelines.json")
