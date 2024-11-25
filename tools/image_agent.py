from agency_swarm import Agent
from .tools.image_analyzer import ImageAnalyzer

class ImageAgent(Agent):
    def __init__(self):
        super().__init__(
            name="Image Agent",
            description="Analyzes images and generates detailed descriptions",
            instructions="./instructions.md",
            tools=[ImageAnalyzer],
            temperature=0.5,
        )
    
    def process_notion_data(self, data):
        """Helper method to process data from Notion Retriever"""
        if data.get('type') != 'image':
            return "Not an image file"
        
        # Use the local path provided by Notion Retriever
        local_path = data.get('local_path')
        if not local_path:
            return "No local file path provided"
        
        return self.tools[0](image_path=local_path).run()