from agency_swarm.tools import BaseTool
from pydantic import Field
import os
from notion_client import Client
from dotenv import load_dotenv

load_dotenv()

notion = Client(auth=os.getenv("NOTION_API_KEY"))

class NotionContentPusher(BaseTool):
    """
    Tool to push processed content to output Notion database
    """
    content_data: dict = Field(
        ..., 
        description="The processed content data to push to Notion"
    )
    database_id: str = Field(
        default="1468d3c0230680309104f004b3aa2b06",
        description="The ID of the output Notion database"
    )

    def run(self):
        """
        Moves the page to output database and updates its properties
        """
        try:
            # Extract page_id from content_data
            page_id = self.content_data.get('page_id')
            if not page_id:
                return {"error": "No page_id provided in content_data"}

            # First, move the page to the output database
            moved_page = notion.pages.update(
                page_id=page_id,
                parent={"database_id": self.database_id}
            )
            
            # Then update the page with processed content
            properties = self._format_properties()
            updated_page = notion.pages.update(
                page_id=page_id,
                properties=properties
            )
            
            return {
                "status": "success",
                "message": "Page moved and updated successfully",
                "page_id": updated_page['id']
            }

        except Exception as e:
            return f"Error updating Notion: {str(e)}"

    def _format_properties(self):
        """Format the content data according to Notion's API requirements"""
        processed_content = self.content_data.get('processed_content', {})
        content_type = self.content_data.get('type', 'unknown')
        
        # Initialize properties with required fields
        properties = {
            # Type of Information (select)
            "Type of Information": {
                "select": {"name": content_type}
            }
        }

        # Title (title)
        if 'title' in processed_content:
            properties["Title"] = {
                "title": [{"text": {"content": processed_content['title']}}]
            }

        # File Extension / Format (rich_text)
        if content_type == 'document' and 'metadata' in processed_content:
            if 'file_type' in processed_content['metadata']:
                properties["File Extension / Format"] = {
                    "rich_text": [{"text": {"content": processed_content['metadata']['file_type']}}]
                }

        # Summary/Key Points/Description/Transcript (rich_text)
        content_field_mapping = {
            'text': 'generated_questions',
            'video': 'transcript',
            'website': 'content',
            'image': 'description',
            'document': 'summary'
        }
        
        content_field = content_field_mapping.get(content_type)
        if content_field and content_field in processed_content:
            content_value = processed_content[content_field]
            if isinstance(content_value, list):
                content_value = "\n• " + "\n• ".join(content_value)
            properties["Summary/Key Points/Description/Transcript"] = {
                "rich_text": [{"text": {"content": str(content_value)}}]
            }

        # Channel/Account/Author (rich_text)
        author_field = processed_content.get('channel') or processed_content.get('author')
        if author_field:
            properties["Channel/Account/Author"] = {
                "rich_text": [{"text": {"content": author_field}}]
            }

        # Like Count (number)
        if 'like_count' in processed_content:
            properties["Like Count"] = {
                "number": int(processed_content['like_count'])
            }

        # View Count/Size Kb (number)
        size_field = (
            processed_content.get('view_count') or 
            processed_content.get('size_kb') or 
            processed_content.get('metadata', {}).get('word_count')
        )
        if size_field:
            properties["View Count/Size Kb"] = {
                "number": int(size_field)
            }

        # Website name (rich_text)
        if 'website_name' in processed_content:
            properties["Website name"] = {
                "rich_text": [{"text": {"content": processed_content['website_name']}}]
            }

        # Published Date (date)
        if 'published_date' in processed_content:
            properties["Published Date"] = {
                "date": {"start": processed_content['published_date']}
            }

        # Dimensions (rich_text)
        if 'dimensions' in processed_content:
            properties["Dimensions"] = {
                "rich_text": [{"text": {"content": processed_content['dimensions']}}]
            }

        # Resource Tags (relation) - needs configuration with actual database IDs
        tags = self._get_resource_tags(content_type)
        if tags:
            properties["Resource Tags"] = {
                "relation": [{"id": tag_id} for tag_id in tags]
            }

        return properties

    def _get_resource_tags(self, content_type):
        """Get appropriate resource tags based on content type"""
        # This needs to be configured with actual tag IDs from your Notion database
        tag_mapping = {
            'text': ['text_content_tag_id'],
            'video': ['video_content_tag_id'],
            'website': ['web_content_tag_id'],
            'image': ['image_content_tag_id'],
            'document': ['document_tag_id']
        }
        
        # Add platform-specific tags
        platform_tags = {
            'youtube': 'youtube_tag_id',
            'instagram': 'instagram_tag_id',
            'social_media': 'social_media_tag_id'
        }
        
        tags = tag_mapping.get(content_type, [])
        platform = self.content_data.get('platform')
        if platform in platform_tags:
            tags.append(platform_tags[platform])
            
        return tags

    def tag_video_content(self, page_id):
        """Tag video content with appropriate UUID"""
        try:
            # Get all available tag UUIDs
            tag_uuids = self.get_tag_uuids()
            
            # Get video tag UUID
            video_tag_id = tag_uuids.get('video')
            if not video_tag_id:
                raise Exception("Video tag UUID not found")
            
            # Update the page with correct UUID
            notion.pages.update(
                page_id=page_id,
                properties={
                    "Resource Tags": {
                        "relation": [
                            {"id": video_tag_id}
                        ]
                    }
                }
            )
            
        except Exception as e:
            print(f"Error tagging content: {str(e)}")

if __name__ == "__main__":
    test_data = {
        "page_id": "1498d3c023068049911be89e90204fa4",
        "type": "video",
        "platform": "youtube",
        "processed_content": {
            "title": "Test Video",
            "channel": "Test Channel",
            "transcript": "Test transcript",
            "view_count": 1000,
            "like_count": 100
        }
    }
    
    tool = NotionContentPusher(
        content_data=test_data,
        database_id="1468d3c0230680309104f004b3aa2b06"
    )
    print(tool.run()) 