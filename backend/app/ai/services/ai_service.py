import json
import logging
from uuid import UUID
from fastapi import HTTPException, status
import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.ai.schemas import (
    LogAnalysisResponse,
    ChatResponse,
    ResolutionResponse,
    IncidentSummaryResponse,
    SOPResponse,
    RCAResponse,
)
from app.incidents.repositories.incident_repository import IncidentRepository

settings = get_settings()
logger = logging.getLogger("ai_service")

# AI Provider configuration
AI_PROVIDER = getattr(settings, "AI_PROVIDER", "ollama")  # "ollama" or "bedrock"

# Ollama settings
OLLAMA_BASE_URL = getattr(settings, "OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = getattr(settings, "OLLAMA_MODEL", "llama3.2:1b")

# Bedrock settings
BEDROCK_REGION = getattr(settings, "AWS_REGION", "us-east-1")
BEDROCK_MODEL = getattr(settings, "BEDROCK_MODEL", "anthropic.claude-3-5-sonnet-20241022-v2:0")


# ─── System Prompts ─────────────────────────────────────────────────────────────

SYSTEM_PROMPTS = {
    "log_analysis": (
        "You are an expert DevOps and SRE engineer specializing in log analysis. "
        "Analyze the provided logs and identify issues, root causes, and solutions. "
        "Be precise, actionable, and concise. Always respond in valid JSON format only, no extra text."
    ),
    "resolution": (
        "You are an expert incident resolution specialist. Based on incident details, "
        "provide clear root cause analysis, step-by-step resolution, and preventive measures. "
        "Be specific and actionable. Always respond in valid JSON format only, no extra text."
    ),
    "chat": (
        "You are an expert AI assistant for an enterprise incident management platform. "
        "Your role is to help engineers and managers understand, diagnose, and resolve incidents. "
        "Rules you MUST follow:\n"
        "1. Answer directly and concisely. Never repeat the user's question back.\n"
        "2. Never prefix your response with 'USER:', 'ASSISTANT:', or any role labels.\n"
        "3. Never say 'As the user has already asked' or reference previous questions.\n"
        "4. Be technical and specific. Provide actionable steps when relevant.\n"
        "5. If incident context is provided, reference specific details from it.\n"
        "6. Format responses clearly with bullet points or numbered steps when listing items."
    ),
    "summary": (
        "You are an incident management expert. Create concise, executive-level summaries "
        "of incidents including timeline, impact, and status. Always respond in valid JSON format only, no extra text."
    ),
    "sop": (
        "You are an expert technical writer specializing in Standard Operating Procedures (SOPs) "
        "for incident management. Create clear, step-by-step procedures that any engineer can follow. "
        "Always respond in valid JSON format only, no extra text."
    ),
    "rca": (
        "You are an expert in Root Cause Analysis (RCA) using methods like 5-Whys, Fishbone diagrams, "
        "and fault tree analysis. Provide thorough, structured RCA reports. "
        "Always respond in valid JSON format only, no extra text."
    ),
}


class AIService:
    """AI-powered incident analysis and assistance using local Ollama."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.incident_repo = IncidentRepository(db)

    # ─── Log Analysis ───────────────────────────────────────────────────────────

    async def analyze_logs(self, log_content: str) -> LogAnalysisResponse:
        """Analyze log content and return structured insights."""
        prompt = f"""Analyze these production logs thoroughly. Identify the root issue, affected systems, and provide specific resolution steps with exact commands or actions an engineer should take.

```
{log_content[:8000]}
```

IMPORTANT: Be specific and technical. Reference actual error messages, timestamps, and patterns from the logs. Don't give generic advice — give actionable steps based on what you see in the logs.

Respond ONLY with this exact JSON structure (no other text):
{{
    "summary": "2-3 sentence summary of what the logs show, referencing specific errors and timestamps",
    "probable_cause": "Specific technical root cause based on log evidence",
    "severity": "low|medium|high|critical",
    "resolution_steps": ["Step 1: Specific immediate action with command", "Step 2: Next action", "Step 3: Verification", "Step 4: Prevention"],
    "affected_components": ["specific-component-1", "specific-component-2"],
    "confidence": 0.85
}}"""

        result = await self._call_ollama(
            system_prompt=SYSTEM_PROMPTS["log_analysis"],
            user_prompt=prompt,
        )

        return LogAnalysisResponse(**result)

    # ─── Resolution Suggestions ─────────────────────────────────────────────────

    async def suggest_resolution(self, incident_id: UUID) -> ResolutionResponse:
        """Generate resolution suggestions for an incident."""
        incident = await self.incident_repo.get_by_id(incident_id)
        if not incident:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Incident not found",
            )

        comments = await self.incident_repo.get_comments(incident_id)
        comments_text = "\n".join(
            [f"- {c.content}" for c in comments[:15]]
        ) if comments else "No comments yet."

        # Get attachment content (text, PDF, DOCX)
        attachments_text = await self._get_attachments_context(incident_id)

        prompt = f"""You are analyzing a production incident. Provide a thorough resolution plan with specific, actionable steps.

**Title:** {incident.title}
**Description:** {incident.description}
**Priority:** {incident.priority.value}
**Status:** {incident.status.value}
**Escalation Level:** {incident.escalation_level}

**Comments/Updates:**
{comments_text}

**Attached Files:**
{attachments_text}

IMPORTANT: Be specific and technical. Include exact commands, queries, config changes, and tools to use. Don't give generic advice — give steps an engineer can execute immediately. Reference any attached documents or logs in your analysis.

Respond ONLY with this exact JSON structure (no other text):
{{
    "summary": "2-3 sentence summary of what's happening and impact",
    "root_cause": "Specific technical root cause based on the evidence",
    "resolution_steps": ["Step 1: Specific action with command/procedure", "Step 2: Next action", "Step 3: Verification step", "Step 4: Additional step", "Step 5: Final verification"],
    "preventive_measures": ["Specific measure 1 with implementation detail", "Specific measure 2", "Specific measure 3"],
    "estimated_effort": "Realistic time estimate (e.g., '45 minutes for hotfix, 2 hours for permanent fix')",
    "confidence": 0.85
}}"""

        # Get images for vision analysis
        images = await self._get_incident_images(incident_id) if AI_PROVIDER == "bedrock" else None

        result = await self._call_ollama(
            system_prompt=SYSTEM_PROMPTS["resolution"],
            user_prompt=prompt,
            images=images,
        )

        return ResolutionResponse(**result)

    # ─── Generate SOP ───────────────────────────────────────────────────────────

    async def generate_sop(self, incident_id: UUID) -> SOPResponse:
        """Generate a Standard Operating Procedure for handling similar incidents."""
        incident = await self.incident_repo.get_by_id(incident_id)
        if not incident:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Incident not found",
            )

        comments = await self.incident_repo.get_comments(incident_id)
        comments_text = "\n".join(
            [f"- {c.content}" for c in comments[:10]]
        ) if comments else "No comments."

        # Get attachment content
        attachments_text = await self._get_attachments_context(incident_id)

        prompt = f"""Based on this incident, create a detailed, production-ready Standard Operating Procedure (SOP) that any engineer can follow step-by-step to diagnose and resolve similar incidents.

**Incident Title:** {incident.title}
**Description:** {incident.description}
**Priority:** {incident.priority.value}
**Status:** {incident.status.value}

**Comments/Findings:**
{comments_text}

**Attached Files:**
{attachments_text}

IMPORTANT GUIDELINES:
- Include 6-10 detailed steps minimum
- Each step should have a SPECIFIC action (include exact commands, SQL queries, CLI commands, config changes where applicable)
- Each expected_result should describe what the engineer should see/verify
- Prerequisites should list specific tools, access levels, and permissions needed
- Rollback procedure should have specific commands to undo changes
- Be technical and specific, not generic

Respond ONLY with this exact JSON structure (no other text):
{{
    "title": "SOP: [specific descriptive title]",
    "purpose": "Detailed explanation of why this SOP exists and what problem it solves",
    "scope": "Specific conditions/symptoms when this SOP should be used",
    "prerequisites": ["Specific tool/access 1", "Specific tool/access 2", "Specific permission 3"],
    "steps": [
        {{"step_number": 1, "action": "Specific action with exact command or procedure", "expected_result": "What you should see if successful"}},
        {{"step_number": 2, "action": "Next specific action", "expected_result": "Expected outcome"}},
        {{"step_number": 3, "action": "Continue with more steps", "expected_result": "Expected outcome"}},
        {{"step_number": 4, "action": "Verification step", "expected_result": "How to confirm resolution"}},
        {{"step_number": 5, "action": "Documentation step", "expected_result": "What to record"}},
        {{"step_number": 6, "action": "Monitoring step", "expected_result": "What to watch for"}}
    ],
    "escalation_criteria": "Specific conditions when to escalate (e.g., 'If issue persists after 30 minutes' or 'If data loss is suspected')",
    "rollback_procedure": "Step-by-step rollback with specific commands to undo all changes made",
    "notes": "Important warnings, common pitfalls, and tips from past incidents"
}}"""

        # Get images for vision analysis
        images = await self._get_incident_images(incident_id) if AI_PROVIDER == "bedrock" else None

        result = await self._call_ollama(
            system_prompt=SYSTEM_PROMPTS["sop"],
            user_prompt=prompt,
            images=images,
        )

        return SOPResponse(**result)

    # ─── Generate RCA ───────────────────────────────────────────────────────────

    async def generate_rca(self, incident_id: UUID) -> RCAResponse:
        """Generate a Root Cause Analysis report."""
        incident = await self.incident_repo.get_by_id(incident_id)
        if not incident:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Incident not found",
            )

        comments = await self.incident_repo.get_comments(incident_id)
        history = await self.incident_repo.get_history(incident_id)

        comments_text = "\n".join(
            [f"- {c.content}" for c in comments[:15]]
        ) if comments else "No comments."

        history_text = "\n".join(
            [f"- [{h.created_at.strftime('%H:%M')}] {h.field_changed}: {h.old_value} → {h.new_value}" for h in history[:10]]
        ) if history else "No changes recorded."

        # Get attachment content
        attachments_text = await self._get_attachments_context(incident_id)

        prompt = f"""Perform a thorough Root Cause Analysis (RCA) for this production incident. Use the 5-Whys technique to drill down to the fundamental root cause. Be specific and technical.

**Title:** {incident.title}
**Description:** {incident.description}
**Priority:** {incident.priority.value}
**Status:** {incident.status.value}
**Created:** {incident.created_at.strftime('%Y-%m-%d %H:%M')}
**Resolved:** {incident.resolved_at.strftime('%Y-%m-%d %H:%M') if incident.resolved_at else "Not yet resolved"}

**Timeline/Changes:**
{history_text}

**Engineer Comments/Findings:**
{comments_text}

**Attached Files:**
{attachments_text}

IMPORTANT: 
- Each "why" should dig deeper than the previous one
- Contributing factors should be specific (not generic)
- Corrective actions should be immediately actionable with specific steps
- Preventive actions should be systemic improvements
- Lessons learned should be insights the team can apply broadly

Respond ONLY with this exact JSON structure (no other text):
{{
    "incident_title": "{incident.title}",
    "summary": "3-4 sentence technical summary of the incident including impact and duration",
    "root_cause": "The fundamental technical root cause (be specific)",
    "contributing_factors": ["Specific factor 1", "Specific factor 2", "Specific factor 3", "Specific factor 4"],
    "five_whys": [
        {{"why": "Why did the incident occur?", "answer": "Specific technical answer"}},
        {{"why": "Why did [answer 1] happen?", "answer": "Deeper technical reason"}},
        {{"why": "Why did [answer 2] happen?", "answer": "Even deeper reason"}},
        {{"why": "Why did [answer 3] happen?", "answer": "Process/system gap"}},
        {{"why": "Why did [answer 4] exist?", "answer": "Fundamental root cause"}}
    ],
    "impact": "Specific business and technical impact (users affected, duration, revenue loss if applicable)",
    "timeline": ["[HH:MM] Event 1", "[HH:MM] Event 2", "[HH:MM] Event 3", "[HH:MM] Event 4"],
    "corrective_actions": ["Immediate fix 1 with specific steps", "Immediate fix 2"],
    "preventive_actions": ["Long-term systemic improvement 1", "Process change 2", "Automation 3"],
    "lessons_learned": ["Key insight 1 for the team", "Key insight 2", "Key insight 3"]
}}"""

        # Get images for vision analysis
        images = await self._get_incident_images(incident_id) if AI_PROVIDER == "bedrock" else None

        result = await self._call_ollama(
            system_prompt=SYSTEM_PROMPTS["rca"],
            user_prompt=prompt,
            images=images,
        )

        return RCAResponse(**result)

    # ─── Chat with Incident Context ─────────────────────────────────────────────

    async def chat(
        self,
        message: str,
        incident_id: UUID | None,
        conversation_history: list[dict] | None,
    ) -> ChatResponse:
        """AI chat with optional incident context."""
        messages = []

        # Add incident context if provided
        incident_context = None
        if incident_id:
            incident = await self.incident_repo.get_by_id(incident_id)
            if incident:
                # Get comments
                comments = await self.incident_repo.get_comments(incident_id)
                comments_text = "\n".join(
                    [f"- {c.content}" for c in comments[:10]]
                ) if comments else "No comments."

                # Get attachments info
                attachments_text = await self._get_attachments_context(incident_id)

                incident_context = (
                    f"Incident: {incident.title}\n"
                    f"Description: {incident.description}\n"
                    f"Priority: {incident.priority.value}\n"
                    f"Status: {incident.status.value}\n"
                    f"Escalation: Level {incident.escalation_level}\n"
                    f"\nComments:\n{comments_text}\n"
                    f"\nAttachments:\n{attachments_text}"
                )

        # Build context
        system = SYSTEM_PROMPTS["chat"]
        if incident_context:
            system += f"\n\nCurrent incident context:\n{incident_context}"

        # Add conversation history
        history_text = ""
        if conversation_history:
            for msg in conversation_history[-8:]:
                role = msg.get("role", "user")
                content = msg.get("content", "")[:1000]
                if role == "user":
                    history_text += f"\n[Question]: {content}"
                else:
                    history_text += f"\n[Answer]: {content}"

        full_prompt = ""
        if history_text:
            full_prompt = f"Previous conversation:{history_text}\n\nNew question: {message}\n\nRespond directly to the new question. Do not repeat it."
        else:
            full_prompt = f"{message}\n\nRespond directly. Do not repeat the question."

        # Call AI (unified) — include images if available
        try:
            images = None
            if incident_id and AI_PROVIDER == "bedrock":
                images = await self._get_incident_images(incident_id)
            ai_response = await self._call_ai_chat(system, full_prompt, images=images)
        except Exception as e:
            logger.error(f"AI chat error: {e}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="AI service unavailable. Check your AI_PROVIDER configuration.",
            )

        return ChatResponse(
            response=ai_response,
            incident_context=incident_context,
            suggestions=None,
        )

    # ─── Incident Summary ───────────────────────────────────────────────────────

    async def summarize_incident(self, incident_id: UUID) -> IncidentSummaryResponse:
        """Generate an executive summary of an incident."""
        incident = await self.incident_repo.get_by_id(incident_id)
        if not incident:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Incident not found",
            )

        comments = await self.incident_repo.get_comments(incident_id)
        history = await self.incident_repo.get_history(incident_id)

        timeline_entries = []
        for h in history:
            timeline_entries.append(
                f"[{h.created_at.strftime('%Y-%m-%d %H:%M')}] {h.field_changed}: {h.old_value} → {h.new_value}"
            )

        prompt = f"""Create an executive summary of this incident:

**Title:** {incident.title}
**Description:** {incident.description}
**Priority:** {incident.priority.value}
**Status:** {incident.status.value}
**Created:** {incident.created_at.strftime('%Y-%m-%d %H:%M')}
**Resolved:** {incident.resolved_at.strftime('%Y-%m-%d %H:%M') if incident.resolved_at else "Not yet"}

**Timeline:**
{chr(10).join(timeline_entries) if timeline_entries else "No recorded changes."}

**Comments ({len(comments)}):**
{chr(10).join([f"- {c.content[:200]}" for c in comments[:10]]) if comments else "None"}

Respond ONLY with this exact JSON structure (no other text):
{{
    "title_suggestion": "Improved, clear incident title",
    "executive_summary": "2-3 sentence summary for management",
    "timeline": ["key event 1", "key event 2"],
    "impact_assessment": "Business impact description",
    "current_status": "Current state and next steps"
}}"""

        result = await self._call_ollama(
            system_prompt=SYSTEM_PROMPTS["summary"],
            user_prompt=prompt,
        )

        return IncidentSummaryResponse(**result)

    # ─── Private: Unified AI Call (JSON mode) ──────────────────────────────────

    async def _call_ollama(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.3,
        images: list[dict] | None = None,
    ) -> dict:
        """Route to the configured AI provider for structured JSON output."""
        if AI_PROVIDER == "bedrock":
            return await self._call_bedrock_json(system_prompt, user_prompt, temperature, images=images)
        else:
            return await self._call_ollama_json(system_prompt, user_prompt, temperature)

    # ─── Private: Chat Call (plain text) ────────────────────────────────────────

    async def _call_ai_chat(self, system_prompt: str, user_prompt: str, images: list[dict] | None = None) -> str:
        """Route to the configured AI provider for plain text chat."""
        if AI_PROVIDER == "bedrock":
            return await self._call_bedrock_chat(system_prompt, user_prompt, images=images)
        else:
            return await self._call_ollama_chat(system_prompt, user_prompt)

    # ─── Ollama Implementation ──────────────────────────────────────────────────

    async def _call_ollama_json(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.3,
    ) -> dict:
        """Make a structured Ollama API call (JSON mode)."""
        try:
            async with httpx.AsyncClient(timeout=300.0) as client:
                response = await client.post(
                    f"{OLLAMA_BASE_URL}/api/generate",
                    json={
                        "model": OLLAMA_MODEL,
                        "system": system_prompt,
                        "prompt": user_prompt,
                        "stream": False,
                        "format": "json",
                        "options": {
                            "temperature": temperature,
                            "num_predict": 2000,
                        },
                    },
                )
                response.raise_for_status()
                data = response.json()
                content = data.get("response", "{}")

            result = json.loads(content)

            # Normalize keys: "root Cause" → "root_cause", "Resolution Steps" → "resolution_steps"
            result = self._normalize_keys(result)

            return result

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Ollama JSON response: {e}")
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="AI returned an invalid response. Please try again.",
            )
        except httpx.ConnectError:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Cannot connect to Ollama. Make sure it's running.",
            )
        except Exception as e:
            logger.error(f"Ollama API error: {e}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"AI service error: {str(e)}",
            )

    async def _get_incident_images(self, incident_id: UUID) -> list[dict] | None:
        """Fetch images attached to an incident from S3 and return as base64 for Claude vision."""
        import boto3
        import base64
        from sqlalchemy import select
        from app.models.attachment import Attachment

        try:
            result = await self.db.execute(
                select(Attachment).where(
                    Attachment.incident_id == incident_id,
                    Attachment.content_type.in_(["image/png", "image/jpeg", "image/gif", "image/webp"]),
                )
            )
            image_attachments = result.scalars().all()

            if not image_attachments:
                return None

            s3 = boto3.client(
                "s3",
                aws_access_key_id=getattr(settings, "AWS_ACCESS_KEY_ID", None),
                aws_secret_access_key=getattr(settings, "AWS_SECRET_ACCESS_KEY", None),
                region_name=getattr(settings, "AWS_REGION", "ap-south-1"),
            )

            images = []
            for att in image_attachments[:3]:  # Max 3 images to avoid token limit
                if att.file_size > 5 * 1024 * 1024:  # Skip images > 5MB
                    continue
                try:
                    obj = s3.get_object(
                        Bucket=getattr(settings, "S3_BUCKET_NAME", ""),
                        Key=att.file_key,
                    )
                    image_bytes = obj["Body"].read()
                    image_base64 = base64.b64encode(image_bytes).decode("utf-8")
                    images.append({
                        "media_type": att.content_type,
                        "data": image_base64,
                    })
                except Exception as e:
                    logger.warning(f"Failed to fetch image {att.file_name}: {e}")
                    continue

            return images if images else None

        except Exception as e:
            logger.warning(f"Failed to get incident images: {e}")
            return None

    async def _get_attachments_context(self, incident_id: UUID) -> str:
        """Fetch attachment info and content (text, PDF, DOCX) to include in AI context."""
        from sqlalchemy import select
        from app.models.attachment import Attachment
        import boto3

        try:
            result = await self.db.execute(
                select(Attachment).where(Attachment.incident_id == incident_id)
            )
            attachments = result.scalars().all()

            if not attachments:
                return "No attachments."

            s3 = boto3.client(
                "s3",
                aws_access_key_id=getattr(settings, "AWS_ACCESS_KEY_ID", None),
                aws_secret_access_key=getattr(settings, "AWS_SECRET_ACCESS_KEY", None),
                region_name=getattr(settings, "AWS_REGION", "ap-south-1"),
            )
            bucket = getattr(settings, "S3_BUCKET_NAME", "")

            context_parts = []
            for att in attachments:
                info = f"[File: {att.file_name} ({att.content_type}, {att.file_size} bytes)]"

                # Text-based files — read directly
                text_types = ["text/plain", "text/csv", "text/x-log", "application/json"]
                if att.content_type in text_types and att.file_size < 50000:
                    try:
                        obj = s3.get_object(Bucket=bucket, Key=att.file_key)
                        content = obj["Body"].read().decode("utf-8", errors="ignore")[:5000]
                        info += f"\nContent:\n```\n{content}\n```"
                    except Exception:
                        info += "\n(Could not read file content)"

                # PDF files — extract text
                elif att.content_type == "application/pdf" and att.file_size < 5000000:
                    try:
                        import io
                        from PyPDF2 import PdfReader
                        obj = s3.get_object(Bucket=bucket, Key=att.file_key)
                        pdf_bytes = obj["Body"].read()
                        reader = PdfReader(io.BytesIO(pdf_bytes))
                        pdf_text = ""
                        for page in reader.pages[:10]:  # Max 10 pages
                            pdf_text += page.extract_text() or ""
                        pdf_text = pdf_text[:5000]  # Limit to 5000 chars
                        if pdf_text.strip():
                            info += f"\nExtracted PDF Content:\n```\n{pdf_text}\n```"
                        else:
                            info += "\n(PDF contains no extractable text — may be scanned/image-based)"
                    except Exception as e:
                        info += f"\n(Could not extract PDF content: {str(e)[:50]})"

                # DOCX files — extract text
                elif att.content_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document" and att.file_size < 5000000:
                    try:
                        import io
                        from docx import Document
                        obj = s3.get_object(Bucket=bucket, Key=att.file_key)
                        docx_bytes = obj["Body"].read()
                        doc = Document(io.BytesIO(docx_bytes))
                        docx_text = "\n".join([p.text for p in doc.paragraphs if p.text.strip()])[:5000]
                        if docx_text.strip():
                            info += f"\nExtracted DOCX Content:\n```\n{docx_text}\n```"
                        else:
                            info += "\n(DOCX is empty or contains only images)"
                    except Exception as e:
                        info += f"\n(Could not extract DOCX content: {str(e)[:50]})"

                # Images — note they are attached (vision handled separately)
                elif att.content_type.startswith("image/"):
                    info += "\n(Image attached — will be analyzed visually if using Claude)"

                context_parts.append(info)

            return "\n".join(context_parts)

        except Exception as e:
            logger.warning(f"Failed to get attachments context: {e}")
            return "Could not load attachments."

    def _normalize_keys(self, data) -> dict:
        """Normalize JSON keys from AI response to match expected schema.
        Handles common model mistakes like 'root Cause' → 'root_cause'."""
        if not isinstance(data, dict):
            return data

        normalized = {}
        for key, value in data.items():
            # Convert to snake_case: "root Cause" → "root_cause", "Resolution Steps" → "resolution_steps"
            new_key = key.lower().replace(' ', '_').replace('-', '_')

            # Normalize nested values
            if isinstance(value, dict):
                value = self._normalize_keys(value)
            elif isinstance(value, list):
                value = [
                    self._normalize_keys(item) if isinstance(item, dict)
                    else str(item) if not isinstance(item, (str, int, float, bool))
                    else item
                    for item in value
                ]
                # Flatten list of dicts with single values (e.g., [{"step1": "..."}, {"step2": "..."}] → ["...", "..."])
                if value and all(isinstance(item, dict) and len(item) == 1 for item in value):
                    value = [list(item.values())[0] for item in value]

            normalized[new_key] = value

        # Add default values for commonly missing fields
        defaults = {
            'confidence': 0.8,
            'severity': 'medium',
            'resolution_steps': [],
            'preventive_measures': [],
            'affected_components': [],
            'estimated_effort': 'Unknown',
            'summary': normalized.get('summary', ''),
            'root_cause': normalized.get('root_cause', normalized.get('probable_cause', '')),
            'probable_cause': normalized.get('probable_cause', normalized.get('root_cause', '')),
        }

        for key, default in defaults.items():
            if key not in normalized:
                normalized[key] = default

        return normalized

    async def _call_ollama_chat(self, system_prompt: str, user_prompt: str) -> str:
        """Make a plain text Ollama API call (chat mode)."""
        try:
            async with httpx.AsyncClient(timeout=300.0) as client:
                response = await client.post(
                    f"{OLLAMA_BASE_URL}/api/generate",
                    json={
                        "model": OLLAMA_MODEL,
                        "system": system_prompt,
                        "prompt": user_prompt,
                        "stream": False,
                        "options": {
                            "temperature": 0.5,
                            "num_predict": 1500,
                        },
                    },
                )
                response.raise_for_status()
                data = response.json()
                return data.get("response", "I couldn't generate a response.")
        except Exception as e:
            logger.error(f"Ollama chat error: {e}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Ollama AI service unavailable.",
            )

    # ─── AWS Bedrock Implementation ─────────────────────────────────────────────

    async def _call_bedrock_json(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.3,
        images: list[dict] | None = None,
    ) -> dict:
        """Make a structured AWS Bedrock API call (JSON mode) with optional image support."""
        import boto3

        try:
            bedrock = boto3.client(
                "bedrock-runtime",
                region_name=BEDROCK_REGION,
                aws_access_key_id=getattr(settings, "AWS_ACCESS_KEY_ID", None),
                aws_secret_access_key=getattr(settings, "AWS_SECRET_ACCESS_KEY", None),
            )

            # Build content with optional images
            content = []
            if images:
                for img in images:
                    content.append({
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": img["media_type"],
                            "data": img["data"],
                        }
                    })
            content.append({"type": "text", "text": user_prompt})

            body = json.dumps({
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 2000,
                "temperature": temperature,
                "system": system_prompt + "\n\nYou MUST respond with valid JSON only. No other text.",
                "messages": [
                    {"role": "user", "content": content}
                ],
            })

            response = bedrock.invoke_model(
                modelId=BEDROCK_MODEL,
                body=body,
                contentType="application/json",
                accept="application/json",
            )

            response_body = json.loads(response["body"].read())
            content = response_body["content"][0]["text"]

            # Parse JSON from response
            return json.loads(content)

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Bedrock JSON response: {e}")
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="AI returned an invalid response. Please try again.",
            )
        except Exception as e:
            logger.error(f"Bedrock API error: {e}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"AWS Bedrock error: {str(e)}",
            )

    async def _call_bedrock_chat(self, system_prompt: str, user_prompt: str, images: list[dict] | None = None) -> str:
        """Make a plain text AWS Bedrock API call (chat mode) with optional image support."""
        import boto3

        try:
            bedrock = boto3.client(
                "bedrock-runtime",
                region_name=BEDROCK_REGION,
                aws_access_key_id=getattr(settings, "AWS_ACCESS_KEY_ID", None),
                aws_secret_access_key=getattr(settings, "AWS_SECRET_ACCESS_KEY", None),
            )

            # Build message content (text + optional images)
            content = []

            # Add images first if provided
            if images:
                for img in images:
                    content.append({
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": img["media_type"],
                            "data": img["data"],
                        }
                    })

            # Add text prompt
            content.append({"type": "text", "text": user_prompt})

            body = json.dumps({
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 2000,
                "temperature": 0.5,
                "system": system_prompt,
                "messages": [
                    {"role": "user", "content": content}
                ],
            })

            response = bedrock.invoke_model(
                modelId=BEDROCK_MODEL,
                body=body,
                contentType="application/json",
                accept="application/json",
            )

            response_body = json.loads(response["body"].read())
            return response_body["content"][0]["text"]

        except Exception as e:
            logger.error(f"Bedrock chat error: {e}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"AWS Bedrock error: {str(e)}",
            )
