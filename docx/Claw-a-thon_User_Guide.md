# GreenNode Claw-a-thon 2026 | Official Contestant User Guide

Welcome, Starters! To receive prompt answers and support, please join the official Microsoft Teams group of the contest to receive announcements, documents, and important updates from the Organizing Committee (BOC): [Join Teams Group](https://teams.microsoft.com/) (Placeholder Link).

---

## Section 1: Rulebook & Submission Guide

### 1.1. Read the Rulebook Before Building
Before you start, all Starters must carefully read the rulebook to ensure a safe and successful agent building journey.
*   **Official Rulebook:** [https://greennode.ai/claw-a-thon-rulebook](https://greennode.ai/claw-a-thon-rulebook)

### 1.2. Submission Requirements
*   **Deadline:** June 17, 2026, at 12:00 PM (GMT+7/Vietnam Time).
*   **Deliverables:** Each team must submit all of the following deliverables (items 1–3 are mandatory, item 4 is optional):
    1.  **Agent Source Code on GitHub:** A link to the agent's repository on GitHub containing the complete source code and documentation.
    2.  **Demo Video:** A 2–3 minute demo video demonstrating the agent operating in practice.
    3.  **Use Case Description:** A 100–200 word use case description explaining what problem the agent solves.
    4.  **Agent Endpoint (Optional):** A link to try/test the agent (Only applicable to web-based agents).

⚠️ **Critical Note:** All links (GitHub repository and demo video) must be set to public at the time of submission and throughout the voting period. Private links will invalidate the submission.

*   **Submission Portal:** [https://greennode.ai/events/greennode-claw-a-thon](https://greennode.ai/events/greennode-claw-a-thon)
    *(Note: The submission link will open after the Training Workshop).*

### 1.3. Post-Submission Workflow
*   **Pre-deadline Revisions:** After submission, teams can edit their submitted content until June 17, 2026, at 12:00 PM. The form will close after this time.
*   **BOC Review Results:** The BOC will review all submissions and return a Pass/Fail result:
    *   **Pass:** The submission is kept as is, with no further edits allowed.
    *   **Fail:** The team will receive an email from the BOC containing the reason and a link to edit/resubmit the project. The editing deadline is until the end of June 18, 2026. After reviewing resubmitted projects, the pass/fail results will be updated on June 19, 2026.
*   **Voting Phase:** The voting page will open on June 22, 2026, at 9:00 AM.

---

## Section 2: Environment Setup & Prerequisites

Before building and deploying your agent, Starters need to install the following toolsets to assist in the agent building and deployment process:

*   **Docker Desktop App (Official Build):** Docker will be used to deploy the agent to AgentBase during the contest.
    *   [Download Docker Desktop](http://docs.docker.com/get-started/introduction/get-docker-desktop/)
    *   *Note:* On some devices, especially Windows machines, the virtualization feature might be disabled, leading to unsuccessful Docker installation or execution. If you need support, please contact the IT Helpdesk to check and resolve it before participating in the training.
*   **GitHub Desktop App:** Helps you interact with source code easily, especially for those not familiar with using Git via command line.
    *   [Download GitHub Desktop](https://desktop.github.com/download/)
*   **GitHub Account:** Each participant is requested to pre-create a GitHub account to manage the agent repository and work with their team throughout the contest.
    *   [Sign Up](https://github.com/signup)
*   **Git CLI:** Git CLI will support basic operations with the agent's source code as well as GreenNode's AgentBase skillset.
    *   [Install Git CLI](https://git-scm.com/install/)

---

## Section 3: Technical Resources & Documentation

### 3.1. Webinar Recordings
Two recorded webinars to watch based on your needs — choose the webinar that fits your current phase:
*   **Claw-a-thon Orientation Webinar:** Watch the recording of Webinar #1 [HERE](webinar_1_link_placeholder).
    *   *When to watch:* When you want to get an overview of the contest — rules, timeline, grading criteria, and submission guide.
*   **Webinar 02: From Prompt to Executable Agent:** Watch the recording of Webinar #2 [HERE](webinar_2_link_placeholder).
    *   *When to watch:* When you start building — to understand the workflow of moving from an idea/prompt to a running agent.

### 3.2. Official GreenNode Links and Support Documentation
Official resources you will use throughout the contest — each link comes with a note on when to use it:
*   **GreenNode AI Portal:** [https://aiplatform.console.vngcloud.vn/](https://aiplatform.console.vngcloud.vn/)
    *   *When to use:* Access API keys, configure IAM accounts, adjust credit wallets, or verify if the agent is running stably on AgentBase with the Runtime, Access Control, and Memory modules.
    *   *Security Note:* Upon first login, you must access the GreenNode AI Platform and change your password. This step is mandatory to ensure the security of your team's account and resources.
*   **AgentBase User Guide:** [https://docs.vngcloud.vn/vng-cloud-document/vn/ai-stack/agent-base](https://docs.vngcloud.vn/vng-cloud-document/vn/ai-stack/agent-base)
    *   *When to use:* Refer to step-by-step instructions on the Portal and learn about the functions and roles of each module within AgentBase for deploying your agent.
*   **Latest AgentBase Skillset:** [https://github.com/vngcloud/greennode-agentbase-skills](https://github.com/vngcloud/greennode-agentbase-skills)
    *   *When to use:* Easily deploy your local agent to the AgentBase cloud platform by importing/cloning this skillset into your working agent directory. This skillset is deployed completely automatically without requiring pre-setup on the GreenNode portal. Compatible with most popular vibe code tools, CLI, and IDEs.
*   **Sample Agent Repository:** [vngcloud/clawathon-2026-sample-agents](https://github.com/vngcloud/clawathon-2026-sample-agents)
    *   *When to use:* Provided as a reference for structure and build instructions before doing it yourself. Samples are for reference only, are not the only correct structure, and copying them exactly (plagiarism) is not allowed.
*   **BOC Guidance Channels & Tool Access Request:** [https://workdrive.zohoexternal.com/file/5gca089643260c84a4ea2b82970cdec9f8159](https://workdrive.zohoexternal.com/file/5gca089643260c84a4ea2b82970cdec9f8159)

---

## Section 4: Best Practice Guide

Tips and experiences to build high-quality AI agents in 7 days.

### 4.1. Best Practices
A few skills and tips to refer to for fast and high-quality agent building:
*   **Agent Build Skill:** Refer to the [Superpowers Plus](https://github.com/khoapnt-vng/superpowers-plus-greennode-agentbase) tool for accelerated agent development.

### 4.2. GreenNode AI Portal Tips
*   **Wallet Credit Management:** Each team is allocated a Main Wallet (default 5 million credits) and a MaaS (Model-as-a-Service) Wallet (default 5 million credits). The MaaS wallet is consumed when calling AI models. When the MaaS wallet is empty, you can transfer more credits from the Main Wallet.
    *   *Important Note:* Only transfer just enough. Keep a minimum of 2 million credits in the Main Wallet for other services (runtime, container registry, openclaw one-click). Wallet credit transfers are non-refundable, so consider carefully before transferring.
    *   [MaaS Wallet Pricing & Transfer Guide](https://docs.vngcloud.vn/vng-cloud-document/ai-stack/ai-platform/model-as-a-service/pricing)
*   **IAM Accounts:** The BOC has pre-created IAM accounts for all teams and emailed the credentials to each team. If you need to create additional IAM accounts, refer to the guide below to create them based on your needs:
    *   [IAM Account Setup Guide](https://docs.vngcloud.vn/vng-cloud-document/datasync/quan-ly-truy-cap/quan-ly-tai-khoan-truy-cap-datasync/tai-khoan-nguoi-dung-iam/khoi-tao-tai-khoan-iam-user-account)
*   **Model Integration in Vibe Code Tools:** If you want to use GreenNode's models in vibe code tools (such as Claude CLI, Codex CLI), refer to the instructions below:
    *   [GreenNode Model Switching Guide](https://docs.vngcloud.vn/vng-cloud-document/vn/ai-stack/agent-base/ai-coding)

---

## Section 5: Troubleshooting

A compilation of common errors encountered during agent building and how to resolve them:

### 5.1. Accounts & Access
*   **Issue:** Do I need a paid account (such as Claude Teams/Enterprise or ChatGPT Plus) to build the agent?
*   **Solution:** No. If you do not have paid features like Claude Cowork or Claude Code, you can still use Codex (free tier). Additionally, many IDEs (like Visual Studio Code or Antigravity) support extensions that allow you to chat and "vibe code" using free models.

### 5.2. Git & AgentBase Skillset Repository Access
*   **Issue:** The repository is reported as private when executing `git clone` for the AgentBase skillset.
*   **Solution:** This error usually occurs when Git CLI or GitHub Desktop is not installed on your machine.
    *   *Workaround:* You can download the skillset directly from the GitHub page (as a ZIP file) and extract it into your agent build folder instead of cloning it.
    *   *Note:* You should still install Git CLI or GitHub Desktop, as they will be required later to push your agent source code to GitHub.
    *   *Inconsistent Reference Warning:* The original document mentions checking "How to push repo to Github với Claude Cowork", but this section does not exist anywhere in the user guide. If using Claude Cowork, please refer to standard Git/GitHub instructions for pushing repositories.
*   **Issue:** "Git is required for local sessions" error in Claude Code.
*   **Solution:** This error occurs when Git CLI is not installed and you select a folder and import the AgentBase skillset link in Claude Code. To resolve, install Git CLI from [https://git-scm.com/install/](https://git-scm.com/install/).

### 5.3. Folder Structure & Workspace Architecture
*   **Issue:** Agent and AgentBase skillset must be stored in the same folder.
*   **Solution:** When creating an agent, you need a folder to store the agent's source code, and the AgentBase skillset must be imported (or cloned) into that exact same folder. If they are in different folders, the agent build and skillset execution may fail.
    *   *Tip:* When starting, you can prompt the AI: *"Create a local folder to house the agent."*
*   **Issue:** Agent does not run when the folder is not stored locally.
*   **Solution:** Running the agent from folders like `Downloads` may cause issues. To ensure tools can access your agent folder, place it in a fixed local directory (e.g., `Documents` or a dedicated workspace folder) and specify this path clearly to the AI.

### 5.4. Tools & Extensions
*   **Issue:** How to install the Claude Code extension for VSCode?
*   **Solution:** IDEs support installing extensions like Claude Code and Codex. To use Claude Code or Codex directly inside Visual Studio Code or Antigravity, simply install the corresponding extension to begin building your agent.
*   **Issue:** AI prompts to update Node.js or Python because of outdated versions when running the skillset.
*   **Solution:** If your machine runs an outdated version of Node.js or Python, Claude or Codex may ask to upgrade during the skillset execution. Approve the request, and the tool will automatically update to the appropriate version and proceed.
*   **Issue:** WSL update error when installing Docker.
*   **Solution:** Copy the terminal command shown in the error message, open your terminal, and run it. Once the Linux (WSL) installation completes successfully, you can proceed with Docker installation.
    *   *Error 403 Forbidden:* If you encounter a 403 Forbidden error, it is usually because the virtualization feature (Hyper-V) is not enabled on your machine. Contact your IT Helpdesk for support.

### 5.5. AgentBase Deployment Pipeline
*   **Issue:** Deploying an empty agent to AgentBase during skillset execution before building the agent.
*   **Solution:** The deployment skillset follows a 9-step process. If you run through the entire process before your agent's use case is built, the agent will be deployed but will remain "hollow" (runtime and access control are set up, but the agent lacks actual functionality).
    *   *Recommended Flow:* If building the agent from the skillset link, **PAUSE** after entering your credentials (Step 1 of the 9-step process) to build your agent's logic first. Resume Step 2 only after the agent logic is complete.
    *   *Alternative Flow:* Use vibe coding tools to build the agent first, then import (or clone) the AgentBase skillset and run the deployment steps.
*   **Issue:** Cannot share the agent link publicly.
*   **Solution:** After building and running the agent locally, when you deploy it to the runtime, the access link might still point to `localhost` (accessible only on your machine). Opening this link in another browser or sending it to others will show a "Not Found" error.
    *   *Fix:* Prompt the AI to *"switch the endpoint to public mode"* to generate a shareable, active URL. This is the link you will share for other Starters to experience your agent.

### 5.6. IAM Credentials
*   **Issue:** IAM credential authentication fails (invalid/missing credentials).
*   **Solution:** When the system reports authentication failure, double-check if your copied credentials contain leading/trailing spaces or missing characters, and enter them again.

### 5.7. Agent Memory
*   **Issue:** Agent memory is saved locally instead of pushed to AgentBase.
*   **Solution:** When building an agent locally, AI tools often suggest saving memory in a local `memory.md` file. However, for stable and long-term memory retrieval, you should upload it to the AgentBase Memory module. This ensures the memory is stored centrally, long-term, and is not lost if you switch machines.
    *   *Action:* Prompt the agent to *"push memory from my machine to the AgentBase Memory module"*; the skillset will automatically handle this task.
