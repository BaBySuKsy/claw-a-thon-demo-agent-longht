import json
from pathlib import Path

def generate_mock_jira_data():
    cache_dir = Path("src/data_platform/cache/jira")
    cache_dir.mkdir(parents=True, exist_ok=True)
    
    # 1. Epic PDPDW-100
    epic_1 = {
        "epic_key": "PDPDW-100",
        "project": "PDPDW",
        "summary": "Data Warehouse Modernization 2026",
        "description": "Upgrade Redshift clusters and migrate old Airflow DAGs.",
        "status": "In Progress",
        "created_at": "2025-02-15T08:00:00Z",
        "tickets": [
            {
                "ticket_key": "PDPDW-105",
                "issuetype": "Task",
                "summary": "Migrate User Dimension to new Tier 1",
                "description": "Refactor user_dim SQL to use new Spark engine.",
                "status": "Done",
                "assignee": {"name": "Data Engineer 1"},
                "created_at": "2026-01-15T14:00:00Z",
                "labels": ["migration", "tier1"]
            },
            {
                "ticket_key": "PDPDW-106",
                "issuetype": "Bug",
                "summary": "Data mismatch in transaction fact",
                "description": "Fix reconciliation issue in tx_fact.",
                "status": "Open",
                "assignee": {"name": "Data Quality Engineer"},
                "created_at": "2026-02-10T09:00:00Z",
                "labels": ["bug", "data-quality"]
            }
        ]
    }
    
    # 2. Epic PCDCM-200
    epic_2 = {
        "epic_key": "PCDCM-200",
        "project": "PCDCM",
        "summary": "Data Collection Framework 2.0",
        "description": "Implement real-time Kafka connectors for new Data Collection Model.",
        "status": "Open",
        "created_at": "2025-11-20T10:00:00Z",
        "tickets": [
            {
                "ticket_key": "PCDCM-205",
                "issuetype": "Story",
                "summary": "Build Kafka Sink for Payments",
                "description": "Route payment events to HDFS.",
                "status": "In Progress",
                "assignee": {"name": "Data Engineer 2"},
                "created_at": "2026-03-01T11:00:00Z",
                "labels": ["kafka", "realtime"]
            }
        ]
    }
    
    # 3. Other Tickets (No Epic)
    other_epic = {
        "epic_key": "OTHER",
        "project": "MIXED",
        "summary": "Tickets without an Epic (Created >= 2026-01-01)",
        "tickets": [
            {
                "ticket_key": "PDPDW-999",
                "issuetype": "Task",
                "summary": "Ad-hoc data dump for Marketing",
                "description": "Export user list for campaign.",
                "status": "Done",
                "assignee": {"name": "Data Analyst"},
                "created_at": "2026-04-05T15:00:00Z",
                "labels": ["ad-hoc"]
            },
            {
                "ticket_key": "PCDCM-888",
                "issuetype": "Bug",
                "summary": "Kafka topic lag alert",
                "description": "Consumer group is lagging.",
                "status": "Open",
                "assignee": {"name": "Data Ops"},
                "created_at": "2026-05-12T08:30:00Z",
                "labels": ["alert"]
            }
        ]
    }
    
    with open(cache_dir / "PDPDW-100.json", "w", encoding="utf-8") as f:
        json.dump(epic_1, f, indent=2, ensure_ascii=False)
        
    with open(cache_dir / "PCDCM-200.json", "w", encoding="utf-8") as f:
        json.dump(epic_2, f, indent=2, ensure_ascii=False)
        
    with open(cache_dir / "other_epic.json", "w", encoding="utf-8") as f:
        json.dump(other_epic, f, indent=2, ensure_ascii=False)
        
    print("Mock Jira data generated successfully according to the strict schema design.")

if __name__ == "__main__":
    generate_mock_jira_data()
