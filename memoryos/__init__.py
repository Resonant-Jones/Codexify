class Memoryos:
    def __init__(
        self,
        short_term_capacity=100,
        mid_term_capacity=50,
        long_term_knowledge_capacity=1000,
        retrieval_queue_capacity=50,
        mid_term_heat_threshold=5.0,
        llm_model="gpt-4",
        **kwargs
    ):
        # Core config with safe defaults
        self.short_term_capacity = short_term_capacity
        self.mid_term_capacity = mid_term_capacity
        self.long_term_knowledge_capacity = long_term_knowledge_capacity
        self.retrieval_queue_capacity = retrieval_queue_capacity
        self.mid_term_heat_threshold = mid_term_heat_threshold

        # Always define the LLM model before using it downstream
        self.llm_model = llm_model

        # Now initialize any downstream components that depend on self.llm_model
        # For example:
        # self.updater = Updater(llm_model=self.llm_model)
