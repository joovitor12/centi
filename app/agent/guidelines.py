"""Agent guidelines configuration."""

from datetime import datetime
from .prompts.add_appointment.condition import prompt as add_appointment_condition
from .prompts.add_appointment.action import prompt as add_appointment_action
import parlant.sdk as p


async def setup_guidelines(
    agent: p.Agent, tools: list, recurring_tools: list = None
) -> None:
    """Setup agent guidelines.

    Args:
        agent: Parlant agent instance
        tools: List of tool functions to use in guidelines
            Expected order: [find_appointments, add_appointment, delete_appointment, edit_appointment]
        recurring_tools: List of recurring appointment tools (optional)
            Expected order: [create_recurring_appointment, list_recurring_appointments, ...]
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

    # Guideline: Adding appointments (NON-RECURRING only)
    if add_appointment:
        current_datetime = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        # Compile the action prompt with the current datetime variable
        # The Langfuse prompt will automatically substitute {{datetime_today}}
        compiled_action = add_appointment_action.compile(
            datetime_today=current_datetime
        )
        await agent.create_guideline(
            condition=add_appointment_condition.compile(),
            action=compiled_action,
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

    # ============================================================
    # Recurring Appointments Guidelines
    # ============================================================

    if recurring_tools and len(recurring_tools) >= 7:
        create_recurring_appointment = recurring_tools[0]
        list_recurring_appointments = recurring_tools[1]
        get_recurring_appointment = recurring_tools[2]
        edit_recurring_appointment = recurring_tools[3]
        pause_recurring_appointment = recurring_tools[4]
        resume_recurring_appointment = recurring_tools[5]
        delete_recurring_appointment = recurring_tools[6]
    else:
        create_recurring_appointment = (
            recurring_tools[0] if recurring_tools and len(recurring_tools) > 0 else None
        )
        list_recurring_appointments = (
            recurring_tools[1] if recurring_tools and len(recurring_tools) > 1 else None
        )
        get_recurring_appointment = (
            recurring_tools[2] if recurring_tools and len(recurring_tools) > 2 else None
        )
        edit_recurring_appointment = (
            recurring_tools[3] if recurring_tools and len(recurring_tools) > 3 else None
        )
        pause_recurring_appointment = (
            recurring_tools[4] if recurring_tools and len(recurring_tools) > 4 else None
        )
        resume_recurring_appointment = (
            recurring_tools[5] if recurring_tools and len(recurring_tools) > 5 else None
        )
        delete_recurring_appointment = (
            recurring_tools[6] if recurring_tools and len(recurring_tools) > 6 else None
        )

    # Guideline: Creating recurring appointments
    if create_recurring_appointment:
        await agent.create_guideline(
            condition="User wants to schedule, add, or create a recurring, repeating, daily, weekly, monthly, or repeating appointment, meeting, reminder, or task",
            action=f"""You must detect recurring patterns and create recurring appointments.

EXAMPLES OF RECURRENCE DETECTION:
- "every day" / "daily" → recurrence_pattern="daily", recurrence_interval=1
- "every week" / "weekly" / "every Monday" / "Mondays" → recurrence_pattern="weekly", recurrence_interval=1
- "every 2 weeks" → recurrence_pattern="weekly", recurrence_interval=2
- "every Monday and Wednesday" / "Mondays and Wednesdays" → recurrence_pattern="weekly", recurrence_byday="MO,WE"
- "every Monday, Wednesday, Friday" → recurrence_pattern="weekly", recurrence_byday="MO,WE,FR"
- "every month" / "monthly" → recurrence_pattern="monthly", recurrence_interval=1
- "every 15th of the month" / "on the 15th of each month" → recurrence_pattern="monthly", recurrence_bymonthday=15

