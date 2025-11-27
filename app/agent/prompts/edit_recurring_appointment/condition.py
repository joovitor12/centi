from app.agent.prompts import get_langfuse_client

langfuse = get_langfuse_client()

prompt = langfuse.get_prompt("recurring_appointments/edit_recurring_appointment/condition", label="production")

