"""
Constants for the family expense report application.
"""

# Source identifiers used throughout the application
class SourceIds:
    """Source identifiers for different financial data sources."""
    CHASE_CHECKING = "chase_checking"
    CHASE_CREDIT_CARD = "chase_credit_card"
    APPLE_CARD_JOE = "apple_card_joe"
    APPLE_CARD_NIKITA = "apple_card_nikita"

    @classmethod
    def apple_card_for_owner(cls, owner: str) -> str:
        """Generate Apple Card source ID for a given owner."""
        return f"apple_card_{owner.lower()}"

# Account owners
class AccountOwners:
    """Account owner identifiers."""
    SHARED = "shared"
    JOE = "joe"
    NIKITA = "nikita"

# Folder names for data sources
class SourceFolders:
    """Folder names for different data sources."""
    CHASE_CHECKING = "chase_checking"
    CHASE_CREDIT_CARD = "chase_card"
    JOE_APPLE_CARD = "joe_apple_card"
    NIKITA_APPLE_CARD = "nikita_apple_card"
