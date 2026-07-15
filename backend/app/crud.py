from sqlalchemy.orm import Session

from app.models import HCPInteraction


def create_interaction(db, data):

    interaction = HCPInteraction(**data.dict())

    db.add(interaction)

    db.commit()

    db.refresh(interaction)

    return interaction


def update_interaction(db, id, data):

    interaction = db.query(HCPInteraction).filter(HCPInteraction.id == id).first()

    if not interaction:

        return None

    for key, value in data.dict().items():

        setattr(interaction, key, value)

    db.commit()

    db.refresh(interaction)

    return interaction


def update_interaction_fields(db, id, fields: dict):
    """
    Update only the specific fields provided (partial update), leaving
    everything else untouched. Used for natural-language corrections like
    "the doctor's name is actually Dr. Smith" where only one or two fields
    need to change.
    """

    interaction = db.query(HCPInteraction).filter(HCPInteraction.id == id).first()

    if not interaction:

        return None

    for key, value in fields.items():

        if value is not None and value != "":

            setattr(interaction, key, value)

    db.commit()

    db.refresh(interaction)

    return interaction