"""gokaidm.persistence – JSON-backed data stores."""

from gokaidm.persistence.campaign import Campaign, CampaignStore
from gokaidm.persistence.ruleset import Ruleset, RulesetStore
from gokaidm.persistence.persona import Persona, PersonaStore
from gokaidm.persistence.location import Location, LocationStore

__all__ = [
    "Campaign",
    "CampaignStore",
    "Ruleset",
    "RulesetStore",
    "Persona",
    "PersonaStore",
    "Location",
    "LocationStore",
]
