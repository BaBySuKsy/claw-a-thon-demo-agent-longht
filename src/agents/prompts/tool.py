# Tool definitions following OpenAI function calling specification.
# These are injected into the LLM context to enable tool-calling capability.

# Legacy prompt strings (kept for backward compatibility)
DATA_DISCOVERY_PROMPT = """
Analyze the query to identify if the user is looking for a dataset, a pipeline, or an owner.
"""

IMPACT_ANALYSIS_PROMPT = """
Guide the impact analysis traversal based on the identified target entity.
"""

# ──────────────────────────────────────────────────────────────────────────────
# OpenAI-compatible tool schemas for MiniMax-M2.5 function calling
# ──────────────────────────────────────────────────────────────────────────────

TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "search_metadata",
            "description": (
                "Search for metadata about a dataset, pipeline, table, or any data entity "
                "by name or description. Use this when the user asks 'What is X?', "
                "'Tell me about X', 'Who uses X?', or wants general info about an entity."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": (
                            "The search term: can be a table name (e.g. 'user_dim'), "
                            "a pipeline name, or a descriptive phrase (e.g. 'user session data')."
                        ),
                    }
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_platform_overview",
            "description": (
                "Get a curated, structured overview of the entire Acme Data Platform in ONE call: "
                "business domains (Lending/Credit, Payment/QrPay, Identity, Merchant/Partner, Infra), their key "
                "Tier1 tables, key pipelines, must-read docs, the owning team, and the Tier system. "
                "ALWAYS use this FIRST for onboarding / orientation questions like 'tôi mới join, bắt đầu "
                "từ đâu?', 'where do I start?', 'how does the data platform work?', 'giới thiệu data platform', "
                "'các domain chính là gì?'. Prefer this over multiple search_metadata calls."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "domain": {
                        "type": "string",
                        "description": (
                            "Optional filter to one domain, e.g. 'lending', 'payment', 'identity', 'merchant'. "
                            "Omit to get all domains."
                        ),
                    }
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_ownership",
            "description": (
                "Retrieve the owner (team and/or person) and domain of a specific entity "
                "by its full entity ID. Use this when the user asks 'Who owns X?', "
                "'Which team is responsible for X?', or 'Who do I contact about X?'."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "entity_id": {
                        "type": "string",
                        "description": (
                            "Entity ID or short table/pipeline name, e.g. 'loan_core_statement' "
                            "or a full DataHub URN. Short names are auto-resolved."
                        ),
                    }
                },
                "required": ["entity_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_entity_details",
            "description": (
                "Retrieve the full details and schema of a specific entity by its full entity ID. "
                "This tool performs Just-In-Time (JIT) freshness verification to ensure the data "
                "is up-to-date. Use this when the user asks for the schema, columns, or full details "
                "of a specific entity."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "entity_id": {
                        "type": "string",
                        "description": (
                            "The full entity ID, e.g. 'urn:li:dataset:(urn:li:dataPlatform:hdfs,name,PROD)'."
                        ),
                    }
                },
                "required": ["entity_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "analyze_impact",
            "description": (
                "Analyze the full downstream impact of changing a specific dataset or table. "
                "Returns all affected downstream entities (tables, pipelines, dashboards) "
                "with their tier classification. Use this when the user asks 'If I change X, "
                "what breaks?', 'What is the impact of modifying X?', or 'What depends on X?'."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "entity_id": {
                        "type": "string",
                        "description": (
                            "Dataset/table name or full URN to analyze, e.g. 'loan_core_statement'. "
                            "Short names are auto-resolved."
                        ),
                    }
                },
                "required": ["entity_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_gitlab_file",
            "description": (
                "Read the full source code or content of a specific file from a GitLab project. "
                "Performs Just-In-Time fetching, compares with local cache, and updates if changed. "
                "Use this to inspect the logic of a DAG, SQL ETL query, or README documentation."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "project_name": {
                        "type": "string",
                        "description": "The name of the GitLab project, e.g. 'airflow-cloud' or 'data-quality-svc'.",
                    },
                    "file_path": {
                        "type": "string",
                        "description": "The path to the file within the repository, e.g. 'dags/pdp-dw-datawarehouse_daily.py'.",
                    }
                },
                "required": ["project_name", "file_path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_related_context",
            "description": (
                "Retrieve all cross-source context for a specific entity: "
                "Jira tickets that requested or tracked it, Confluence documentation pages, "
                "and GitLab pipelines linked via Jira tickets. "
                "Use this when the user asks: 'Has there been a ticket for this table?', "
                "'Is someone currently working on this?', 'What documentation covers this dataset?', "
                "'Which project owns the pipeline for this table?', "
                "or 'Should I create a new table — does it already exist or is there a ticket for it?'"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "entity_id": {
                        "type": "string",
                        "description": (
                            "The full entity ID of the dataset or pipeline to look up context for. "
                            "Use search_metadata first if you don't have the ID."
                        ),
                    }
                },
                "required": ["entity_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_confluence_page",
            "description": (
                "Read the full Markdown content of a specific Confluence page by its ID. "
                "Performs Just-In-Time fetching, compares with local cache, and updates if changed. "
                "Use this to inspect documentation, guidelines, metadata standards, or architecture diagrams."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "page_id": {
                        "type": "string",
                        "description": "The Confluence Page ID, e.g. '5983249'.",
                    }
                },
                "required": ["page_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_jira_tickets",
            "description": (
                "Search Jira tickets live by full-text query (JQL). "
                "Use when user asks: 'is there a ticket for X?', 'who is working on Y?', "
                "'has this been requested before?', 'what's the status of Z?', "
                "'find open tasks related to...'. Optionally filter by status."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Text to search for in Jira ticket summaries and descriptions.",
                    },
                    "status": {
                        "type": "string",
                        "description": "Optional status filter, e.g. 'In Progress', 'Done', 'New'.",
                    },
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_recent_commits",
            "description": (
                "Get recent GitLab commits for a pipeline/project. "
                "Use when user asks: 'what changed recently in pipeline X?', "
                "'who modified this DAG?', 'any recent breaking changes?', "
                "'what did team do last week in credit-curated-etl?'."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "project_name": {
                        "type": "string",
                        "description": "GitLab project name, e.g. 'credit-curated-etl', 'data-quality-svc'.",
                    },
                    "days": {
                        "type": "integer",
                        "description": "How many days back to look. Default 7.",
                    },
                },
                "required": ["project_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_data_freshness",
            "description": (
                "Get the last update time and row count for a dataset from DataHub. "
                "Use when user asks: 'is this table up-to-date?', 'when was this last refreshed?', "
                "'how many rows does this table have?', 'is there a data delay?'."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "entity_id": {
                        "type": "string",
                        "description": "Full DataHub URN of the dataset, e.g. 'urn:li:dataset:(...)'.",
                    },
                },
                "required": ["entity_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_schema",
            "description": (
                "Get column-level schema (column names, data types, descriptions) for a dataset. "
                "Use when user asks: 'what columns does this table have?', 'show me the schema', "
                "'which columns are PII?', 'what fields are in this table?', "
                "'what data types does X use?'."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "entity_id": {
                        "type": "string",
                        "description": "Full DataHub URN or short table name, e.g. 'loan_core_statement'.",
                    },
                },
                "required": ["entity_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_health_briefing",
            "description": (
                "Generate a proactive 'Daily Data Health Briefing' — a digest of the whole "
                "Data Platform's current health: stale Tier1 tables, recent risky pipeline commits, "
                "and open Jira incidents, with an overall status. Use when the user asks for a "
                "summary/overview of platform health: 'tình hình hôm nay thế nào?', 'morning briefing', "
                "'platform health summary', 'tổng quan sức khỏe data platform', 'báo cáo trong ngày'."
            ),
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "diagnose_entity",
            "description": (
                "Run an INCIDENT TRIAGE / root-cause analysis on a table or pipeline. "
                "Correlates data freshness (stale?), recent GitLab commits on related pipelines, "
                "open Jira incidents, and downstream Tier1 impact — then returns findings, the most "
                "likely root cause, and concrete recommended actions. "
                "Use this when the user reports a PROBLEM: 'bảng X bị lỗi/chậm/delay', 'tại sao X không "
                "cập nhật?', 'X có vấn đề gì?', 'why is X stale/broken/failing?', 'debug X', "
                "'điều tra sự cố X'. Prefer this over calling freshness/commits/jira separately."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "entity_id": {
                        "type": "string",
                        "description": "Full URN or short table/pipeline name, e.g. 'loan_core_statement'.",
                    }
                },
                "required": ["entity_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_platform_alerts",
            "description": (
                "Get current proactive health alerts detected by the background monitor. "
                "Alerts cover: stale Tier1 data (not updated > 48h), recent pipeline commits "
                "that may introduce breaking changes, and open Jira incidents. "
                "Use when user asks: 'có vấn đề gì không?', 'data có bị delay không?', "
                "'có alert nào không?', 'stale tables?', 'any incidents on the platform?', "
                "'check platform health', 'platform status'."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "severity": {
                        "type": "string",
                        "description": "Filter by severity: 'critical', 'warning', or 'info'. Omit to return all.",
                    },
                    "entity_id": {
                        "type": "string",
                        "description": "Filter to alerts for a specific entity name or ID fragment, e.g. 'loan_core_order'.",
                    },
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_changes_since",
            "description": (
                "TIME-TRAVEL: report what has CHANGED across the Data Platform in a recent time window — "
                "schema drift (columns added/removed/type-changed vs the known baseline — potentially "
                "BREAKING), newly stale Tier1 tables, and recent pipeline commits. "
                "Use when the user asks: 'có gì thay đổi từ hôm qua?', 'data platform có gì mới?', "
                "'what changed recently?', 'what's changed since yesterday?', 'any schema changes?', "
                "'thay đổi gần đây', 'recent changes that could break my pipeline'. "
                "This answers temporal questions a static catalog cannot."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "scope": {
                        "type": "string",
                        "description": (
                            "Optional table/domain filter, e.g. 'credit' or 'identity'. Omit for the whole platform."
                        ),
                    },
                    "hours": {
                        "type": "integer",
                        "description": "Look-back window in hours. Default 24.",
                    },
                },
                "required": [],
            },
        },
    },
]

__all__ = [
    "DATA_DISCOVERY_PROMPT",
    "IMPACT_ANALYSIS_PROMPT",
    "TOOL_DEFINITIONS",
]
