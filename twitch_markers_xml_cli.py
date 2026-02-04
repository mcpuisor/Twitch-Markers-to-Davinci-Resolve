#!/usr/bin/env python3
"""
Twitch CSV to DaVinci Resolve Markers (FCP XML - CLI)
Converts Twitch stream markers from CSV format to FCP XML format for DaVinci Resolve

Usage:
    python3 twitch_markers_xml_cli.py input.csv
    
Or run without arguments for interactive mode.
"""

import csv
import sys
from datetime import timedelta
from pathlib import Path


class TwitchToXMLConverter:
    def __init__(self, framerate=25):
        self.framerate = framerate
        
    def parse_timestamp(self, timestamp_str):
        """Parse timestamp from format h:mm:ss or hh:mm:ss"""
        parts = timestamp_str.strip().split(':')
        if len(parts) == 3:
            hours = int(parts[0])
            minutes = int(parts[1])
            seconds = int(parts[2])
            return timedelta(hours=hours, minutes=minutes, seconds=seconds)
        raise ValueError(f"Invalid timestamp format: {timestamp_str}")
    
    def timedelta_to_frames(self, td):
        """Convert timedelta to frame count"""
        total_seconds = td.total_seconds()
        return int(total_seconds * self.framerate)
    
    def convert_csv_to_xml(self, csv_path, xml_path):
        """Convert Twitch CSV markers to FCP XML format"""
        markers = []
        
        # Read CSV file
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            for row in reader:
                if len(row) >= 3 and row[0].strip():
                    timestamp = row[0].strip()
                    role = row[1].strip()
                    username = row[2].strip()
                    # Get description if present (4th column)
                    description = row[3].strip() if len(row) > 3 else ""
                    markers.append({
                        'timestamp': timestamp,
                        'role': role,
                        'username': username,
                        'description': description
                    })
        
        if not markers:
            raise ValueError("No valid markers found in CSV file")
        
        # Calculate duration
        last_marker_td = self.parse_timestamp(markers[-1]['timestamp'])
        duration_frames = self.timedelta_to_frames(last_marker_td) + (self.framerate * 60)
        
        # Build XML manually
        xml_lines = ['<?xml version="1.0" encoding="UTF-8"?>']
        xml_lines.append('<!DOCTYPE xmeml>')
        xml_lines.append('<xmeml version="5">')
        xml_lines.append('  <sequence>')
        xml_lines.append('    <n>Twitch Markers Timeline</n>')
        xml_lines.append(f'    <duration>{duration_frames}</duration>')
        xml_lines.append('    <rate>')
        xml_lines.append(f'      <timebase>{self.framerate}</timebase>')
        xml_lines.append('      <ntsc>FALSE</ntsc>')
        xml_lines.append('    </rate>')
        xml_lines.append('    <timecode>')
        xml_lines.append('      <rate>')
        xml_lines.append(f'        <timebase>{self.framerate}</timebase>')
        xml_lines.append('        <ntsc>FALSE</ntsc>')
        xml_lines.append('      </rate>')
        xml_lines.append('      <string>00:00:00:00</string>')
        xml_lines.append('      <frame>0</frame>')
        xml_lines.append('    </timecode>')
        xml_lines.append('    <media>')
        xml_lines.append('      <video>')
        xml_lines.append('        <format>')
        xml_lines.append('          <samplecharacteristics>')
        xml_lines.append('            <width>1920</width>')
        xml_lines.append('            <height>1080</height>')
        xml_lines.append('          </samplecharacteristics>')
        xml_lines.append('        </format>')
        xml_lines.append('      </video>')
        xml_lines.append('    </media>')
        
        # Add markers
        for marker in markers:
            td = self.parse_timestamp(marker['timestamp'])
            frame_number = self.timedelta_to_frames(td)
            
            # Build marker name with description if present
            if marker['description']:
                marker_name = f"{marker['description']} - by {marker['username']} [{marker['role']}]"
                marker_comment = f"{marker['description']} (Twitch marker by {marker['username']})"
            else:
                marker_name = f"by {marker['username']} [{marker['role']}]"
                marker_comment = f"Twitch marker by {marker['username']}"
            
            xml_lines.append('    <marker>')
            xml_lines.append(f'      <n>{self._escape_xml(marker_name)}</n>')
            xml_lines.append(f'      <comment>{self._escape_xml(marker_comment)}</comment>')
            xml_lines.append(f'      <in>{frame_number}</in>')
            xml_lines.append(f'      <out>{frame_number + 1}</out>')
            xml_lines.append('    </marker>')
        
        xml_lines.append('  </sequence>')
        xml_lines.append('</xmeml>')
        
        # Write to file
        with open(xml_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(xml_lines))
        
        return len(markers)
    
    def _escape_xml(self, text):
        """Escape special XML characters"""
        text = text.replace('&', '&amp;')
        text = text.replace('<', '&lt;')
        text = text.replace('>', '&gt;')
        text = text.replace('"', '&quot;')
        text = text.replace("'", '&apos;')
        return text


