from app.agent.prompts import get_langfuse_client

langfuse = get_langfuse_client()

prompt = langfuse.get_prompt("appointments/add_appointment/action", label="production")
