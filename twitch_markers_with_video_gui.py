#!/usr/bin/env python3
"""
Twitch CSV to DaVinci Resolve XML Converter (With Video + Audio)
Converts Twitch stream markers from CSV format to FCP XML format
and links them to a video file with its embedded audio.

CSV Format: timestamp,role,username,description(optional)
Example: 4:08:26,Broadcaster,StreamerJoe,Epic clutch moment!
"""

import csv
import os
import sys
import json
import subprocess
import html
from pathlib import Path
from datetime import timedelta
import tkinter as tk
from tkinter import filedialog, messagebox


# ─── Framerate Rounding ───────────────────────────────────────────────────────

COMMON_FRAMERATES = {
    23.976: 24, 23.98: 24, 24.0: 24,
    25.0: 25,
    29.97: 30, 30.0: 30,
    50.0: 50,
    59.94: 60, 60.0: 60,
}

def round_framerate(fps):
    """Round detected framerate to nearest common value."""
    fps_rounded = round(fps, 2)
    if fps_rounded in COMMON_FRAMERATES:
        return COMMON_FRAMERATES[fps_rounded]
    # Find closest common framerate
    closest = min(COMMON_FRAMERATES.keys(), key=lambda x: abs(x - fps))
    if abs(closest - fps) < 1.0:
        return COMMON_FRAMERATES[closest]
    return int(round(fps))


# ─── Video Info Detection ─────────────────────────────────────────────────────

