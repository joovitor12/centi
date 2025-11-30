from app.agent.prompts import get_langfuse_client

langfuse = get_langfuse_client()

prompt = langfuse.get_prompt(
    "email_meeting_coordination/extract_meeting_context/user", label="production"
)


