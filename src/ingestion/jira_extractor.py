import os
import json
import logging
import asyncio
import aiohttp
import base64
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class JiraExtractor:
    def __init__(self):
        self.url = os.getenv("JIRA_URL", "")
        self.user = os.getenv("JIRA_USER")
        self.token = os.getenv("JIRA_TOKEN") or os.getenv("JIRA_API_TOKEN")
        self.cache_dir = Path("src/data_platform/cache/jira")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.session = None

    def get_headers(self):
        if not self.token:
            return {"Accept": "application/json"}
            
        return {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/json",
            "Content-Type": "application/json"
        }

    async def init_session(self):
        if not self.session:
            self.session = aiohttp.ClientSession(headers=self.get_headers())

    async def close_session(self):
        if self.session:
            await self.session.close()

    async def fetch_issues_jql(self, jql: str):
        """Fetch all issues matching a JQL query."""
        issues = []
        start_at = 0
        max_results = 100
        
        while True:
            payload = {
                "jql": jql,
                "startAt": start_at,
                "maxResults": max_results,
                "fields": ["summary", "description", "status", "issuetype", "created", "assignee", "labels", "customfield_10101", "epic"]
            }
            
            endpoint = f"{self.url}/rest/api/2/search"
            try:
                async with self.session.post(endpoint, json=payload) as res:
                    if res.status == 200:
                        data = await res.json()
                        fetched = data.get("issues", [])
                        issues.extend(fetched)
                        
                        if start_at + max_results >= data.get("total", 0):
                            break
                        start_at += max_results
                    else:
                        logger.error(f"Jira API error: {res.status}")
                        break
            except Exception as e:
                logger.error(f"Error fetching JQL {jql}: {e}")
                break
                
        return issues

    def build_ticket_schema(self, issue: dict):
        """Standardize the Ticket Schema."""
        fields = issue.get("fields", {})
        assignee = fields.get("assignee")
        status = fields.get("status", {})
        issuetype = fields.get("issuetype", {})
        
        epic_link = None
        if "epic" in fields and fields["epic"]:
            epic_link = fields["epic"].get("key")
        elif "customfield_10101" in fields and fields["customfield_10101"]:
             epic_link = fields["customfield_10101"]

        return {
            "ticket_key": issue.get("key"),
            "issuetype": issuetype.get("name", "Unknown"),
            "summary": fields.get("summary", ""),
            "description": fields.get("description", "") or "",
            "status": status.get("name", "Open"),
            "assignee": {"name": assignee.get("displayName")} if assignee else None,
            "created_at": fields.get("created"),
            "labels": fields.get("labels", []),
            "epic_link": epic_link
        }

    async def run(self):
        await self.init_session()
        
        logger.info("Fetching Epics created >= 2025-01-01 in PCDCM, PDPDW...")
        epic_jql = 'project in (PCDCM, PDPDW) AND issuetype = Epic AND created >= "2025-01-01"'
        raw_epics = await self.fetch_issues_jql(epic_jql)
        
        epics_map = {}
        for e in raw_epics:
            schema = self.build_ticket_schema(e)
            epics_map[schema["ticket_key"]] = {
                "epic_key": schema["ticket_key"],
                "project": schema["ticket_key"].split("-")[0],
                "summary": schema["summary"],
                "description": schema["description"],
                "status": schema["status"],
                "created_at": schema["created_at"],
                "tickets": []
            }
            
        logger.info(f"Found {len(epics_map)} matching Epics.")
        
        logger.info("Fetching Tickets created >= 2026-01-01 in PCDCM, PDPDW...")
        ticket_jql = 'project in (PCDCM, PDPDW) AND issuetype != Epic AND created >= "2026-01-01"'
        raw_tickets = await self.fetch_issues_jql(ticket_jql)
        
        other_epic = {
            "epic_key": "OTHER",
            "project": "MIXED",
            "summary": "Tickets without an Epic (Created >= 2026-01-01)",
            "tickets": []
        }
        
        for t in raw_tickets:
            schema = self.build_ticket_schema(t)
            epic_link = schema.get("epic_link")
            
            del schema["epic_link"]
            
            if epic_link and epic_link in epics_map:
                epics_map[epic_link]["tickets"].append(schema)
            else:
                other_epic["tickets"].append(schema)
                
        logger.info(f"Found {len(raw_tickets)} matching Tickets.")
        logger.info(f"Assigned {len(other_epic['tickets'])} tickets to other_epic.json")
        
        for epic_key, epic_data in epics_map.items():
            filepath = self.cache_dir / f"{epic_key}.json"
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(epic_data, f, indent=2, ensure_ascii=False)
                
        if other_epic["tickets"]:
            filepath = self.cache_dir / "other_epic.json"
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(other_epic, f, indent=2, ensure_ascii=False)
                
        logger.info(f"Saved {len(epics_map) + (1 if other_epic['tickets'] else 0)} JSON files to {self.cache_dir}")
        await self.close_session()

if __name__ == "__main__":
    extractor = JiraExtractor()
    asyncio.run(extractor.run())
