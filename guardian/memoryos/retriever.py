class Retriever:
    def retrieve_context(self, user_query, user_id):
        return {
            "retrieved_pages": [],
            "retrieved_user_knowledge": [],
            "retrieved_assistant_knowledge": [],
        }