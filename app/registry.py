"""
------------------------------------------------------------------------------
Project: Snowflake Data Product API
Developer: Rikesh Chhetri
Description: Registry management for mapping API slugs to Snowflake tables.
------------------------------------------------------------------------------
"""
import os
from typing import Dict
from pathlib import Path
from app.config import logger

# Registry of supported data views
# Key: URL friendly name (slug)
# Value: Actual Snowflake Table/View Name

def load_view_registry() -> Dict[str, str]:
    """
    Dynamically loads the view registry from snowflake_view_list.txt.
    Generates URL-friendly slugs (e.g., 'company-index') for each table.
    Also merges in manual friendly aliases.
    """
    # 1. Start with manual friendly aliases (Backward Compatibility)
    registry = {
        "companies": "COMPANY_INDEX",
        "fed-reserve": "FEDERAL_RESERVE_TIMESERIES",
        "fbi-crime": "FBI_CRIME_TIMESERIES",
        "climate": "CLIMATE_WATCH_TIMESERIES",
        "labor-stats": "BUREAU_OF_LABOR_STATISTICS_EMPLOYMENT_TIMESERIES"
    }
    
    # Define path relative to this file (app/registry.py -> ../snowflake_view_list.txt)
    base_dir = Path(__file__).resolve().parent.parent
    view_list_path = base_dir / "snowflake_view_list.txt"
    
    try:
        if view_list_path.exists():
            logger.info(f"Loading views from {view_list_path}")
            with open(view_list_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
                
            count = 0
            for line in lines:
                table_name = line.strip()
                
                # Skip empty lines or header
                if not table_name or table_name.lower() == "name":
                    continue
                    
                # Generate slug: AIRCRAFT_CARRIER_INDEX -> aircraft-carrier-index
                slug = table_name.lower().replace("_", "-")
                
                # Add to registry (won't overwrite manual aliases if we did dict.update, 
                # but here we just set keys. If we want manual to win, we should be careful.
                # Actually, having both 'company-index' and 'companies' pointing to the same table is fine.)
                registry[slug] = table_name
                count += 1
                
            logger.info(f"Successfully loaded {count} views from file. Total registry size: {len(registry)}")
        else:
            logger.warning(f"View list not found at {view_list_path}. Using only manual aliases.")
            
    except Exception as e:
        logger.error(f"Failed to load view registry: {e}")
        # Fallback is just the initial manual registry
        
    return registry

# Initialize the registry
VIEW_ALLOWLIST = load_view_registry()
