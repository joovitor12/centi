from app.agent.prompts import get_langfuse_client

langfuse = get_langfuse_client()

prompt = langfuse.get_prompt(
    "email_meeting_coordination/process_meeting_response/system", label="production"
)


