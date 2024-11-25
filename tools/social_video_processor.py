from agency_swarm.tools import BaseTool
from pydantic import Field
import yt_dlp
import os
import logging
import whisper
from moviepy.editor import VideoFileClip
import tempfile
from pathlib import Path
from datetime import datetime

class SocialVideoProcessor(BaseTool):
    """
    Tool to download and process videos from social media platforms
    """
    retriever_data: dict = Field(
        ..., 
        description="The complete data object from the Notion Retriever"
    )

    def __init__(self, **data):
        super().__init__(**data)
        self._temp_dir = tempfile.mkdtemp()
        self._whisper_model = whisper.load_model("base")
        self._ydl_opts = {
            'format': 'best',  # Get best quality
            'outtmpl': os.path.join(self._temp_dir, '%(title)s.%(ext)s'),
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
            # Add required HTTP headers
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
        }

    def run(self):
        try:
            # Get video URL from retriever data
            video_url = self.retriever_data.get('link')
            if not video_url:
                raise Exception("No video URL provided")

            # Process video and get info
            video_info = self._process_video(video_url)
            
            # Create a copy of the original data
            processed_data = self.retriever_data.copy()
            
            # Add processed content
            processed_data['processed_content'] = {
                'title': video_info.get('title', 'Unknown Title'),
                'transcript': video_info.get('transcript', 'No transcript available'),
                'view_count': video_info.get('view_count', 0),
                'like_count': video_info.get('like_count', 0),
                'processing_agent': 'Social Video Agent'
            }
            
            return processed_data
            
        except Exception as e:
            # Return error in a format that matches other agents
            processed_data = self.retriever_data.copy()
            processed_data['processed_content'] = {
                'title': 'Error Processing Video',
                'error': str(e),
                'processing_agent': 'Social Video Agent'
            }
            return processed_data

    def _process_video(self, video_url):
        """Process video and return metadata"""
        try:
            with yt_dlp.YoutubeDL(self._ydl_opts) as ydl:
                # Extract video info first
                info = ydl.extract_info(video_url, download=False)
                if not info:
                    raise Exception("Could not extract video info")

                # Download the video
                video_path = ydl.prepare_filename(info)
                ydl.download([video_url])

                if not os.path.exists(video_path):
                    raise Exception("Video download failed")

                # Extract audio for transcription
                video = VideoFileClip(video_path)
                audio_path = os.path.join(self._temp_dir, "audio.wav")
                video.audio.write_audiofile(audio_path, logger=None)
                video.close()

                # Generate transcript
                result = self._whisper_model.transcribe(audio_path)
                transcript = result["text"]

                # Clean up temp files
                os.remove(audio_path)
                os.remove(video_path)

                return {
                    "title": info.get("title", ""),
                    "view_count": info.get("view_count", 0),
                    "like_count": info.get("like_count", 0),
                    "transcript": transcript
                }

        except Exception as e:
            logging.error(f"Error processing video: {str(e)}")
            return {"error": str(e)}

    def __del__(self):
        """Cleanup temporary files"""
        try:
            if hasattr(self, '_temp_dir') and self._temp_dir:
                import shutil
                shutil.rmtree(self._temp_dir)
        except Exception as e:
            if hasattr(logging, 'error'):
                logging.error(f"Error cleaning up temp files: {str(e)}")

if __name__ == "__main__":
    # Test with a public social media video
    tool = SocialVideoProcessor(
        retriever_data={
            'link': "https://www.instagram.com/reel/DBy1aprRNXe/?utm_source=ig_web_copy_link",
            'platform': "instagram",
            'transcribe': True
        }
    )
    print(tool.run())