from app.ai.tools import log_interaction

print(
    log_interaction.invoke(
        {
            "interaction": "Visited Dr. Sharma today."
        }
    )
)