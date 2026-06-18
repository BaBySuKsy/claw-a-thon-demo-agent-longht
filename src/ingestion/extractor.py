import json
import logging
from src.ingestion.datahub_client import DataHubClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class IngestionOrchestrator:
    """
    Orchestrates extraction. Currently focusing on DataHub -> datasets.json.
    """
    def __init__(self):
        self.datahub = DataHubClient()

    def run_pipeline(self):
        logger.info("Starting ingestion pipeline for DataHub...")
        
        # 1. Authenticate
        if not self.datahub.authenticate():
            logger.error("Failed to authenticate DataHub")
            return
            
        # 2. Extract Data
        logger.info("Extracting data from DataHub (HDFS, active, no-test)...")
        # Let's fetch 50 datasets for our local JSON store
        datasets = self.datahub.fetch_datasets()
        
        # 3. Save to JSON
        dataset_path = "src/data_platform/datasets.json"
        logger.info(f"Saving {len(datasets)} datasets to {dataset_path}")
        with open(dataset_path, "w", encoding="utf-8") as f:
            json.dump(datasets, f, indent=2, ensure_ascii=False)
            
        # 4. Extract GitLab Pipelines
        logger.info("Extracting data from GitLab (Airflow Repos)...")
        from src.ingestion.gitlab_client import GitLabClient
        gitlab_client = GitLabClient()
        if gitlab_client.authenticate():
            pipelines = gitlab_client.fetch_dags()
            pipeline_path = "src/data_platform/pipelines.json"
            logger.info(f"Saving {len(pipelines)} pipelines to {pipeline_path}")
            with open(pipeline_path, "w", encoding="utf-8") as f:
                json.dump(pipelines, f, indent=2, ensure_ascii=False)
        else:
            logger.error("Failed to authenticate GitLab")
            
        logger.info("Extraction complete!")

if __name__ == "__main__":
    orchestrator = IngestionOrchestrator()
    orchestrator.run_pipeline()
