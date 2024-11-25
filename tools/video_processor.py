from agency_swarm.tools import BaseTool
from pydantic import Field
import os
from pytube import YouTube
from youtube_transcript_api import YouTubeTranscriptApi
import re
from dotenv import load_dotenv
import urllib.request
import json

load_dotenv()

def get_video_info(video_id):
    """Get video info directly from YouTube"""
    url = f"https://www.youtube.com/watch?v={video_id}"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    request = urllib.request.Request(url, headers=headers)
    response = urllib.request.urlopen(request)
    html = response.read().decode('utf-8')
    
    # Extract title
    title_match = re.search(r'"title":"([^"]+)"', html)
    title = title_match.group(1) if title_match else "Unknown Title"
    
    # Extract channel name
    channel_match = re.search(r'"channelName":"([^"]+)"', html)
    channel = channel_match.group(1) if channel_match else "Unknown Channel"
    
    return {
        'title': title,
        'channel': channel,
    }

class VideoProcessor(BaseTool):
    """
    Tool to process standard YouTube videos and extract information
    """
    retriever_data: dict = Field(
        ..., 
        description="The complete data object from the Notion Retriever"
    )

    def run(self):
        """
        Processes a YouTube video and appends analysis to retriever data
        """
        try:
            # Get video URL from retriever data
            video_url = self.retriever_data.get('link')
            if not video_url:
                raise Exception("No video URL provided")

            if 'youtube.com/watch' in video_url or 'youtu.be' in video_url:
                # Process the video
                video_info = self._process_youtube_video(video_url)
                
                # Create a copy of the original data
                processed_data = self.retriever_data.copy()
                
                # Add processed content
                processed_data['processed_content'] = {
                    'title': video_info.get('title', 'Unknown Title'),
                    'channel': video_info.get('channel', 'Unknown Channel'),
                    'platform': 'YouTube',
                    'transcript': video_info.get('transcript', 'No transcript available'),
                    'processing_agent': 'Video Agent',
                    'views': video_info.get('views', 0),
                    'publish_date': video_info.get('publish_date', 'Unknown Date')
                }
                
                return processed_data
            else:
                return "This tool only processes standard YouTube videos"

        except Exception as e:
            return f"Error processing video: {str(e)}"

    def _process_youtube_video(self, url):
        """Process YouTube video specifically"""
        try:
            # Extract video ID
            video_id = self._extract_youtube_id(url)
            if not video_id:
                return "Could not extract video ID"
            
            # Get video info directly
            info = get_video_info(video_id)
            
            # Add additional info
            info.update({
                'platform': 'YouTube',
                'url': url,
                'views': 0,  # Default value as we can't reliably get this
                'publish_date': 'Unknown Date'
            })
            
            # Get transcript if available
            try:
                print(video_id)
                transcript = YouTubeTranscriptApi.get_transcript(video_id)
                info['transcript'] = ' '.join([entry['text'] for entry in transcript])
            except:
                info['transcript'] = "No transcript available"
            
            return info

        except Exception as e:
            return f"Error processing YouTube video: {str(e)}"

    def _extract_youtube_id(self, url):
        """Extract YouTube video ID from URL"""
        try:
            from urllib.parse import urlparse, parse_qs
            
            # Handle different URL formats
            parsed_url = urlparse(url)
            
            if 'youtube.com' in parsed_url.netloc:
                if 'watch' in parsed_url.path:
                    # Standard watch URL
                    return parse_qs(parsed_url.query)['v'][0]
                elif 'shorts' in parsed_url.path:
                    # Shorts URL
                    return parsed_url.path.split('/shorts/')[1]
                elif 'embed' in parsed_url.path:
                    # Embedded URL
                    return parsed_url.path.split('/embed/')[1]
            elif 'youtu.be' in parsed_url.netloc:
                # Short URL
                return parsed_url.path[1:]
                
            return None
            
        except Exception as e:
            print(f"Error extracting video ID: {str(e)}")
            return None

if __name__ == "__main__":
    # Test with sample retriever data
    test_data = {
        'page_id': 'test_page_id',
        'name': 'Test Video',
        'type': 'video',
        'platform': 'youtube',
        'link': 'https://www.youtube.com/watch?v=Og73plUTabs'
    }
    tool = VideoProcessor(retriever_data=test_data)
    print(tool.run())