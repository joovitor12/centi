"""Agent guidelines configuration."""

from datetime import datetime
import parlant.sdk as p

# Import all prompts from Langfuse
from .prompts.add_appointment.condition import prompt as add_appointment_condition
from .prompts.add_appointment.action import prompt as add_appointment_action
from .prompts.find_appointments.condition import prompt as find_appointments_condition
from .prompts.find_appointments.action import prompt as find_appointments_action
from .prompts.edit_appointment.condition import prompt as edit_appointment_condition
from .prompts.edit_appointment.action import prompt as edit_appointment_action
from .prompts.delete_appointment.condition import prompt as delete_appointment_condition
from .prompts.delete_appointment.action import prompt as delete_appointment_action

# Recurring appointments prompts
from .prompts.create_recurring_appointment.condition import (
    prompt as create_recurring_appointment_condition,
)
from .prompts.create_recurring_appointment.action import (
    prompt as create_recurring_appointment_action,
)
from .prompts.list_recurring_appointments.condition import (
    prompt as list_recurring_appointments_condition,
)
from .prompts.list_recurring_appointments.action import (
    prompt as list_recurring_appointments_action,
)
from .prompts.get_recurring_appointment.condition import (
    prompt as get_recurring_appointment_condition,
)
from .prompts.get_recurring_appointment.action import (
    prompt as get_recurring_appointment_action,
)
from .prompts.edit_recurring_appointment.condition import (
    prompt as edit_recurring_appointment_condition,
)
from .prompts.edit_recurring_appointment.action import (
    prompt as edit_recurring_appointment_action,
)
from .prompts.pause_recurring_appointment.condition import (
    prompt as pause_recurring_appointment_condition,
)
from .prompts.pause_recurring_appointment.action import (
    prompt as pause_recurring_appointment_action,
)
from .prompts.resume_recurring_appointment.condition import (
    prompt as resume_recurring_appointment_condition,
)
from .prompts.resume_recurring_appointment.action import (
    prompt as resume_recurring_appointment_action,
)
from .prompts.delete_recurring_appointment.condition import (
    prompt as delete_recurring_appointment_condition,
)
from .prompts.delete_recurring_appointment.action import (
    prompt as delete_recurring_appointment_action,
)


