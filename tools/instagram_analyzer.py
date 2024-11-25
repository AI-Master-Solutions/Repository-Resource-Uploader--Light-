from agency_swarm.tools import BaseTool
from pydantic import Field
import instaloader
import os
from dotenv import load_dotenv
import re
from typing import Optional, ClassVar
from openai import OpenAI

load_dotenv()

client = OpenAI(
    api_key=os.environ.get("OPENAI_API_KEY"),
)

class InstagramAnalyzer(BaseTool):
    """
    Tool to analyze Instagram posts and extract essential information
    """
    retriever_data: dict = Field(
        ..., 
        description="The complete data object from the Notion Retriever"
    )
    
    _loader: ClassVar[Optional[instaloader.Instaloader]] = None
    
    @property
    def loader(self) -> instaloader.Instaloader:
        if InstagramAnalyzer._loader is None:
            InstagramAnalyzer._loader = instaloader.Instaloader(
                download_pictures=False,
                download_videos=False,
                download_video_thumbnails=False,
                save_metadata=True,
                quiet=True
            )
            
            if os.getenv("INSTAGRAM_USERNAME") and os.getenv("INSTAGRAM_PASSWORD"):
                try:
                    InstagramAnalyzer._loader.login(
                        os.getenv("INSTAGRAM_USERNAME"),
                        os.getenv("INSTAGRAM_PASSWORD")
                    )
                except Exception as e:
                    print(f"Login failed: {str(e)}")
        
        return InstagramAnalyzer._loader

    def _analyze_content(self, content):
        """Analyze content using GPT-4o-mini"""
        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": """Extract the following from this Instagram post:
                        1. Title: Create a title based on the content
                        2. Description: Summarize the main message
                        3. Content: Key points or themes
                        4. Keywords: Important terms or themes (excluding hashtags)
                        
                        Format response exactly as:
                        Title: [title]
                        Description: [description]
                        Content: [content]
                        Keywords: [keyword1, keyword2, ...]"""
                    },
                    {
                        "role": "user",
                        "content": f"Analyze this Instagram content:\n{content}"
                    }
                ],
                temperature=0.3,
                max_tokens=500
            )
            
            # Parse the response into a dictionary
            result = {}
            response_text = response.choices[0].message.content
            
            for line in response_text.split('\n'):
                if ':' in line:
                    key, value = line.split(':', 1)
                    key = key.strip().lower()
                    value = value.strip()
                    # Convert keywords string to list
                    if key == 'keywords':
                        value = [k.strip() for k in value.strip('[]').split(',')]
                    result[key] = value if value else 'Not available'
            
            return result
            
        except Exception as e:
            return {
                'title': 'Error in analysis',
                'description': 'Not available',
                'content': f'Error analyzing content: {str(e)}',
                'keywords': []
            }

    def run(self):
        try:
            # Get Instagram URL from retriever data
            instagram_url = self.retriever_data.get('link')
            if not instagram_url:
                raise Exception("No Instagram URL provided")

            shortcode = re.search(r'/p/([^/]+)/', instagram_url)
            if not shortcode:
                shortcode = re.search(r'/reel/([^/]+)/', instagram_url)
            if not shortcode:
                raise Exception("Invalid Instagram URL")
            
            shortcode = shortcode.group(1)
            post = instaloader.Post.from_shortcode(self.loader.context, shortcode)
            
            # Extract hashtags
            hashtags = []
            if post.caption:
                hashtags = re.findall(r'#(\w+)', post.caption)
            
            # Get AI analysis of content
            analysis = self._analyze_content(post.caption if post.caption else "")
            
            # Ensure keywords is always a list
            ai_keywords = analysis.get('keywords', [])
            if isinstance(ai_keywords, str):
                ai_keywords = [ai_keywords]
            
            # Combine AI keywords with hashtags
            all_keywords = list(set(ai_keywords + hashtags))
            
            # Create a copy of the original data
            processed_data = self.retriever_data.copy()
            
            # Add processed content
            processed_data['processed_content'] = {
                'title': analysis.get('title', 'Instagram post'),
                'author': post.owner_username,
                'description': analysis.get('description', 'No description available'),
                'content': analysis.get('content', 'No content available'),
                'keywords': all_keywords,
                'processing_agent': 'Instagram Agent'
            }
            
            return processed_data

        except Exception as e:
            return f"Error analyzing Instagram post: {str(e)}"

if __name__ == "__main__":
    # Test with sample retriever data
    test_data = {
        'page_id': 'test_page_id',
        'name': 'Test Instagram Post',
        'type': 'website',
        'platform': 'instagram',
        'link': 'https://www.instagram.com/p/DBtGC0bAGFq/'
    }
    tool = InstagramAnalyzer(retriever_data=test_data)
    print(tool.run())