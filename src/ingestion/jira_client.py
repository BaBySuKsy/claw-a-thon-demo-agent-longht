import os
import logging
from atlassian import Jira
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

class JiraClient:
    """
    Standard Wrapper for Jira Cloud/Data Center API using atlassian-python-api.
    """
    def __init__(self, url=None, user=None, token=None):
        self.url = url or os.getenv("JIRA_URL", "")
        self.user = user or os.getenv("JIRA_USER")
        self.token = token or os.getenv("JIRA_TOKEN")
        
        # Use token as PAT (ignore user as suggested for Data Center)
        self.client = Jira(
            url=self.url,
            token=self.token,
            cloud=False
        )

    def authenticate(self) -> bool:
        """
        Validate Jira connection.
        """
        try:
            # We can search with an empty JQL to verify connection or get current user
            self.client.jql("order by created DESC", limit=1)
            logger.info("Jira authenticated successfully.")
            return True
        except Exception as e:
            logger.error(f"Jira authentication failed: {e}")
            return False
