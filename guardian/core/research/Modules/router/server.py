from __future__ import annotations


class Server:
    """
    workflow:
        planner:
            state 1: no more planning / no more planning step / staisfy response ; action: return response
            state 2: more information about this subject is requried before writing report ; action: browser agent
            state 3: local information is needed (requrie by the use for example) ; action: send to local RAG query
            state 4: retrival information from previous round ; action: RAG query
            state 5: enough information to write the report / response ; action writer

        search:
            state 1: no more searching step ; action summarize current db --> send back to planner
            state 2: no next url in the searching space; action: based on available searching api --> search relevant information
            state 3: have next url --> search relevent content and script the list of available website (selected by LLM)

        retrival:
            state 1: no more searching step action terminate
            state 2: not enough content --> action: summary with local top k selected document [TODO: maybe save in sqlite3 ?]
            state 3: enough content --> action return summary
    """

    def __init__(self):
        self.routers: dict = {}
        self.router_list: list = []
        self.initial_router: str = ""
        self.next_router = None
        self.data = []

    def recv_message(self):
        pass

    async def start(self, query: str):
        """
        start the workflow
        """
        self.next_router = self.routers[self.initial_router]

        while True:
            query = await self.next_router.recv_response(query, self.data)
            if self.check_response(query):
                return query

            self.next_router, query, self.data = self.query_handler(query)

    def query_handler(self, query: dict):
        """
        This should parese the query and get
        1. which agent it want to send to i.e next router
        step one is find next router and parse the prompt with corresponding class
        2. pase to the format the next agent could accept
        return Next agent , parsed to basemode response
        {
            "next_router": str

        }
        """
        return self.routers[query["agent"]], query["task"], query["data"]

    def check_response(self, msg: dict):
        """
        Check if the message is terminate message
        Please note that for our case only planner could have the right
        to terminate the process.
        Other agent typically should route back to the planner agent
        """
        if msg["agent"] == "TERMINATE":
            return True
        return False

    def set_initial_router(self, name: str, msg: str):
        self.initial_router = name
        self.initial_message = msg

    def add_router(self, name: str, router: "Router"):
        self.routers[name] = router
        self.router_list.append(name)
