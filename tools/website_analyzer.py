from agency_swarm.tools import BaseTool
from pydantic import Field
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse
import os
from dotenv import load_dotenv
from openai import OpenAI
import re
from datetime import datetime

load_dotenv()

client = OpenAI(
    api_key=os.environ.get("OPENAI_API_KEY"),
)

class WebsiteAnalyzer(BaseTool):
    """
    Tool to analyze websites and extract relevant information
    """
    retriever_data: dict = Field(
        ..., 
        description="The complete data object from the Notion Retriever"
    )

    def run(self):
        """
        Analyzes a website and appends analysis to retriever data
        """
        try:
            # Get website URL from retriever data
            website_url = self.retriever_data.get('link')
            if not website_url:
                raise Exception("No website URL provided")

            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            response = requests.get(website_url, headers=headers)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Get website name
            website_name = urlparse(website_url).netloc
            
            # Find publication date
            publish_date = self._find_publish_date(soup)
            
            # Use GPT to identify the main content
            content = self._identify_main_content(soup.get_text(separator=' ', strip=True))
            
            # Create a copy of the original data
            processed_data = self.retriever_data.copy()
            
            # Add processed content
            processed_data['processed_content'] = {
                'title': self._find_title(soup),
                'author': self._find_author(soup),
                'website_name': website_name,
                'content': content,
                'published_date': publish_date,
                'processing_agent': 'Website Agent'
            }
            
            return processed_data

        except Exception as e:
            return f"Error analyzing website: {str(e)}"

    def _find_publish_date(self, soup):
        """Try to find publication date in various formats"""
        # Common meta tags for dates
        date_meta_tags = [
            'article:published_time',
            'datePublished',
            'date',
            'pubdate',
            'publishdate',
            'og:published_time'
        ]
        
        for tag in date_meta_tags:
            date = soup.find('meta', property=tag) or soup.find('meta', attrs={'name': tag})
            if date and date.get('content'):
                return date['content']
        
        # Look for time tags
        time_tag = soup.find('time')
        if time_tag and time_tag.get('datetime'):
            return time_tag['datetime']
        
        return 'Not available'

    def _find_title(self, soup):
        """Find the main title of the page"""
        # Try article title first
        article_title = soup.find('h1')
        if article_title:
            return article_title.get_text(strip=True)
        
        # Fallback to page title
        if soup.title:
            return soup.title.string.strip()
        
        return 'Not available'

    def _find_author(self, soup):
        """Try to find author information"""
        # Common author meta tags and classes
        author_elements = [
            soup.find('meta', property='author'),
            soup.find('meta', attrs={'name': 'author'}),
            soup.find(class_='author'),
            soup.find(attrs={'rel': 'author'}),
            soup.find('a', class_='author')
        ]
        
        for element in author_elements:
            if element:
                if element.get('content'):
                    return element['content']
                return element.get_text(strip=True)
        
        return 'Not available'

    def _identify_main_content(self, text):
        """Use GPT to identify the main content of the page"""
        try:
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system",
                        "content": """You are a content extractor. Your task is to identify and extract the main content from a webpage.
                        For articles: Extract the full article text
                        For social media: Extract the post content
                        For product pages: Extract the product description
                        
                        Return ONLY the raw content, without any analysis or modification."""
                    },
                    {
                        "role": "user",
                        "content": f"Extract the main content from this webpage:\n{text[:4000]}"
                    }
                ],
                temperature=0.3,
                max_tokens=1500
            )
            
            return response.choices[0].message.content.strip()

        except Exception as e:
            return f"Error extracting content: {str(e)}"

if __name__ == "__main__":
    # Test with sample retriever data
    test_data = {
        'page_id': 'test_page_id',
        'name': 'Test Website',
        'type': 'website',
        'platform': 'web',
        'link': 'https://example.com'
    }
    tool = WebsiteAnalyzer(retriever_data=test_data)
    print(tool.run())