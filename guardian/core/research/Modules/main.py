"""
    This is the main function of the agent
"""
import json 

from src.agent import Planner, Agent
from src.router import Server , Router 

async def generate_report(query , planner:Planner , agents:list[Agent]):
    planner.query = query
    server = Server()

    planner_router = Router(server , planner)    
    server.add_router(planner.name , planner_router)

    for agent in agents:
        r = Router(server , agent)
        server.add_router(agent.name , r)
        planner.add_model(agent.name , agent.description)
    server.set_initial_router(planner.name , query)

    report = await server.start(query= query)
    report = report['data']

    with open("report.md", "w", encoding="utf-8") as file:
        file.write(report + "\n\n") 
    return report
    
def read_config():
    """
        TODO: should this be place in util folder ?  
    """
    with open("./config.json", 'r') as file:
        content = file.read()
        config = json.loads(content)
    return config


