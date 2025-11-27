from app.agent.prompts import get_langfuse_client

langfuse = get_langfuse_client()

prompt = langfuse.get_prompt(
    "appointments/find_appointments/condition", label="production"
)