async def setup_guidelines(
    agent: p.Agent, tools: list, recurring_tools: list = None, newsletter_tools: list = None
) -> None:
    """Setup agent guidelines.

    Args:
        agent: Parlant agent instance
        tools: List of tool functions to use in guidelines
            Expected order: [find_appointments, add_appointment, delete_appointment, edit_appointment]
        recurring_tools: List of recurring appointment tools (optional)
            Expected order: [create_recurring_appointment, list_recurring_appointments, ...]
        newsletter_tools: List of newsletter tools (optional)
            Expected order: [list_newsletters, create_newsletter, update_newsletter, ...]
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

    # Guideline: Multilingual behavior (PT-BR / EN)
    await agent.create_guideline(
        condition=(
            "User communicates in Portuguese or English, or switches language during conversation."
        ),
        action=(
            "Always reply in the language used by the user's latest message. "
            "If user writes in Portuguese, reply in Portuguese (pt-BR). "
            "If user writes in English, reply in English. "
            "If language is mixed or unclear, ask one short language preference question."
        ),
    )

    # Guideline: Adding appointments (NON-RECURRING only)
    await agent.create_guideline(
        condition=(
            "User asks what the assistant can do, asks for available features/tools, "
            "or asks for a precise capabilities list."
        ),
        action=(
            "Answer only with currently supported Centi features and use the user's language. Mention: "
            "create/list/edit/delete one-time appointments, create/list/edit/pause/"
            "resume/delete recurring appointments, and newsletter builder "
            "(create/list/update/delete newsletter configs, up to 5 themes with defaults "
            "videogames/tecnologia/esportes, generate newsletter content, send now, "
            "and scheduled delivery daily/weekly/every N days). "
            "Do not claim unrelated generic abilities."
        ),
    )

    # Guideline: Adding appointments (NON-RECURRING only)
    if add_appointment:
        current_datetime = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
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
            condition=find_appointments_condition.compile(),
            action=find_appointments_action.compile(),
            tools=[find_appointments],
        )

    # Guideline: Editing appointments
    if edit_appointment and find_appointments:
        await agent.create_guideline(
            condition=edit_appointment_condition.compile(),
            action=edit_appointment_action.compile(),
            tools=[find_appointments, edit_appointment],
        )

    # Guideline: Deleting appointments
    if delete_appointment and find_appointments:
        await agent.create_guideline(
            condition=delete_appointment_condition.compile(),
            action=delete_appointment_action.compile(),
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
        current_datetime = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        compiled_action = create_recurring_appointment_action.compile(
            datetime_today=current_datetime
        )
        await agent.create_guideline(
            condition=create_recurring_appointment_condition.compile(),
            action=compiled_action,
            tools=[create_recurring_appointment],
        )

    # Guideline: Listing recurring appointments
    if list_recurring_appointments:
        await agent.create_guideline(
            condition=list_recurring_appointments_condition.compile(),
            action=list_recurring_appointments_action.compile(),
            tools=[list_recurring_appointments],
        )

    # Guideline: Getting specific recurring appointment details
    if get_recurring_appointment and list_recurring_appointments:
        await agent.create_guideline(
            condition=get_recurring_appointment_condition.compile(),
            action=get_recurring_appointment_action.compile(),
            tools=[list_recurring_appointments, get_recurring_appointment],
        )

    # Guideline: Editing recurring appointments
    if edit_recurring_appointment and list_recurring_appointments:
        await agent.create_guideline(
            condition=edit_recurring_appointment_condition.compile(),
            action=edit_recurring_appointment_action.compile(),
            tools=[list_recurring_appointments, edit_recurring_appointment],
        )

    # Guideline: Pausing recurring appointments
    if pause_recurring_appointment and list_recurring_appointments:
        await agent.create_guideline(
            condition=pause_recurring_appointment_condition.compile(),
            action=pause_recurring_appointment_action.compile(),
            tools=[list_recurring_appointments, pause_recurring_appointment],
        )

    # Guideline: Resuming recurring appointments
    if resume_recurring_appointment and list_recurring_appointments:
        await agent.create_guideline(
            condition=resume_recurring_appointment_condition.compile(),
            action=resume_recurring_appointment_action.compile(),
            tools=[list_recurring_appointments, resume_recurring_appointment],
        )

    # Guideline: Deleting recurring appointments
    if delete_recurring_appointment and list_recurring_appointments:
        await agent.create_guideline(
            condition=delete_recurring_appointment_condition.compile(),
            action=delete_recurring_appointment_action.compile(),
            tools=[list_recurring_appointments, delete_recurring_appointment],
        )

    # ============================================================
    # Newsletter Builder Guidelines
    # ============================================================
    if newsletter_tools and len(newsletter_tools) >= 6:
        list_newsletters = newsletter_tools[0]
        create_newsletter = newsletter_tools[1]
        update_newsletter = newsletter_tools[2]
        delete_newsletter = newsletter_tools[3]
        generate_newsletter_content = newsletter_tools[4]
        send_newsletter_now = newsletter_tools[5]

        await agent.create_guideline(
            condition=(
                "User asks to create/configure a newsletter with title, themes, or frequency."
            ),
            action=(
                "Use authenticated session context for user_id/email whenever available. "
                "Only ask the user for user_id/email if tool feedback says they were not found in context. "
                "Enforce max 5 themes, suggest defaults (videogames, tecnologia, esportes), "
                "then call create_newsletter."
            ),
            tools=[create_newsletter],
        )

        await agent.create_guideline(
            condition=(
                "User asks to see, list, manage, or review their newsletter configurations."
            ),
            action=(
                "Call list_newsletters first to show available newsletter IDs and current settings."
            ),
            tools=[list_newsletters],
        )

        await agent.create_guideline(
            condition=(
                "User asks to edit newsletter title/themes/email/frequency or pause/resume delivery."
            ),
            action=(
                "Call update_newsletter with the newsletter ID and only requested fields."
            ),
            tools=[update_newsletter],
        )

        await agent.create_guideline(
            condition="User asks to delete a newsletter.",
            action="Call delete_newsletter using the newsletter ID.",
            tools=[delete_newsletter],
        )

        await agent.create_guideline(
            condition=(
                "User asks to generate the newsletter content or preview the next edition."
            ),
            action=(
                "Call generate_newsletter_content using newsletter_id and user_id."
            ),
            tools=[generate_newsletter_content],
        )

        await agent.create_guideline(
            condition=(
                "User asks to send newsletter now or test immediate delivery by email."
            ),
            action=(
                "Call send_newsletter_now using newsletter_id and user_id."
            ),
            tools=[send_newsletter_now],
        )
