import os
import requests
import logging
from typing import Dict, Any, List
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

class DataHubClient:
    """
    Client to connect to DataHub using username/password login.
    Uses GraphQL to fetch entities.
    """
    def __init__(self):
        self.base_url = os.getenv("DATAHUB_BASE_URL", "").rstrip('/')
        self.username = os.getenv("DATAHUB_USERNAME")
        self.password = os.getenv("DATAHUB_PASSWORD")
        self.session = requests.Session()

    def authenticate(self) -> bool:
        if not self.username or not self.password:
            logger.error("DataHub credentials missing.")
            return False
            
        login_url = f"{self.base_url}/logIn"
        payload = {"username": self.username, "password": self.password}
        
        try:
            res = self.session.post(login_url, json=payload, timeout=10)
            if res.status_code == 200:
                logger.info("DataHub authenticated successfully via /logIn.")
                return True
            else:
                logger.error(f"DataHub auth failed: {res.status_code}")
                return False
        except Exception as e:
            logger.error(f"DataHub connection exception: {e}")
            return False

    def fetch_datasets(self) -> List[Dict[str, Any]]:
        """
        Fetch specific HDFS datasets (acme.analytics, acme.secure, zds)
        Filter out 'test' and DEPRECATED ones.
        Supports pagination to get all records.
        """
        query = '''
        query SearchDatasets($start: Int!, $count: Int!) {
          search(input: {
            type: DATASET, 
            query: "*", 
            orFilters: [{
              and: [{field: "platform", values: ["urn:li:dataPlatform:hdfs"]}]
            }],
            start: $start, 
            count: $count
          }) {
            total
            searchResults {
              entity {
                urn
                ... on Dataset {
                  properties { name description }
                  status { removed }
                  ownership { owners { owner { ... on CorpUser { urn } ... on CorpGroup { urn } } } }
                  schemaMetadata { fields { fieldPath nativeDataType } }
                  tags { tags { tag { urn } } }
                  upstream: lineage(input: {direction: UPSTREAM}) { relationships { entity { urn } } }
                  downstream: lineage(input: {direction: DOWNSTREAM}) { relationships { entity { urn } } }
                }
              }
            }
          }
        }
        '''
        
        graphql_url = f"{self.base_url}/api/graphql"
        import time
        normalized_datasets = []
        
        start = 0
        batch_size = 100
        total = 1  # Will be updated on first response
        
        while start < total:
            logger.info(f"Fetching DataHub GraphQL (start: {start})...")
            res = self.session.post(graphql_url, json={"query": query, "variables": {"start": start, "count": batch_size}}, timeout=10)
            
            if res.status_code != 200:
                logger.error(f"GraphQL error: {res.status_code} - {res.text}")
                break
                
            json_res = res.json()
            if "errors" in json_res:
                logger.error(f"GraphQL returned errors: {json_res['errors']}")
                break
                
            search_block = json_res.get("data", {}).get("search", {})
            total = search_block.get("total", 0)
            data = search_block.get("searchResults", [])
            
            if not data:
                break
                
            for item in data:
                entity = item.get("entity", {})
                urn = entity.get("urn", "")
                if not urn:
                    continue
                    
                # Active filter
                status = entity.get("status") or {}
                if status.get("removed", False) is True:
                    continue
                    
                props = entity.get("properties") or {}
                name = props.get("name", "")
                
                # Prefix filter
                is_zds = False
                if name.startswith("acme.analytics.") or name.startswith("acme.secure."):
                    pass
                elif name.startswith("zds."):
                    is_zds = True
                else:
                    continue
                
                # Parse tags early for filtering
                tags_data = entity.get("tags") or {}
                tags_list = tags_data.get("tags", [])
                clean_tags = [t.get("tag", {}).get("urn", "").split(":")[-1] for t in tags_list]
                
                # Test & Deprecated filter
                if not is_zds:
                    if "test" in name.lower():
                        continue
                    if any(t.lower() == "deprecated" for t in clean_tags):
                        continue
                
                # --- Hierarchical Parsing ---
                platform = "hdfs"
                parts = name.split(".")
                hierarchy = [platform] + parts
                domain = parts[2] if len(parts) > 2 else "unknown"
                
                # Parse ownership
                ownership = entity.get("ownership") or {}
                owners_list = ownership.get("owners", [])
                owner_urn = owners_list[0].get("owner", {}).get("urn", "unknown") if owners_list else "unknown"
                owner_name = owner_urn.split(":")[-1] if ":" in owner_urn else owner_urn
                
                # Parse schema
                schema_data = entity.get("schemaMetadata") or {}
                fields = schema_data.get("fields", [])
                columns = [{"name": f.get("fieldPath"), "type": f.get("nativeDataType")} for f in fields]
                
                # Parse lineage
                upstreams = entity.get("upstream", {}).get("relationships", [])
                downstreams = entity.get("downstream", {}).get("relationships", [])
                up_urns = [u.get("entity", {}).get("urn") for u in upstreams]
                down_urns = [d.get("entity", {}).get("urn") for d in downstreams]
                
                dataset = {
                    "id": urn,
                    "name": name,
                    "type": "dataset",
                    "description": props.get("description", "No description provided"),
                    "owner": {
                        "type": "user",
                        "name": owner_name
                    },
                    "domain": domain,
                    "tier": "Tier2" if "core" in clean_tags else "Tier3",
                    "tags": clean_tags,
                    "upstream": up_urns,
                    "downstream": down_urns,
                    "metadata": {
                        "hierarchy": hierarchy,
                        "columns": columns
                    }
                }
                normalized_datasets.append(dataset)
            
            start += batch_size
            time.sleep(1)
            
        return normalized_datasets

    def fetch_dataset_by_urn(self, urn: str) -> Dict[str, Any]:
        """
        Fetch a single dataset by its URN for Just-In-Time verification.
        """
        if not self.session.cookies:
            self.authenticate()
            
        query = '''
        query GetDataset($urn: String!) {
          dataset(urn: $urn) {
            urn
            properties { name description }
            status { removed }
            ownership { owners { owner { ... on CorpUser { urn } ... on CorpGroup { urn } } } }
            schemaMetadata { fields { fieldPath nativeDataType } }
            tags { tags { tag { urn } } }
            upstream: lineage(input: {direction: UPSTREAM}) { relationships { entity { urn } } }
            downstream: lineage(input: {direction: DOWNSTREAM}) { relationships { entity { urn } } }
          }
        }
        '''
        graphql_url = f"{self.base_url}/api/graphql"
        res = self.session.post(graphql_url, json={"query": query, "variables": {"urn": urn}}, timeout=10)
        
        if res.status_code != 200:
            return None
            
        json_res = res.json()
        if "errors" in json_res:
            return None
            
        entity = json_res.get("data", {}).get("dataset")
        if not entity:
            return None
            
        # Parse logic same as batch
        status = entity.get("status") or {}
        if status.get("removed", False) is True:
            return None
            
        props = entity.get("properties") or {}
        name = props.get("name", "")
        
        # tags
        tags_data = entity.get("tags") or {}
        tags_list = tags_data.get("tags", [])
        clean_tags = [t.get("tag", {}).get("urn", "").split(":")[-1] for t in tags_list]
        
        # hierarchy
        platform = "unknown"
        if "urn:li:dataPlatform:" in urn:
            platform = urn.split("urn:li:dataPlatform:")[1].split(",")[0]
        parts = name.split(".")
        hierarchy = [platform] + parts
        domain = parts[2] if len(parts) > 2 else "unknown"
        
        # ownership
        ownership = entity.get("ownership") or {}
        owners_list = ownership.get("owners", [])
        owner_urn = owners_list[0].get("owner", {}).get("urn", "unknown") if owners_list else "unknown"
        owner_name = owner_urn.split(":")[-1] if ":" in owner_urn else owner_urn
        
        # schema
        schema_data = entity.get("schemaMetadata") or {}
        fields = schema_data.get("fields", [])
        columns = [{"name": f.get("fieldPath"), "type": f.get("nativeDataType")} for f in fields]
        
        # lineage
        upstreams = entity.get("upstream", {}).get("relationships", [])
        downstreams = entity.get("downstream", {}).get("relationships", [])
        up_urns = [u.get("entity", {}).get("urn") for u in upstreams]
        down_urns = [d.get("entity", {}).get("urn") for d in downstreams]
        
        return {
            "id": urn,
            "name": name,
            "type": "dataset",
            "description": props.get("description", "No description provided"),
            "owner": {
                "type": "user",
                "name": owner_name
            },
            "domain": domain,
            "tier": "Tier2" if "core" in clean_tags else "Tier3",
            "tags": clean_tags,
            "upstream": up_urns,
            "downstream": down_urns,
            "metadata": {
                "hierarchy": hierarchy,
                "columns": columns
            }
        }

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    client = DataHubClient()
    if client.authenticate():
        datasets = client.fetch_datasets(limit=5)
        import json
        print(json.dumps(datasets, indent=2))