TIME FORMAT:
- Calculate the exact datetime for the first occurrence
- Format must be exactly "YYYY-MM-DD HH:MM:SS"
- Today datetime is {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

BYDAY FORMAT (for weekly):
- Single day: "MO" (Monday), "TU" (Tuesday), "WE" (Wednesday), "TH" (Thursday), "FR" (Friday), "SA" (Saturday), "SU" (Sunday)
- Multiple days: "MO,WE,FR" (comma-separated, no spaces)

CRITICAL:
- If user mentions "every", "daily", "weekly", "monthly", "repeat", "recurring" → use create_recurring_appointment
- DO NOT use add_appointment when creating a recurring appointment - ONLY use create_recurring_appointment
- The recurring appointment will automatically create all future occurrences - you don't need to create individual appointments
- Extract the description, start time, and recurrence pattern
- Call create_recurring_appointment with ALL required parameters
- NEVER use placeholder text - ALWAYS provide actual calculated values""",
            tools=[create_recurring_appointment],
        )

    # Guideline: Listing recurring appointments
    if list_recurring_appointments:
        await agent.create_guideline(
            condition="User asks about their recurring appointments, repeating reminders, or repeating tasks",
            action="Use list_recurring_appointments to show all recurring appointments. Set active_only=True to show only active ones.",
            tools=[list_recurring_appointments],
        )

    # Guideline: Getting specific recurring appointment details
    if get_recurring_appointment and list_recurring_appointments:
        await agent.create_guideline(
            condition="User asks for details or information about a specific recurring appointment by ID",
            action="""When user wants to see details of a specific recurring appointment:
1. If the user provides an ID, use get_recurring_appointment with that recurring_appointment_id
2. If the user hasn't listed appointments yet, first use list_recurring_appointments to show options
3. Then use get_recurring_appointment with the ID the user specifies""",
            tools=[list_recurring_appointments, get_recurring_appointment],
        )

    # Guideline: Editing recurring appointments
    if edit_recurring_appointment and list_recurring_appointments:
        await agent.create_guideline(
            condition="User wants to change or update an existing recurring appointment",
            action="""When user wants to edit a recurring appointment:
1. First use list_recurring_appointments to show all recurring appointments
2. When user specifies which recurring appointment to edit (by ID), use edit_recurring_appointment
3. Extract the fields to update (description, time, pattern, etc.)
4. Call edit_recurring_appointment with recurring_appointment_id and the fields to update""",
            tools=[list_recurring_appointments, edit_recurring_appointment],
        )

    # Guideline: Pausing recurring appointments
    if pause_recurring_appointment and list_recurring_appointments:
        await agent.create_guideline(
            condition="User wants to pause, stop, or disable a recurring appointment",
            action="""When user wants to pause a recurring appointment:
1. Use list_recurring_appointments to show recurring appointments
2. When user specifies which one to pause (by ID), use pause_recurring_appointment
3. Call pause_recurring_appointment with the recurring_appointment_id""",
            tools=[list_recurring_appointments, pause_recurring_appointment],
        )

    # Guideline: Resuming recurring appointments
    if resume_recurring_appointment and list_recurring_appointments:
        await agent.create_guideline(
            condition="User wants to resume, reactivate, or re-enable a paused recurring appointment",
            action="""When user wants to resume a recurring appointment:
1. Use list_recurring_appointments to show recurring appointments (including inactive ones)
2. When user specifies which one to resume (by ID), use resume_recurring_appointment
3. Call resume_recurring_appointment with the recurring_appointment_id""",
            tools=[list_recurring_appointments, resume_recurring_appointment],
        )

    # Guideline: Deleting recurring appointments
    if delete_recurring_appointment and list_recurring_appointments:
        await agent.create_guideline(
            condition="User wants to delete, remove, or cancel a recurring appointment completely",
            action="""When user wants to delete a recurring appointment:
1. Use list_recurring_appointments to show recurring appointments
2. When user specifies which one to delete (by ID), use delete_recurring_appointment
3. Call delete_recurring_appointment with the recurring_appointment_id""",
            tools=[list_recurring_appointments, delete_recurring_appointment],
        )