def detect_video_info(video_path):
    """Use ffprobe to detect video properties."""
    try:
        cmd = [
            'ffprobe', '-v', 'quiet', '-print_format', 'json',
            '-show_streams', '-show_format', str(video_path)
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode != 0:
            raise RuntimeError(f"ffprobe error: {result.stderr}")
        
        data = json.loads(result.stdout)
        
        video_stream = None
        audio_stream = None
        for stream in data.get('streams', []):
            if stream.get('codec_type') == 'video' and video_stream is None:
                video_stream = stream
            elif stream.get('codec_type') == 'audio' and audio_stream is None:
                audio_stream = stream
        
        if not video_stream:
            raise RuntimeError("No video stream found in file")
        
        # Parse framerate
        r_frame_rate = video_stream.get('r_frame_rate', '30/1')
        if '/' in r_frame_rate:
            num, den = map(int, r_frame_rate.split('/'))
            raw_fps = num / den if den != 0 else 30.0
        else:
            raw_fps = float(r_frame_rate)
        
        fps = round_framerate(raw_fps)
        
        # Parse duration
        duration = float(data.get('format', {}).get('duration', 
                         video_stream.get('duration', '0')))
        
        # Width/height
        width = int(video_stream.get('width', 1920))
        height = int(video_stream.get('height', 1080))
        
        # Audio info
        has_audio = audio_stream is not None
        audio_channels = int(audio_stream.get('channels', 2)) if has_audio else 0
        audio_sample_rate = int(audio_stream.get('sample_rate', 48000)) if has_audio else 48000
        audio_bit_depth = int(audio_stream.get('bits_per_sample', 16)) if has_audio else 16
        if audio_bit_depth == 0:
            audio_bit_depth = 16  # Default for compressed formats like AAC
        
        return {
            'width': width,
            'height': height,
            'fps': fps,
            'duration': duration,
            'has_audio': has_audio,
            'audio_channels': audio_channels,
            'audio_sample_rate': audio_sample_rate,
            'audio_bit_depth': audio_bit_depth,
        }
    except FileNotFoundError:
        raise RuntimeError("ffprobe not found. Please install FFmpeg.")
    except Exception as e:
        raise RuntimeError(f"Failed to detect video info: {e}")


# ─── Converter ────────────────────────────────────────────────────────────────

class TwitchMarkersWithVideoConverter:
    def __init__(self):
        self.framerate = 30
    
    def _escape_xml(self, text):
        """Escape special XML characters."""
        return html.escape(str(text), quote=True)
    
    def _get_marker_color(self, marker_type):
        """Get color code for marker type (markers=Blue, clips=Orange)."""
        # FCP XML color names: Red, Green, Blue, Yellow, Cyan, Magenta, etc.
        if marker_type == "clip":
            return "Orange"
        return "Blue"  # Default for regular markers
    
    def parse_timestamp(self, timestamp_str):
        """Parse timestamp from format h:mm:ss or hh:mm:ss."""
        parts = timestamp_str.strip().split(':')
        if len(parts) == 3:
            hours = int(parts[0])
            minutes = int(parts[1])
            seconds = int(parts[2])
            return timedelta(hours=hours, minutes=minutes, seconds=seconds)
        raise ValueError(f"Invalid timestamp format: {timestamp_str}")
    
    def timedelta_to_frames(self, td):
        """Convert timedelta to frame count."""
        return int(td.total_seconds() * self.framerate)
    
    def read_markers(self, csv_path, marker_type="marker"):
        """Read markers from CSV file. marker_type can be 'marker' or 'clip'."""
        markers = []
        with open(csv_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.reader(f)
            for row in reader:
                if len(row) >= 3 and row[0].strip():
                    try:
                        td = self.parse_timestamp(row[0].strip())
                        marker = {
                            'timestamp': row[0].strip(),
                            'timedelta': td,
                            'role': row[1].strip(),
                            'username': row[2].strip(),
                            'description': row[3].strip() if len(row) > 3 else '',
                            'type': marker_type,
                        }
                        markers.append(marker)
                    except (ValueError, IndexError):
                        continue
        return markers
    
    def read_markers_and_clips(self, markers_csv_path, clips_csv_path=None):
        """Read and merge markers and clips from CSV files."""
        all_markers = []
        
        # Read markers
        if markers_csv_path:
            all_markers.extend(self.read_markers(markers_csv_path, marker_type="marker"))
        
        # Read clips
        if clips_csv_path:
            all_markers.extend(self.read_markers(clips_csv_path, marker_type="clip"))
        
        # Sort by timestamp
        all_markers.sort(key=lambda m: m['timedelta'])
        
        return all_markers
    
    def video_path_to_url(self, video_path):
        """Convert file path to file://localhost/ URL (FCP7 XML standard)."""
        from urllib.parse import quote
        abs_path = os.path.abspath(video_path)
        # URL-encode path but keep forward slashes and common safe chars
        encoded_path = quote(abs_path, safe="/")
        return "file://localhost" + encoded_path
    
    def generate_xml(self, csv_path, video_path, output_path, clips_csv_path=None):
        """Generate FCP7 XML (xmeml) with video, audio, markers and clips."""
        # Detect video properties
        video_info = detect_video_info(video_path)
        self.framerate = video_info['fps']
        
        # Read markers and clips
        markers = self.read_markers_and_clips(csv_path, clips_csv_path)
        if not markers:
            raise ValueError("No valid markers/clips found in CSV files")
        
        video_filename = os.path.basename(video_path)
        video_url = self.video_path_to_url(video_path)
        video_duration_frames = int(video_info['duration'] * self.framerate)
        
        has_audio = video_info['has_audio']
        audio_channels = video_info['audio_channels'] if has_audio else 2
        audio_sample_rate = video_info['audio_sample_rate']
        audio_bit_depth = video_info['audio_bit_depth']
        
        timeline_name = Path(csv_path).stem + "_with_video"
        tb = int(self.framerate)
        esc = self._escape_xml
        
        L = []
        a = L.append
        
        a('<?xml version="1.0" encoding="UTF-8"?>')
        a('<!DOCTYPE xmeml>')
        a('<xmeml version="4">')
        a('  <sequence>')
        a('    <name>' + esc(timeline_name) + '</name>')
        a('    <duration>' + str(video_duration_frames) + '</duration>')
        a('    <rate>')
        a('      <timebase>' + str(tb) + '</timebase>')
        a('      <ntsc>FALSE</ntsc>')
        a('    </rate>')
        a('    <timecode>')
        a('      <rate>')
        a('        <timebase>' + str(tb) + '</timebase>')
        a('        <ntsc>FALSE</ntsc>')
        a('      </rate>')
        a('      <string>00:00:00:00</string>')
        a('      <frame>0</frame>')
        a('      <displayformat>NDF</displayformat>')
        a('    </timecode>')
        
        # Sequence-level markers
        for marker in markers:
            frame_pos = self.timedelta_to_frames(marker['timedelta'])
            marker_type_label = "[CLIP]" if marker['type'] == 'clip' else ""
            if marker['description']:
                mname = marker['description'] + " - by " + marker['username'] + " [" + marker['role'] + "]" + (" " + marker_type_label if marker_type_label else "")
                mcomment = marker['description'] + " (Twitch marker by " + marker['username'] + ")"
            else:
                mname = "by " + marker['username'] + " [" + marker['role'] + "]" + (" " + marker_type_label if marker_type_label else "")
                mcomment = "Twitch marker by " + marker['username']
            color = self._get_marker_color(marker['type'])
            a('    <marker>')
            a('      <name>' + esc(mname) + '</name>')
            a('      <comment>' + esc(mcomment) + '</comment>')
            a('      <in>' + str(frame_pos) + '</in>')
            a('      <out>' + str(frame_pos + 1) + '</out>')
            a('      <color>' + color + '</color>')
            a('    </marker>')
        
        # Media section
        a('    <media>')
        
        # VIDEO TRACK
        a('      <video>')
        a('        <format>')
        a('          <samplecharacteristics>')
        a('            <rate>')
        a('              <timebase>' + str(tb) + '</timebase>')
        a('              <ntsc>FALSE</ntsc>')
        a('            </rate>')
        a('            <width>' + str(video_info["width"]) + '</width>')
        a('            <height>' + str(video_info["height"]) + '</height>')
        a('            <anamorphic>FALSE</anamorphic>')
        a('            <pixelaspectratio>square</pixelaspectratio>')
        a('            <fielddominance>none</fielddominance>')
        a('          </samplecharacteristics>')
        a('        </format>')
        a('        <track>')
        
        # Video clipitem
        a('          <clipitem id="clipitem-1" frameBlend="FALSE">')
        a('            <name>' + esc(video_filename) + '</name>')
        a('            <duration>' + str(video_duration_frames) + '</duration>')
        a('            <rate>')
        a('              <timebase>' + str(tb) + '</timebase>')
        a('              <ntsc>FALSE</ntsc>')
        a('            </rate>')
        a('            <start>0</start>')
        a('            <end>' + str(video_duration_frames) + '</end>')
        a('            <in>0</in>')
        a('            <out>' + str(video_duration_frames) + '</out>')
        
        # File reference
        a('            <file id="file-1">')
        a('              <name>' + esc(video_filename) + '</name>')
        a('              <pathurl>' + esc(video_url) + '</pathurl>')
        a('              <rate>')
        a('                <timebase>' + str(tb) + '</timebase>')
        a('                <ntsc>FALSE</ntsc>')
        a('              </rate>')
        a('              <duration>' + str(video_duration_frames) + '</duration>')
        a('              <timecode>')
        a('                <rate>')
        a('                  <timebase>' + str(tb) + '</timebase>')
        a('                  <ntsc>FALSE</ntsc>')
        a('                </rate>')
        a('                <string>00:00:00:00</string>')
        a('                <frame>0</frame>')
        a('                <displayformat>NDF</displayformat>')
        a('              </timecode>')
        a('              <media>')
        a('                <video>')
        a('                  <samplecharacteristics>')
        a('                    <rate>')
        a('                      <timebase>' + str(tb) + '</timebase>')
        a('                      <ntsc>FALSE</ntsc>')
        a('                    </rate>')
        a('                    <width>' + str(video_info["width"]) + '</width>')
        a('                    <height>' + str(video_info["height"]) + '</height>')
        a('                    <anamorphic>FALSE</anamorphic>')
        a('                    <pixelaspectratio>square</pixelaspectratio>')
        a('                    <fielddominance>none</fielddominance>')
        a('                  </samplecharacteristics>')
        a('                </video>')
        if has_audio:
            a('                <audio>')
            a('                  <samplecharacteristics>')
            a('                    <depth>' + str(audio_bit_depth) + '</depth>')
            a('                    <samplerate>' + str(audio_sample_rate) + '</samplerate>')
            a('                  </samplecharacteristics>')
            a('                  <channelcount>' + str(audio_channels) + '</channelcount>')
            a('                  <layout>stereo</layout>')
            a('                </audio>')
        a('              </media>')
        a('            </file>')
        
        # Source track
        a('            <sourcetrack>')
        a('              <mediatype>video</mediatype>')
        a('              <trackindex>1</trackindex>')
        a('            </sourcetrack>')
        
        # Links
        if has_audio:
            a('            <link>')
            a('              <linkclipref>clipitem-1</linkclipref>')
            a('              <mediatype>video</mediatype>')
            a('              <trackindex>1</trackindex>')
            a('              <clipindex>1</clipindex>')
            a('            </link>')
            a('            <link>')
            a('              <linkclipref>clipitem-2</linkclipref>')
            a('              <mediatype>audio</mediatype>')
            a('              <trackindex>1</trackindex>')
            a('              <clipindex>1</clipindex>')
            a('            </link>')
        
        a('          </clipitem>')
        a('        </track>')
        a('      </video>')
        
        # AUDIO (single stereo track, same file)
        if has_audio:
            a('      <audio>')
            a('        <numOutputChannels>2</numOutputChannels>')
            a('        <format>')
            a('          <samplecharacteristics>')
            a('            <depth>' + str(audio_bit_depth) + '</depth>')
            a('            <samplerate>' + str(audio_sample_rate) + '</samplerate>')
            a('          </samplecharacteristics>')
            a('        </format>')
            a('        <track>')
            a('          <clipitem id="clipitem-2" frameBlend="FALSE">')
            a('            <name>' + esc(video_filename) + '</name>')
            a('            <duration>' + str(video_duration_frames) + '</duration>')
            a('            <rate>')
            a('              <timebase>' + str(tb) + '</timebase>')
            a('              <ntsc>FALSE</ntsc>')
            a('            </rate>')
            a('            <start>0</start>')
            a('            <end>' + str(video_duration_frames) + '</end>')
            a('            <in>0</in>')
            a('            <out>' + str(video_duration_frames) + '</out>')
            a('            <file id="file-1"/>')
            a('            <sourcetrack>')
            a('              <mediatype>audio</mediatype>')
            a('              <trackindex>1</trackindex>')
            a('            </sourcetrack>')
            a('            <link>')
            a('              <linkclipref>clipitem-1</linkclipref>')
            a('              <mediatype>video</mediatype>')
            a('              <trackindex>1</trackindex>')
            a('              <clipindex>1</clipindex>')
            a('            </link>')
            a('            <link>')
            a('              <linkclipref>clipitem-2</linkclipref>')
            a('              <mediatype>audio</mediatype>')
            a('              <trackindex>1</trackindex>')
            a('              <clipindex>1</clipindex>')
            a('            </link>')
            a('          </clipitem>')
            a('        </track>')
            a('      </audio>')
        
        a('    </media>')
        a('  </sequence>')
        a('</xmeml>')
        
        # Write XML
        xml_content = "\n".join(L)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(xml_content)
        
        return len(markers), video_info

        return len(markers), video_info


# ─── Modern GUI Components ────────────────────────────────────────────────────

class StyledButton(tk.Button):
    """A styled button compatible with all platforms."""
    def __init__(self, parent, text, command=None, bg_color="#4A90D9",
                 fg_color="#333333", hover_color="#3A7BC8",
                 font=("Segoe UI", 11, "bold"), **kwargs):
        # Remove unsupported kwargs
        kwargs.pop('width', None)
        kwargs.pop('height', None)
        kwargs.pop('corner_radius', None)
        super().__init__(parent, text=text, command=command,
                        font=font, bg=bg_color, fg=fg_color,
                        activebackground=hover_color, activeforeground=fg_color,
                        relief='flat', cursor='hand2', padx=12, pady=4, **kwargs)
        self.bg_color = bg_color
        self.hover_color = hover_color
        self.bind("<Enter>", lambda e: self.config(bg=self.hover_color))
        self.bind("<Leave>", lambda e: self.config(bg=self.bg_color))
    
    def set_enabled(self, enabled):
        if enabled:
            self.config(state='normal', bg=self.bg_color)
        else:
            self.config(state='disabled', bg="#888888")


class RoundedCard(tk.Frame):
    """A frame styled as a card with rounded appearance."""
    def __init__(self, parent, bg="#2D2D2D", **kwargs):
        super().__init__(parent, bg=bg, padx=15, pady=12, **kwargs)


# ─── Main GUI ─────────────────────────────────────────────────────────────────

class TwitchMarkersWithVideoGUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Twitch Markers → DaVinci Resolve (With Video)")
        self.root.geometry("600x680")
        self.root.configure(bg="#1E1E1E")
        self.root.resizable(False, False)
        
        self.markers_csv_path = None
        self.clips_csv_path = None
        self.video_path = None
        self.converter = TwitchMarkersWithVideoConverter()
        
        self._build_ui()
    
    def _build_ui(self):
        bg = "#1E1E1E"
        fg = "#E0E0E0"
        accent = "#4A90D9"
        
        # Title
        title_frame = tk.Frame(self.root, bg=bg)
        title_frame.pack(pady=(20, 5))
        tk.Label(title_frame, text="🎬 Twitch Markers → DaVinci Resolve",
                font=("Segoe UI", 16, "bold"), bg=bg, fg=fg).pack()
        tk.Label(title_frame, text="With Video + Audio Import",
                font=("Segoe UI", 10), bg=bg, fg="#888888").pack()
        
        # CSV file card
        csv_card = RoundedCard(self.root, bg="#2D2D2D")
        csv_card.pack(fill='x', padx=25, pady=(15, 5))
        
        tk.Label(csv_card, text="📋 Markers CSV File", font=("Segoe UI", 11, "bold"),
                bg="#2D2D2D", fg=fg).pack(anchor='w')
        
        csv_row = tk.Frame(csv_card, bg="#2D2D2D")
        csv_row.pack(fill='x', pady=(5, 0))
        
        self.markers_label = tk.Label(csv_row, text="No file selected",
                                 font=("Segoe UI", 9), bg="#2D2D2D", fg="#888888",
                                 anchor='w')
        self.markers_label.pack(side='left', fill='x', expand=True)
        
        StyledButton(csv_row, "Browse", command=self._choose_markers_csv,
                      width=90, height=30, corner_radius=8,
                      font=("Segoe UI", 9, "bold")).pack(side='right')
        
        # Clips CSV file card
        clips_card = RoundedCard(self.root, bg="#2D2D2D")
        clips_card.pack(fill='x', padx=25, pady=5)
        
        tk.Label(clips_card, text="🎬 Clips CSV File (Optional)", font=("Segoe UI", 11, "bold"),
                bg="#2D2D2D", fg=fg).pack(anchor='w')
        
        clips_row = tk.Frame(clips_card, bg="#2D2D2D")
        clips_row.pack(fill='x', pady=(5, 0))
        
        self.clips_label = tk.Label(clips_row, text="No file selected",
                                   font=("Segoe UI", 9), bg="#2D2D2D", fg="#888888",
                                   anchor='w')
        self.clips_label.pack(side='left', fill='x', expand=True)
        
        StyledButton(clips_row, "Browse", command=self._choose_clips_csv,
                      width=90, height=30, corner_radius=8,
                      font=("Segoe UI", 9, "bold")).pack(side='right')
        
        # Video file card
        video_card = RoundedCard(self.root, bg="#2D2D2D")
        video_card.pack(fill='x', padx=25, pady=5)
        
        tk.Label(video_card, text="🎥 Video File", font=("Segoe UI", 11, "bold"),
                bg="#2D2D2D", fg=fg).pack(anchor='w')
        
        video_row = tk.Frame(video_card, bg="#2D2D2D")
        video_row.pack(fill='x', pady=(5, 0))
        
        self.video_label = tk.Label(video_row, text="No file selected",
                                   font=("Segoe UI", 9), bg="#2D2D2D", fg="#888888",
                                   anchor='w')
        self.video_label.pack(side='left', fill='x', expand=True)
        
        StyledButton(video_row, "Browse", command=self._choose_video,
                      width=90, height=30, corner_radius=8,
                      font=("Segoe UI", 9, "bold")).pack(side='right')
        
        # Info card (shows detected properties)
        self.info_card = RoundedCard(self.root, bg="#2D2D2D")
        self.info_card.pack(fill='x', padx=25, pady=5)
        
        tk.Label(self.info_card, text="ℹ️ Video Properties", 
                font=("Segoe UI", 11, "bold"), bg="#2D2D2D", fg=fg).pack(anchor='w')
        
        self.info_label = tk.Label(self.info_card, text="Select a video file to detect properties",
                                  font=("Segoe UI", 9), bg="#2D2D2D", fg="#888888",
                                  anchor='w', justify='left')
        self.info_label.pack(anchor='w', pady=(5, 0))
        
        # Convert button
        btn_frame = tk.Frame(self.root, bg=bg)
        btn_frame.pack(pady=15)
        
        self.convert_btn = StyledButton(
            btn_frame, "🚀 Create XML with Video + Audio",
            command=self._convert,
            bg_color="#2ECC71", hover_color="#27AE60",
            width=300, height=45, corner_radius=12,
            font=("Segoe UI", 12, "bold")
        )
        self.convert_btn.pack()
        
        # Status
        self.status_label = tk.Label(self.root, text="", font=("Segoe UI", 9),
                                    bg=bg, fg="#888888", wraplength=550)
        self.status_label.pack(pady=(5, 0))
        
        # Help text
        help_card = RoundedCard(self.root, bg="#2D2D2D")
        help_card.pack(fill='x', padx=25, pady=(10, 15))
        
        help_text = (
            "CSV format: timestamp,role,username,description(optional)\n"
            "Example: 4:08:26,Broadcaster,StreamerJoe,Epic moment!\n\n"
            "Markers will appear as BLUE, Clips as ORANGE on the timeline.\n"
            "The XML will contain your video with its audio and all markers/clips."
        )
        tk.Label(help_card, text=help_text, font=("Segoe UI", 8),
                bg="#2D2D2D", fg="#666666", justify='left').pack(anchor='w')
    
    def _choose_markers_csv(self):
        path = filedialog.askopenfilename(
            title="Choose Twitch Markers CSV",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )
        if path:
            self.markers_csv_path = path
            self.markers_label.config(text=os.path.basename(path), fg="#E0E0E0")
            self.status_label.config(text="")
    
    def _choose_clips_csv(self):
        path = filedialog.askopenfilename(
            title="Choose Twitch Clips CSV (Optional)",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )
        if path:
            self.clips_csv_path = path
            self.clips_label.config(text=os.path.basename(path), fg="#E0E0E0")
            self.status_label.config(text="")
    
    def _choose_video(self):
        path = filedialog.askopenfilename(
            title="Choose Video File",
            filetypes=[
                ("Video files", "*.mp4 *.mkv *.mov *.avi *.webm *.ts *.flv *.m4v"),
                ("All files", "*.*")
            ]
        )
        if path:
            self.video_path = path
            self.video_label.config(text=os.path.basename(path), fg="#E0E0E0")
            self.status_label.config(text="Detecting video properties...")
            self.root.update()
            
            try:
                info = detect_video_info(path)
                audio_str = "Yes" if info['has_audio'] else "No"
                if info['has_audio']:
                    audio_str += f" ({info['audio_channels']}ch, {info['audio_sample_rate']}Hz, {info['audio_bit_depth']}bit)"
                
                info_text = (
                    f"Resolution: {info['width']}x{info['height']}  |  "
                    f"FPS: {info['fps']}  |  "
                    f"Duration: {timedelta(seconds=int(info['duration']))}\n"
                    f"Audio: {audio_str}"
                )
                self.info_label.config(text=info_text, fg="#E0E0E0")
                self.status_label.config(text="✅ Video detected successfully", fg="#2ECC71")
            except Exception as e:
                self.info_label.config(text=f"Error: {e}", fg="#E74C3C")
                self.status_label.config(text="", fg="#888888")
    
    def _convert(self):
        if not self.markers_csv_path:
            messagebox.showwarning("Missing File", "Please select a Markers CSV file.")
            return
        if not self.video_path:
            messagebox.showwarning("Missing File", "Please select a video file.")
            return
        
        # Generate output path next to markers CSV
        csv_dir = os.path.dirname(self.markers_csv_path)
        csv_stem = Path(self.markers_csv_path).stem
        if csv_stem.lower() == "markers":
            # If markers.csv, replace with combined name
            output_stem = "markers_and_clips" if self.clips_csv_path else "markers"
        else:
            output_stem = csv_stem + ("_and_clips" if self.clips_csv_path else "")
        output_path = os.path.join(csv_dir, f"{output_stem}_with_video.xml")
        
        self.status_label.config(text="Generating XML...", fg="#F39C12")
        self.root.update()
        
        try:
            num_markers, video_info = self.converter.generate_xml(
                self.markers_csv_path, self.video_path, output_path,
                clips_csv_path=self.clips_csv_path
            )
            
            audio_status = "with audio" if video_info['has_audio'] else "without audio"
            self.status_label.config(
                text=f"✅ Done! {num_markers} items + video ({audio_status}) → {os.path.basename(output_path)}",
                fg="#2ECC71"
            )
            
            clip_info = f"Clips: {len([m for m in self.converter.read_markers_and_clips(self.markers_csv_path, self.clips_csv_path) if m['type'] == 'clip'])}\n" if self.clips_csv_path else ""
            marker_info = f"Markers: {len([m for m in self.converter.read_markers_and_clips(self.markers_csv_path, self.clips_csv_path) if m['type'] == 'marker'])}\n" if self.markers_csv_path else ""
            
            messagebox.showinfo(
                "Success!",
                f"XML created successfully!\n\n"
                f"📄 {output_path}\n\n"
                f"{marker_info}{clip_info}"
                f"Total: {num_markers} items\n"
                f"Video: {video_info['width']}x{video_info['height']} @ {video_info['fps']}fps\n"
                f"Audio: {'Yes (' + str(video_info['audio_channels']) + ' channels)' if video_info['has_audio'] else 'No audio detected'}\n\n"
                f"Colors: 🔵 BLUE = Markers | 🟠 ORANGE = Clips\n\n"
                f"Import in DaVinci Resolve:\n"
                f"File → Import → Timeline → Import AAF, EDL, XML...\n\n"
                f"The video with its audio and all markers/clips will be on the timeline!"
            )
        except Exception as e:
            self.status_label.config(text=f"❌ Error: {e}", fg="#E74C3C")
            messagebox.showerror("Error", str(e))
    
    def run(self):
        self.root.mainloop()


# ─── CLI mode ─────────────────────────────────────────────────────────────────

def cli_mode():
    if len(sys.argv) < 3:
        print("Usage: python3 twitch_markers_with_video_gui.py <markers.csv> <video_file> [clips.csv] [output.xml]")
        print("       python3 twitch_markers_with_video_gui.py   (launches GUI)")
        print("\nExample:")
        print("  python3 twitch_markers_with_video_gui.py markers.csv video.mp4")
        print("  python3 twitch_markers_with_video_gui.py markers.csv video.mp4 clips.csv")
        sys.exit(1)
    
    markers_csv_path = sys.argv[1]
    video_path = sys.argv[2]
    clips_csv_path = sys.argv[3] if len(sys.argv) > 3 and sys.argv[3].endswith('.csv') else None
    
    # Find output path
    output_path = None
    for i in range(3, len(sys.argv)):
        if not sys.argv[i].endswith('.csv'):
            output_path = sys.argv[i]
            break
    
    if not os.path.exists(markers_csv_path):
        print(f"Error: Markers CSV file not found: {markers_csv_path}")
        sys.exit(1)
    if not os.path.exists(video_path):
        print(f"Error: Video file not found: {video_path}")
        sys.exit(1)
    if clips_csv_path and not os.path.exists(clips_csv_path):
        print(f"Error: Clips CSV file not found: {clips_csv_path}")
        sys.exit(1)
    
    if not output_path:
        if clips_csv_path:
            output_path = str(Path(markers_csv_path).with_stem(Path(markers_csv_path).stem + "_and_clips")) + "_with_video.xml"
        else:
            output_path = str(Path(markers_csv_path).with_suffix('')) + "_with_video.xml"
    
    converter = TwitchMarkersWithVideoConverter()
    num_markers, video_info = converter.generate_xml(markers_csv_path, video_path, output_path, clips_csv_path=clips_csv_path)
    
    # Count markers and clips
    all_items = converter.read_markers_and_clips(markers_csv_path, clips_csv_path)
    markers_count = len([m for m in all_items if m['type'] == 'marker'])
    clips_count = len([m for m in all_items if m['type'] == 'clip'])
    
    print(f"✅ Created {output_path}")
    print(f"   Markers: {markers_count} (BLUE)")
    print(f"   Clips: {clips_count} (ORANGE)")
    print(f"   Video: {video_info['width']}x{video_info['height']} @ {video_info['fps']}fps")
    print(f"   Audio: {'Yes (' + str(video_info['audio_channels']) + 'ch)' if video_info['has_audio'] else 'No'}")
    print(f"\nImport in DaVinci Resolve: File → Import → Timeline → Import AAF, EDL, XML...")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        cli_mode()
    else:
        app = TwitchMarkersWithVideoGUI()
        app.run()
