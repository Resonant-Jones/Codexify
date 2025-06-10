"""
This file aims to provide a state action pair for agent to do action in a more simple
way.

Each agent should have a router connected. The following diagram explain how it should communicate
Agent<-->Router<--> Server <--> Router <--> Agent
"""

from .server import Server
from ..agent.agent import Agent

from pydantic import BaseModel


class Router(object):
    """
    The purpsoe of router is to simplify the communication between agent
    [OK actually i want to develope this as a lib but i don't have time and i think this idea is so awesome hahahha]
    """

    def __init__(
        self,
        server: Server,
        agent: Agent,
        send_format: BaseModel = None,
        recv_format: BaseModel = None,
    ):
        self.send_format = send_format
        self.recv_format = recv_format
        self.server = server
        self.agent = agent

    def send_response(self, response):
        return response

    async def recv_response(self, message, data=None):
        """
        An agent receive the message from other agent
        use the run function and send it back to server
        """
        res = await self.agent.run(message, data)
        return self.send_response(res)

    def set_send_format(self, s: BaseModel):
        self.send_format = s

    def set_recv_format(self, r: BaseModel):
        self.recv_format = r

    def get_send_format(self):
        self.agent.get_send_format()

    def get_recv_format(self):
        self.agent.get_recv_format()
