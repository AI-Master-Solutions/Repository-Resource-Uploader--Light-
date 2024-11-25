from agency_swarm import Agent
from .tools.document_analyzer import DocumentAnalyzer

class DocumentAgent(Agent):
    def __init__(self):
        super().__init__(
            name="Document Agent",
            description="Analyzes various document formats and extracts key information",
            instructions="./instructions.md",
            tools=[DocumentAnalyzer],
            temperature=0.5,
        )
    
    def process_notion_data(self, data):
        """Helper method to process data from Notion Retriever"""
        if data.get('type') != 'document':
            return "Not a document file"
        
        # Use the local path provided by Notion Retriever
        local_path = data.get('local_path')
        if not local_path:
            return "No local file path provided"
        
        return self.tools[0](file_path=local_path).run()