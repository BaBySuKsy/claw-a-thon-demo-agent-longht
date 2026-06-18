EXTRACTION_PROMPT = """
Extract technical entities and relationships from the following text. 
Return a valid JSON object following the schema: {entities: [...], relationships: [...]}.
Focus on identifying Datasets, Pipelines, and Owners.
"""
