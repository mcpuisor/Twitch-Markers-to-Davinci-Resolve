#!/usr/bin/env python3
"""
Video Framerate Checker
Quick utility to check your video file's framerate before converting markers
"""

import sys
import subprocess
from pathlib import Path


def check_framerate(video_path):
    """Check video framerate using ffprobe or ffmpeg"""
    
    # Try ffprobe first (cleaner output)
    try:
        result = subprocess.run(
            ['ffprobe', '-v', 'error', '-select_streams', 'v:0', 
             '-show_entries', 'stream=r_frame_rate', '-of', 
             'default=noprint_wrappers=1:nokey=1', video_path],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0 and result.stdout.strip():
            # Parse fraction like "30/1" or "60000/1001"
            fps_str = result.stdout.strip()
            if '/' in fps_str:
                num, den = fps_str.split('/')
                fps = float(num) / float(den)
                return fps, 'ffprobe'
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    
    # Try ffmpeg if ffprobe not available
    try:
        result = subprocess.run(
            ['ffmpeg', '-i', video_path],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        # ffmpeg outputs to stderr
        output = result.stderr
        
        # Look for fps in output
        for line in output.split('\n'):
            if 'fps' in line.lower() and 'Stream' in line:
                # Extract fps value
                import re
                match = re.search(r'(\d+\.?\d*)\s*fps', line)
                if match:
                    fps = float(match.group(1))
                    return fps, 'ffmpeg'
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    
    return None, None


def get_recommendation(fps):
    """Get configuration recommendation based on fps"""
    if fps is None:
        return "Unable to determine"
    
    # Round to common framerates
    if abs(fps - 23.976) < 0.1 or abs(fps - 24) < 0.1:
        return "24 (film/cinematic)"
    elif abs(fps - 25) < 0.1:
        return "25 (PAL standard - DEFAULT)"
    elif abs(fps - 29.97) < 0.1 or abs(fps - 30) < 0.1:
        return "30 (most common for streaming)"
    elif abs(fps - 59.94) < 0.1 or abs(fps - 60) < 0.1:
        return "60 (high-motion gaming)"
    else:
        return f"{fps:.2f}"


def main():
    print("=" * 60)
    print("Video Framerate Checker")
    print("=" * 60)
    print()
    
    # Get video path
    if len(sys.argv) > 1:
        video_path = sys.argv[1]
    else:
        print("Drag and drop your video file here (or enter path):")
        video_path = input("> ").strip().strip('"').strip("'")
    
    if not video_path:
        print("Error: No file provided")
        sys.exit(1)
    
    # Check if file exists
    video_file = Path(video_path)
    if not video_file.exists():
        print(f"Error: File not found: {video_path}")
        sys.exit(1)
    
    print(f"Checking: {video_file.name}")
    print()
    
    # Check framerate
    fps, method = check_framerate(video_path)
    
    if fps is None:
        print("❌ Could not determine framerate!")
        print()
        print("Possible reasons:")
        print("  1. ffmpeg/ffprobe not installed")
        print("  2. Video file is corrupted")
        print("  3. Unsupported video format")
        print()
        print("To install ffmpeg:")
        print("  macOS: brew install ffmpeg")
        print("  Ubuntu: sudo apt-get install ffmpeg")
        print("  Windows: Download from https://ffmpeg.org/")
        sys.exit(1)
    
    print(f"✓ Framerate detected: {fps:.3f} fps (using {method})")
    print()
    
    recommendation = get_recommendation(fps)
    print("=" * 60)
    print("CONFIGURATION RECOMMENDATION:")
    print("=" * 60)
    
    if abs(fps - 25) < 0.1:
        print(f"✓ Your video is {fps:.3f} fps")
        print("✓ This matches the DEFAULT framerate (25 fps)")
        print("✓ NO CHANGES NEEDED - use scripts as-is!")
    else:
        print(f"⚠️  Your video is {fps:.3f} fps")
        print("⚠️  This does NOT match the default (25 fps)")
        print()
        print("YOU MUST EDIT THE SCRIPT before converting!")
        print()
        print(f"Change this line in twitch_markers_xml_gui.py or twitch_markers_xml_cli.py:")
        print()
        print("  FROM:")
        print("    converter = TwitchToXMLConverter(framerate=25)")
        print()
        print("  TO:")
        
        # Provide exact value based on detected fps
        if abs(fps - 30) < 0.5:
            print("    converter = TwitchToXMLConverter(framerate=30)")
        elif abs(fps - 60) < 0.5:
            print("    converter = TwitchToXMLConverter(framerate=60)")
        elif abs(fps - 24) < 0.5:
            print("    converter = TwitchToXMLConverter(framerate=24)")
        elif abs(fps - 29.97) < 0.5:
            print("    converter = TwitchToXMLConverter(framerate=29.97)")
        elif abs(fps - 59.94) < 0.5:
            print("    converter = TwitchToXMLConverter(framerate=59.94)")
        else:
            print(f"    converter = TwitchToXMLConverter(framerate={fps:.2f})")
    
    print()
    print("=" * 60)
    print()
    print("Common Twitch/streaming framerates:")
    print("  • 30 fps - Standard streaming (most common)")
    print("  • 60 fps - High-motion gaming")
    print("  • 25 fps - PAL standard (Europe)")
    print("  • 24 fps - Cinematic/film look")
    print()


if __name__ == "__main__":
    main()
