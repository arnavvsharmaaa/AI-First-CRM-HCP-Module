import uuid
import os
from langchain_core.tools import tool
from sqlalchemy import select
from models.database import async_session
from models.hcp import HCP


@tool
async def search_hcp(hcp_name: str) -> dict:
    """
    Searches for an HCP (Healthcare Professional) by name in the database.
    Call this when the user mentions a doctor's name, asks to find an HCP,
    or when you need to look up a healthcare professional before logging an interaction.
    If the HCP is not found, a new profile is created automatically.
    Returns a form_update that populates the hcpName field.
    """
    search_term = hcp_name.strip()

    async with async_session() as session:
        # Search for existing HCP using ILIKE (case-insensitive partial match)
        result = await session.execute(
            select(HCP)
            .where(HCP.name.ilike(f"%{search_term}%"))
            .limit(5)
        )
        hcps = result.scalars().all()

        if hcps:
            # Use the first (closest) match
            found = hcps[0]
            extra_info = ""
            if found.specialty:
                extra_info += f" — {found.specialty}"
            if found.hospital:
                extra_info += f" at {found.hospital}"

            return {
                "type": "form_update",
                "fields": {"hcpName": found.name},
                "ai_message": (
                    f"Found {found.name}{extra_info} in the database. "
                    "Setting as the HCP for this interaction."
                ),
            }
        else:
            # HCP not found — create a new record
            new_hcp = HCP(
                id=uuid.uuid4(),
                name=search_term,
            )
            session.add(new_hcp)
            await session.commit()

            return {
                "type": "form_update",
                "fields": {"hcpName": search_term},
                "ai_message": (
                    f"I couldn't find \"{search_term}\" in the database, "
                    "so I've created a new HCP profile for them."
                ),
            }
