import pytest
from app.registry import VIEW_ALLOWLIST

def test_manual_aliases_exist():
    """Test that hardcoded friendly aliases are preserved."""
    assert "companies" in VIEW_ALLOWLIST
    assert VIEW_ALLOWLIST["companies"] == "COMPANY_INDEX"
    
    assert "fbi-crime" in VIEW_ALLOWLIST
    assert VIEW_ALLOWLIST["fbi-crime"] == "FBI_CRIME_TIMESERIES"

def test_dynamic_loading_works():
    """Test that views from snowflake_view_list.txt are loaded."""
    # Check for a view that is definitely in the text file but not in manual aliases
    # 'AIRCRAFT_CARRIER_INDEX' -> 'aircraft-carrier-index'
    
    slug = "aircraft-carrier-index"
    assert slug in VIEW_ALLOWLIST
    assert VIEW_ALLOWLIST[slug] == "AIRCRAFT_CARRIER_INDEX"
    
def test_normalization():
    """Test that slugs are correctly normalized (lowercase, kebab-case)."""
    # 'AMERICAN_COMMUNITY_SURVEY_ATTRIBUTES' -> 'american-community-survey-attributes'
    slug = "american-community-survey-attributes"
    assert slug in VIEW_ALLOWLIST
    assert VIEW_ALLOWLIST[slug] == "AMERICAN_COMMUNITY_SURVEY_ATTRIBUTES"
