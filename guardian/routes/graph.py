"""
Graph Routes
~~~~~~~~~~~~

Neo4j graph visualization and health check endpoints.
"""

import os
import logging
from typing import Dict, Any
from fastapi import APIRouter, HTTPException, Depends
from neo4j import GraphDatabase

logger = logging.getLogger(__name__)

# Optional Neo4j driver session provider
try:
    from guardian.db.neo import get_session as get_neo_session
    NEO4J_AVAILABLE = True
except Exception as e:
    logging.warning(f"[Codexify ⚠️] Neo4j driver not available: {e}")
    get_neo_session = None
    NEO4J_AVAILABLE = False

router = APIRouter(tags=["Graph"])


@router.get('/graph', summary='Return graph data from Neo4j')
def get_graph(scope: str = 'codexify'):
    """
    Fetch graph data from Neo4j and return nodes and links.

    Args:
        scope: Scope for the graph query (default: 'codexify')

    Returns:
        Dictionary containing nodes and links arrays
    """
    uri = os.getenv('NEO4J_URI', 'bolt://neo4j:7687')
    user = os.getenv('NEO4J_USER', 'neo4j')
    password = os.getenv('NEO4J_PASSWORD', 'test')

    try:
        driver = GraphDatabase.driver(uri, auth=(user, password))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f'Failed to connect to Neo4j: {e}')

    nodes, links = [], []
    try:
        with driver.session() as session:
            result = session.run('MATCH (a)-[r]->(b) RETURN a, r, b LIMIT 250')
            for record in result:
                a, r, b = record['a'], record['r'], record['b']
                nodes.extend([
                    {"id": a.element_id, "label": a.get('name', list(a.labels)[0] if a.labels else 'Node'), "type": list(a.labels)[0] if a.labels else 'node'},
                    {"id": b.element_id, "label": b.get('name', list(b.labels)[0] if b.labels else 'Node'), "type": list(b.labels)[0] if b.labels else 'node'}
                ])
                links.append({"source": a.element_id, "target": b.element_id, "label": r.type})
    except Exception as e:
        raise HTTPException(status_code=500, detail=f'Graph query failed: {e}')
    finally:
        driver.close()

    unique_nodes = list({n['id']: n for n in nodes}.values())
    return {"nodes": unique_nodes, "links": links}


@router.get("/health/neo4j", tags=["Health"])
async def neo4j_health(session=Depends(get_neo_session) if NEO4J_AVAILABLE and get_neo_session else None):
    """
    Check Neo4j database health.

    Returns:
        Health status dictionary
    """
    if not NEO4J_AVAILABLE or not get_neo_session:
        raise HTTPException(status_code=503, detail="Neo4j driver not available")

    try:
        await session.run("RETURN 1 AS ok")
        return {"ok": True}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
