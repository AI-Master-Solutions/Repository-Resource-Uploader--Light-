from agency_swarm.tools import BaseTool
from pydantic import Field
import os
import requests
from notion_client import Client
from dotenv import load_dotenv
import re
import mimetypes
import tempfile
from urllib.parse import urlparse

load_dotenv()

notion = Client(auth=os.getenv("NOTION_API_KEY"))

class NotionDatabaseRetriever(BaseTool):
    """
    Tool to retrieve data from the input Notion database
    """
    database_id: str = Field(
        default="1278d3c0230680a9bca5c7b10cbed742",
        description="The ID of the input Notion database"
    )
    download_dir: str = Field(
        default=tempfile.gettempdir(),
        description="Directory to download files to"
    )

    def get_property_safely(self, properties, property_name):
        """Safely extract property value from Notion properties"""
        try:
            prop = properties.get(property_name, {})
            
            # Handle Title/Name property
            if property_name == 'Name':
                titles = prop.get('title', [])
                if titles:
                    return titles[0].get('text', {}).get('content', '')
                return ''
                
            # Handle URL/Link property
            elif property_name == 'Link':
                return prop.get('url', '')
                
            # Handle File property
            elif property_name == 'File':
                files = prop.get('files', [])
                if not files:
                    return None
                    
                file_obj = files[0]
                file_type = file_obj.get('type', '')
                
                if file_type == 'file':
                    return {
                        'url': file_obj.get('file', {}).get('url', ''),
                        'name': file_obj.get('name', '')
                    }
                elif file_type == 'external':
                    return {
                        'url': file_obj.get('external', {}).get('url', ''),
                        'name': file_obj.get('name', '')
                    }
                return None
                
        except Exception as e:
            print(f"Error extracting {property_name}: {str(e)}")
            return None if property_name == 'File' else ''

    def run(self):
        """Retrieves one item from the database"""
        try:
            # Query only one item
            response = notion.databases.query(
                database_id=self.database_id,
                page_size=1
            )
            
            if not response['results']:
                return {"status": "empty", "message": "No items to process"}
            
            page = response['results'][0]
            page_id = page['id']
            properties = page.get('properties', {})
            
            # Extract properties safely
            name = self.get_property_safely(properties, 'Name')
            link = self.get_property_safely(properties, 'Link')
            file_info = self.get_property_safely(properties, 'File')
            
            # Determine content type
            if file_info:
                content_type = self._identify_file_type(file_info)
            elif name.startswith('"') and name.endswith('"'):
                content_type = {'type': 'text', 'platform': 'text'}
            elif link:
                content_type = self._identify_content_type(link, name)
            else:
                content_type = {'type': 'unknown', 'platform': 'unknown'}
            
            return {
                'page_id': page_id,
                'name': name,
                'link': link,
                'file': file_info,
                'type': content_type['type'],
                'platform': content_type['platform']
            }
            
        except Exception as e:
            return f"Error retrieving from database: {str(e)}"

    def _process_file(self, file_obj, name):
        """Process file from Notion and download if necessary"""
        try:
            file_type = file_obj.get('type', 'external')
            
            if file_type == 'file':
                # Internal Notion file
                file_url = file_obj['file']['url']
                file_name = file_obj.get('name', name)
            elif file_type == 'external':
                # External file
                file_url = file_obj['external']['url']
                file_name = file_obj.get('name', name)
            else:
                return None
            
            # Download the file
            local_path = self._download_file(file_url, file_name)
            
            return {
                'name': file_name,
                'url': file_url,
                'path': local_path,
                'type': file_type
            }
            
        except Exception as e:
            print(f"Error processing file: {str(e)}")
            return None

    def _download_file(self, url, name):
        """Download file from URL to local storage"""
        try:
            # Create download directory if it doesn't exist
            os.makedirs(self.download_dir, exist_ok=True)
            
            # Get file extension from URL or name
            ext = os.path.splitext(urlparse(url).path)[1]
            if not ext:
                ext = os.path.splitext(name)[1]
            if not ext:
                # Try to guess extension from content type
                response = requests.head(url)
                content_type = response.headers.get('content-type', '')
                ext = mimetypes.guess_extension(content_type) or ''
            
            # Create safe filename
            safe_name = "".join([c for c in name if c.isalpha() or c.isdigit() or c in (' ', '-', '_')]).rstrip()
            filename = f"{safe_name}{ext}"
            local_path = os.path.join(self.download_dir, filename)
            
            # Download file
            response = requests.get(url)
            with open(local_path, 'wb') as f:
                f.write(response.content)
            
            return local_path
            
        except Exception as e:
            print(f"Error downloading file: {str(e)}")
            return None

    def _identify_content_type(self, link, name):
        """Helper method to identify content type from link and name"""
        # Check for quoted text first
        if name and name.startswith('"') and name.endswith('"'):
            return {'type': 'text', 'platform': 'text'}
        
        # Check for empty/missing link
        if not link:
            # Only return unknown if we don't have a text entry
            return {'type': 'unknown', 'platform': 'unknown'}
        
        link_lower = link.lower()
        
        # YouTube patterns
        youtube_patterns = {
            'watch': r'youtube\.com/watch\?v=[\w-]+',
            'shorts': r'youtube\.com/shorts/[\w-]+',
            'youtu.be': r'youtu\.be/[\w-]+'
        }
        
        # Instagram patterns
        instagram_patterns = {
            'reel': r'instagram\.com/reels?/[\w-]+',
            'post': r'instagram\.com/p/[\w-]+',
            'tv': r'instagram\.com/tv/[\w-]+'
        }
        
        # TikTok patterns
        tiktok_patterns = {
            'video': r'tiktok\.com/.+/video/[\w-]+',
            'vm': r'vm\.tiktok\.com/[\w-]+'
        }
        
        # Check YouTube
        for pattern in youtube_patterns.values():
            if re.search(pattern, link_lower):
                return {'type': 'video', 'platform': 'youtube'}
        
        # Check Facebook
        if 'facebook.com' in link_lower:
            return {'type': 'manual_processing', 'platform': 'facebook'}
        
        # Check Instagram
        for key, pattern in instagram_patterns.items():
            if re.search(pattern, link_lower):
                if key in ['reel', 'tv']:
                    return {'type': 'video', 'platform': 'instagram'}
                return {'type': 'website', 'platform': 'instagram'}
        
        # Check TikTok
        for pattern in tiktok_patterns.values():
            if re.search(pattern, link_lower):
                return {'type': 'video', 'platform': 'tiktok'}
        
        return {'type': 'website', 'platform': 'web'}

if __name__ == "__main__":
    tool = NotionDatabaseRetriever()
    print(tool.run())