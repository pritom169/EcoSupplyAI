"""
EcoSupplyAI MCP Server — exposes supply chain tools via Model Context Protocol.

To use with Claude Desktop, add to your claude_desktop_config.json:
{
    "mcpServers": {
        "ecosupplyai": {
            "command": "python",
            "args": ["-m", "src.mcp_server.server"],
            "cwd": "/path/to/EcoSupplyAI"
        }
    }
}
"""

from __future__ import annotations

import json
from pathlib import Path

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "sample"

server = Server("ecosupplyai")


def _load_suppliers() -> list[dict]:
    path = DATA_DIR / "suppliers.json"
    if path.exists():
        return json.loads(path.read_text()).get("suppliers", [])
    return []


def _load_regulations() -> list[dict]:
    path = DATA_DIR / "regulations.json"
    if path.exists():
        return json.loads(path.read_text()).get("regulations", [])
    return []


@server.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="search_suppliers",
            description="Search the supplier database by name, country, or industry",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search term"},
                    "country": {"type": "string", "description": "Filter by country"},
                    "industry": {"type": "string", "description": "Filter by industry"},
                },
                "required": ["query"],
            },
        ),
        Tool(
            name="get_supplier_details",
            description="Get full details for a specific supplier by ID",
            inputSchema={
                "type": "object",
                "properties": {"supplier_id": {"type": "string"}},
                "required": ["supplier_id"],
            },
        ),
        Tool(
            name="calculate_esg_score",
            description="Calculate composite ESG score with breakdown for a supplier",
            inputSchema={
                "type": "object",
                "properties": {"supplier_id": {"type": "string"}},
                "required": ["supplier_id"],
            },
        ),
        Tool(
            name="search_regulations",
            description="Search EU sustainability regulations by keyword",
            inputSchema={
                "type": "object",
                "properties": {"query": {"type": "string"}},
                "required": ["query"],
            },
        ),
        Tool(
            name="get_risk_assessment",
            description="Get risk assessment (low/medium/high/critical) for a supplier",
            inputSchema={
                "type": "object",
                "properties": {"supplier_id": {"type": "string"}},
                "required": ["supplier_id"],
            },
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    if name == "search_suppliers":
        return _handle_search_suppliers(arguments)
    elif name == "get_supplier_details":
        return _handle_get_supplier(arguments)
    elif name == "calculate_esg_score":
        return _handle_esg_score(arguments)
    elif name == "search_regulations":
        return _handle_search_regulations(arguments)
    elif name == "get_risk_assessment":
        return _handle_risk_assessment(arguments)
    else:
        return [TextContent(type="text", text=f"Unknown tool: {name}")]


def _handle_search_suppliers(args: dict) -> list[TextContent]:
    query = args.get("query", "").lower()
    country = args.get("country", "").lower()
    industry = args.get("industry", "").lower()
    suppliers = _load_suppliers()
    results = [
        s for s in suppliers
        if query in s["name"].lower()
        or query in s["country"].lower()
        or query in s["industry"].lower()
        and (not country or country in s["country"].lower())
        and (not industry or industry in s["industry"].lower())
    ]
    return [TextContent(type="text", text=json.dumps(results, indent=2))]


def _handle_get_supplier(args: dict) -> list[TextContent]:
    supplier_id = args.get("supplier_id", "")
    suppliers = _load_suppliers()
    for s in suppliers:
        if s["id"] == supplier_id:
            return [TextContent(type="text", text=json.dumps(s, indent=2))]
    return [TextContent(type="text", text=f"Supplier {supplier_id} not found")]


def _handle_esg_score(args: dict) -> list[TextContent]:
    supplier_id = args.get("supplier_id", "")
    suppliers = _load_suppliers()
    for s in suppliers:
        if s["id"] == supplier_id:
            env = s["environmental_score"]
            soc = s["labor_score"]
            gov = s["governance_score"]
            composite = round(env * 0.4 + soc * 0.3 + gov * 0.3, 1)
            result = {
                "supplier_id": supplier_id,
                "supplier_name": s["name"],
                "environmental_score": env,
                "social_score": soc,
                "governance_score": gov,
                "composite_esg_score": composite,
                "renewable_energy_pct": s["renewable_energy_pct"],
                "waste_recycling_pct": s["waste_recycling_pct"],
            }
            return [TextContent(type="text", text=json.dumps(result, indent=2))]
    return [TextContent(type="text", text=f"Supplier {supplier_id} not found")]


def _handle_search_regulations(args: dict) -> list[TextContent]:
    query = args.get("query", "").lower()
    regulations = _load_regulations()
    results = [
        r for r in regulations
        if query in r["name"].lower()
        or query in r["acronym"].lower()
        or query in r["description"].lower()
    ]
    return [TextContent(type="text", text=json.dumps(results, indent=2))]


def _handle_risk_assessment(args: dict) -> list[TextContent]:
    supplier_id = args.get("supplier_id", "")
    suppliers = _load_suppliers()
    for s in suppliers:
        if s["id"] == supplier_id:
            composite = s["environmental_score"] * 0.4 + s["labor_score"] * 0.3 + s["governance_score"] * 0.3
            if composite >= 85:
                level = "low"
            elif composite >= 70:
                level = "medium"
            elif composite >= 50:
                level = "high"
            else:
                level = "critical"

            risk_factors = []
            if s["renewable_energy_pct"] < 30:
                risk_factors.append("Low renewable energy adoption")
            if s["waste_recycling_pct"] < 50:
                risk_factors.append("Below-average waste recycling")
            if s["environmental_score"] < 60:
                risk_factors.append("Poor environmental score")
            if s["labor_score"] < 60:
                risk_factors.append("Labour practice concerns")

            result = {
                "supplier_id": supplier_id,
                "supplier_name": s["name"],
                "risk_level": level,
                "composite_score": round(composite, 1),
                "risk_factors": risk_factors,
            }
            return [TextContent(type="text", text=json.dumps(result, indent=2))]
    return [TextContent(type="text", text=f"Supplier {supplier_id} not found")]


async def main() -> None:
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
