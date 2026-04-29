from langchain_core.tools import tool
from sqlalchemy import select, or_
from models.database import async_session
from models.interaction import Interaction


@tool
async def get_interaction(query: str) -> dict:
    """
    Retrieves a previously logged HCP interaction from the database.
    Call this when the user asks to load, show, recall, or review a past interaction.
    The query can be an HCP name (e.g. "Dr. Patel"), a date (e.g. "2025-04-19"),
    a partial date like "yesterday", or a UUID interaction ID.
    Returns a form_update containing ALL fields of the matched interaction.
    """
    search_term = query.strip()

    # Detect if the query looks like a UUID
    is_uuid = (
        len(search_term) == 36
        and search_term.count("-") == 4
        and all(c in "0123456789abcdefABCDEF-" for c in search_term)
    )

    async with async_session() as session:
        if is_uuid:
            # Try exact UUID match first, then fall back to name/date search
            stmt = (
                select(Interaction)
                .where(
                    or_(
                        Interaction.id == search_term,
                        Interaction.hcpName.ilike(f"%{search_term}%"),
                        Interaction.date.ilike(f"%{search_term}%"),
                    )
                )
                .order_by(Interaction.date.desc())
                .limit(1)
            )
        else:
            # Search by HCP name or date (both are stored as strings)
            stmt = (
                select(Interaction)
                .where(
                    or_(
                        Interaction.hcpName.ilike(f"%{search_term}%"),
                        Interaction.date.ilike(f"%{search_term}%"),
                    )
                )
                .order_by(Interaction.date.desc())
                .limit(1)
            )

        result = await session.execute(stmt)
        interaction = result.scalars().first()

    if interaction is None:
        return {
            "type": "form_update",
            "fields": {},
            "ai_message": (
                f"I couldn't find any interaction matching \"{search_term}\". "
                "Try searching by doctor name or date (YYYY-MM-DD)."
            ),
        }

    # Map ALL Interaction model columns → Redux form shape
    fields = {
        "id": str(interaction.id),
        "hcpName": interaction.hcpName or "",
        "interactionType": interaction.interactionType or "Meeting",
        "date": interaction.date or "",
        "time": interaction.time or "",
        "attendees": interaction.attendees or [],
        "topicsDiscussed": interaction.topicsDiscussed or "",
        "materialsShared": interaction.materialsShared or [],
        "samplesDistributed": interaction.samplesDistributed or [],
        "sentiment": interaction.sentiment or "neutral",
        "outcomes": interaction.outcomes or "",
        "followUpActions": interaction.followUpActions or "",
        "aiSuggestedFollowups": interaction.aiSuggestedFollowups or [],
    }

    return {
        "type": "form_update",
        "fields": fields,
        "interaction_id": str(interaction.id),
        "ai_message": (
            f"Loaded your interaction with {interaction.hcpName} from {interaction.date}. "
            "All fields have been populated in the form."
        ),
    }
