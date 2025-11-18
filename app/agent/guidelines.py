"""Agent guidelines configuration."""

from datetime import datetime
import parlant.sdk as p


async def setup_guidelines(agent: p.Agent, tools: list) -> None:
    """Setup agent guidelines.

    Args:
        agent: Parlant agent instance
        tools: List of tool functions to use in guidelines
        Expected order: [find_appointments, add_appointment, delete_appointment, edit_appointment]
    """
    # Tools are returned in order from create_appointment_tools:
    # [find_appointments, add_appointment, delete_appointment, edit_appointment]
    if len(tools) >= 4:
        find_appointments = tools[0]
        add_appointment = tools[1]
        delete_appointment = tools[2]
        edit_appointment = tools[3]
    else:
        # Fallback: try to find by name if order is different
        find_appointments = tools[0] if len(tools) > 0 else None
        add_appointment = tools[1] if len(tools) > 1 else None
        delete_appointment = tools[2] if len(tools) > 2 else None
        edit_appointment = tools[3] if len(tools) > 3 else None

    # Guideline: Adding appointments
    if add_appointment:
        await agent.create_guideline(
            condition="User wants to schedule, add, or create an appointment, meeting, reminder, or task",
            action=f"""You must calculate the exact datetime and provide it in the correct format.

EXAMPLES:
- If user says "in 5 hours" and current time is 09:24, calculate: 09:24 + 5 hours = 14:24, then format as "2025-11-14 14:24:00"
- If user says "tomorrow at 4:30pm", format as "2025-11-15 16:30:00" 
- If user says "today at 2pm", format as "2025-11-14 14:00:00"

CRITICAL: 
- NEVER use placeholder text like "calculated_datetime_based_on_current_time_plus_5_hours"
- ALWAYS provide an actual datetime string like "2025-11-14 14:24:00"
- Format must be exactly "YYYY-MM-DD HH:MM:SS"

Use add_appointment tool with description and the calculated when parameter. Today datetime is {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}.""",
            tools=[add_appointment],
        )

    # Guideline: Finding appointments
    if find_appointments:
        await agent.create_guideline(
            condition="User asks about their schedule, appointments, calendar, or what they have planned",
            action="Search and display their appointments using find_appointments",
            tools=[find_appointments],
        )

    # Guideline: Editing appointments
    if edit_appointment and find_appointments:
        await agent.create_guideline(
            condition="User wants to change or update an existing appointment, meeting, reminder, or task, need to return all existing appointments first for the user to decide which to edit",
            action="""When user wants to edit an appointment:
1. First use find_appointments to list all appointments
2. When the user specifies which appointment to edit (by ID number, description, or time), you MUST call the edit_appointment tool
3. CRITICALLY IMPORTANT: Use the 'id' field from the appointment data returned by find_appointments, NOT the position/index in the list
4. For example, if find_appointments returns appointments with ids [4, 5, 6, 7, 8] and the user says "ID 8" or "appointment 8", use appointment_id=8 (the database ID)
5. Extract the new description and/or new time from the user's request
6. Call edit_appointment with: appointment_id (the database ID), new_description (if changed), and new_when (if changed, in format "YYYY-MM-DD HH:MM:SS")
7. DO NOT just say you updated it - you MUST actually call the edit_appointment tool function""",
            tools=[find_appointments, edit_appointment],
        )

    # Guideline: Deleting appointments
    if delete_appointment and find_appointments:
        await agent.create_guideline(
            condition="User wants to delete an appointment, meeting, reminder, or task",
            action="""When user wants to delete an appointment:
1. First use find_appointments to list all appointments
2. When the user specifies which appointment to delete (by ID number, description, or time), you MUST call the delete_appointment tool
3. CRITICALLY IMPORTANT: Use the 'id' field from the appointment data returned by find_appointments, NOT the position/index in the list
4. For example, if find_appointments returns appointments with ids [4, 5, 6, 7, 8] and the user says "ID 8" or "appointment 8", use appointment_id=8 (the database ID)
5. Call delete_appointment with: appointment_id (the database ID)""",
            tools=[find_appointments, delete_appointment],
        )
