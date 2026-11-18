#!/usr/bin/env python3
"""
YouTube Transcript Extractor
Extracts transcripts from YouTube videos using youtube-transcript-api.
"""

import argparse
import sys
import subprocess
import re


def check_dependencies():
    """Check if youtube-transcript-api is installed, install if not."""
    try:
        from youtube_transcript_api import YouTubeTranscriptApi
        return YouTubeTranscriptApi
    except ImportError:
        print("youtube-transcript-api not found. Installing...")
        subprocess.run([sys.executable, "-m", "pip", "install", "--break-system-packages", "youtube-transcript-api"], check=True)
        from youtube_transcript_api import YouTubeTranscriptApi
        return YouTubeTranscriptApi


def extract_video_id(url_or_id):
    """Extract video ID from various YouTube URL formats."""
    # Already a video ID (11 characters)
    if re.match(r'^[a-zA-Z0-9_-]{11}$', url_or_id):
        return url_or_id

    # Standard YouTube URL
    match = re.search(r'(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/embed/)([a-zA-Z0-9_-]{11})', url_or_id)
    if match:
        return match.group(1)

    raise ValueError(f"Could not extract video ID from: {url_or_id}")


def format_timestamp(seconds):
    """Format seconds to MM:SS or HH:MM:SS."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)

    if hours > 0:
        return f"[{hours:02d}:{minutes:02d}:{secs:02d}]"
    return f"[{minutes:02d}:{secs:02d}]"


def get_transcript(video_id, include_timestamps=False):
    """
    Get transcript for a YouTube video.

    Args:
        video_id: YouTube video ID
        include_timestamps: Whether to include timestamps

    Returns:
        Transcript text
    """
    YouTubeTranscriptApi = check_dependencies()

    try:
        # New API v1.x: instantiate and use fetch method
        api = YouTubeTranscriptApi()
        # Request English only, no translation
        transcript_data = api.fetch(video_id, languages=['en', 'en-US', 'en-GB'])

        # Format output
        lines = []
        for entry in transcript_data:
            # New API uses object attributes instead of dict
            text = entry.text.replace('\n', ' ').strip()
            if include_timestamps:
                timestamp = format_timestamp(entry.start)
                lines.append(f"{timestamp} {text}")
            else:
                lines.append(text)

        if include_timestamps:
            return '\n'.join(lines)
        else:
            # Join into paragraphs for plain text
            return ' '.join(lines)

    except Exception as e:
        raise Exception(f"Could not get transcript: {str(e)}")


def main():
    parser = argparse.ArgumentParser(
        description="Extract transcripts from YouTube videos"
    )
    parser.add_argument("url", help="YouTube video URL or ID")
    parser.add_argument(
        "--timestamps", "-t",
        action="store_true",
        help="Include timestamps in output"
    )
    parser.add_argument(
        "--output", "-o",
        help="Output file path (prints to stdout if not specified)"
    )

    args = parser.parse_args()

    try:
        video_id = extract_video_id(args.url)
        print(f"Extracting transcript for video: {video_id}", file=sys.stderr)

        transcript = get_transcript(video_id, args.timestamps)

        if args.output:
            with open(args.output, 'w', encoding='utf-8') as f:
                f.write(transcript)
            print(f"Transcript saved to: {args.output}", file=sys.stderr)
        else:
            print(transcript)

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
