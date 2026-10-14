"""Reserved for the future MCP integration.

The core analysis services in services/analysis_service.py are intentionally
independent of MCP so they can be exposed later through an MCP server without
changing the analysis engine.
"""

from services.analysis_service import AnalysisService


def get_analysis_service():
    return AnalysisService