def get_framerate():
    """Prompt user for framerate"""
    print()
    print("=" * 60)
    print("⚠️  VIDEO FRAMERATE REQUIRED")
    print("=" * 60)
    print()
    print("Enter your video's framerate (fps):")
    print()
    print("Common options:")
    print("  24     - Film/cinematic")
    print("  25     - PAL standard (Europe)")
    print("  30     - Most common for Twitch streams ⭐")
    print("  60     - High-motion gaming streams")
    print("  23.976 - NTSC film")
    print("  29.97  - NTSC video")
    print("  59.94  - NTSC 60fps")
    print()
    print("💡 Tip: Check your video framerate first:")
    print("   ffmpeg -i your_video.mp4 2>&1 | grep fps")
    print("   OR use: python3 check_video_framerate.py your_video.mp4")
    print()
    
    while True:
        fps_input = input("Enter framerate [default: 30]: ").strip()
        
        if not fps_input:
            return 30.0  # Default to 30 fps (most common for Twitch)
        
        try:
            fps = float(fps_input)
            if fps <= 0 or fps > 120:
                print("❌ Invalid framerate. Please enter a value between 1 and 120.")
                continue
            return fps
        except ValueError:
            print("❌ Invalid input. Please enter a number (e.g., 30 or 29.97)")


def main():
    print("=" * 60)
    print("Twitch CSV to DaVinci Resolve Markers (FCP XML)")
    print("=" * 60)
    print()
    
    # Get CSV file path
    if len(sys.argv) > 1:
        csv_path = sys.argv[1]
    else:
        print("Enter the path to your CSV file (or drag and drop it here):")
        csv_path = input("> ").strip().strip('"').strip("'")
    
    if not csv_path:
        print("Error: No file provided")
        sys.exit(1)
    
    # Validate input file
    csv_file = Path(csv_path)
    if not csv_file.exists():
        print(f"Error: File not found: {csv_path}")
        sys.exit(1)
    
    # Get framerate from user
    framerate = get_framerate()
    
    # Generate output path
    xml_path = csv_file.with_suffix('.xml')
    
    print()
    print("=" * 60)
    print("CONVERSION SETTINGS")
    print("=" * 60)
    print(f"Input:     {csv_file}")
    print(f"Output:    {xml_path}")
    print(f"Framerate: {framerate} fps")
    print("=" * 60)
    print()
    print("Converting...")
    
    try:
        # Convert
        converter = TwitchToXMLConverter(framerate=framerate)
        marker_count = converter.convert_csv_to_xml(csv_file, xml_path)
        
        # Success
        print()
        print("=" * 60)
        print("✓ CONVERSION SUCCESSFUL")
        print("=" * 60)
        print(f"✓ Converted {marker_count} markers")
        print(f"✓ Using framerate: {framerate} fps")
        print(f"✓ XML file saved to: {xml_path}")
        print()
        print("=" * 60)
        print("HOW TO IMPORT INTO DAVINCI RESOLVE:")
        print("=" * 60)
        print("1. Open DaVinci Resolve")
        print("2. Go to: File → Import → Timeline → Import AAF, EDL, XML...")
        print("3. Select the .xml file")
        print("4. You'll get a timeline with MARKERS (no clips!)")
        print("5. Import your video and drag it onto the timeline")
        print()
        print("The markers will show exactly where your Twitch markers were!")
        print("=" * 60)
        print()
        
    except Exception as e:
        print()
        print("=" * 60)
        print("✗ CONVERSION FAILED")
        print("=" * 60)
        print(f"Error: {e}")
        print("=" * 60)
        sys.exit(1)


if __name__ == "__main__":
    main()
