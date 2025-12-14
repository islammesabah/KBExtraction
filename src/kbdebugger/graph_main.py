from kbdebugger.graph.retriever import KnowledgeGraphRetriever

retriever = KnowledgeGraphRetriever(limit_per_pattern=20)
hits = retriever.retrieve("requirement")  # includes match_pattern by default
retriever.pretty_print(hits)
