from agency_swarm.tools import BaseTool
from pydantic import Field
import nltk
from nltk.tokenize import sent_tokenize
from dotenv import load_dotenv

load_dotenv()

# Download required NLTK data
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt')

class TextAnalyzer(BaseTool):
    """
    Tool to analyze and expand upon text content
    """
    retriever_data: dict = Field(
        ..., 
        description="The complete data object from the Notion Retriever"
    )

    def run(self):
        """
        Analyzes text content and appends analysis to retriever data
        """
        try:
            # Get the text content from the name field (quoted text)
            text_content = self.retriever_data.get('name', '').strip('"')
            
            # Split into sentences for question generation
            sentences = sent_tokenize(text_content)
            
            # Generate questions based on content
            questions = self._generate_questions(sentences)
            
            # Create a copy of the original data
            processed_data = self.retriever_data.copy()
            
            # Add processed content
            processed_data['processed_content'] = {
                'title': f"Text Analysis: {text_content[:50]}...",
                'generated_questions': questions,
                'processing_agent': 'Text Agent'
            }
            
            return processed_data

        except Exception as e:
            return f"Error analyzing text: {str(e)}"

    def _generate_questions(self, sentences):
        """Generate basic questions from the text"""
        questions = []
        for sentence in sentences[:3]:  # Generate questions from first 3 sentences
            # Simple question generation by replacing subject with "what"
            question = sentence.strip()
            if question.endswith('.'):
                question = question[:-1] + '?'
                question = 'What ' + question[question.find(' ')+1:].lower()
                questions.append(question)
        return questions

if __name__ == "__main__":
    # Test with sample retriever data
    test_data = {
        'page_id': 'test_page_id',
        'name': '"This is a sample text. It contains multiple sentences. We can analyze it to generate questions."',
        'type': 'text',
        'platform': 'text'
    }
    tool = TextAnalyzer(retriever_data=test_data)
    print(tool.run())