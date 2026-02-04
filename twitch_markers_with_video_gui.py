#!/usr/bin/env python3
"""
Twitch CSV to DaVinci Resolve Markers with Linked Video (FCP XML Format - GUI)
Creates timeline with video clip and markers already positioned
"""

import csv
import os
import subprocess
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox
from datetime import datetime, timedelta
import urllib.parse


class TwitchToXMLWithVideoConverter:
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
    
    def get_video_info(self, video_path):
        """Get video duration, resolution and framerate using ffprobe"""
        try:
            # Get duration
            result = subprocess.run(
                ['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
                 '-of', 'default=noprint_wrappers=1:nokey=1', video_path],
                capture_output=True,
                text=True,
                timeout=10
            )
            duration_seconds = float(result.stdout.strip())
            
            # Get resolution
            result = subprocess.run(
                ['ffprobe', '-v', 'error', '-select_streams', 'v:0',
                 '-show_entries', 'stream=width,height',
                 '-of', 'csv=p=0', video_path],
                capture_output=True,
                text=True,
                timeout=10
            )
            width, height = result.stdout.strip().split(',')
            
            # Get framerate
            result = subprocess.run(
                ['ffprobe', '-v', 'error', '-select_streams', 'v:0',
                 '-show_entries', 'stream=r_frame_rate',
                 '-of', 'default=noprint_wrappers=1:nokey=1', video_path],
                capture_output=True,
                text=True,
                timeout=10
            )
            fps_str = result.stdout.strip()
            if '/' in fps_str:
                num, den = fps_str.split('/')
                fps = float(num) / float(den)
            else:
                fps = float(fps_str)
            
            # Round to common framerates for cleaner output
            if abs(fps - 23.976) < 0.1:
                fps = 24.0
            elif abs(fps - 29.97) < 0.1:
                fps = 30.0
            elif abs(fps - 59.94) < 0.1:
                fps = 60.0
            else:
                fps = round(fps, 2)
            
            return {
                'duration': duration_seconds,
                'width': int(width),
                'height': int(height),
                'fps': fps
            }
        except Exception as e:
            raise Exception(f"Could not get video info. Is ffprobe installed? Error: {str(e)}")
    
    def convert_csv_to_xml_with_video(self, csv_path, video_path, xml_path):
        """Convert Twitch CSV markers to FCP XML with linked video"""
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
        
        # Get video info
        video_info = self.get_video_info(video_path)
        
        # Use video's actual framerate
        self.framerate = video_info['fps']
        
        # Calculate durations
        video_duration_frames = int(video_info['duration'] * self.framerate)
        
        # Create file URL for the video
        video_path_abs = Path(video_path).resolve()
        video_url = f"file://localhost{urllib.parse.quote(str(video_path_abs))}"
        video_filename = video_path_abs.name
        
        # Build XML
        xml_lines = ['<?xml version="1.0" encoding="UTF-8"?>']
        xml_lines.append('<!DOCTYPE xmeml>')
        xml_lines.append('<xmeml version="5">')
        xml_lines.append('  <sequence>')
        xml_lines.append('    <n>Twitch Stream with Markers</n>')
        xml_lines.append(f'    <duration>{video_duration_frames}</duration>')
        xml_lines.append('    <rate>')
        xml_lines.append(f'      <timebase>{int(self.framerate)}</timebase>')
        xml_lines.append('      <ntsc>FALSE</ntsc>')
        xml_lines.append('    </rate>')
        xml_lines.append('    <timecode>')
        xml_lines.append('      <rate>')
        xml_lines.append(f'        <timebase>{int(self.framerate)}</timebase>')
        xml_lines.append('        <ntsc>FALSE</ntsc>')
        xml_lines.append('      </rate>')
        xml_lines.append('      <string>00:00:00:00</string>')
        xml_lines.append('      <frame>0</frame>')
        xml_lines.append('    </timecode>')
        xml_lines.append('    <media>')
        xml_lines.append('      <video>')
        xml_lines.append('        <format>')
        xml_lines.append('          <samplecharacteristics>')
        xml_lines.append(f'            <width>{video_info["width"]}</width>')
        xml_lines.append(f'            <height>{video_info["height"]}</height>')
        xml_lines.append('          </samplecharacteristics>')
        xml_lines.append('        </format>')
        xml_lines.append('        <track>')
        
        # Add video clip to track
        xml_lines.append('          <clipitem id="clipitem-1">')
        xml_lines.append(f'            <name>{self._escape_xml(video_filename)}</name>')
        xml_lines.append(f'            <duration>{video_duration_frames}</duration>')
        xml_lines.append('            <rate>')
        xml_lines.append(f'              <timebase>{int(self.framerate)}</timebase>')
        xml_lines.append('              <ntsc>FALSE</ntsc>')
        xml_lines.append('            </rate>')
        xml_lines.append('            <start>0</start>')
        xml_lines.append(f'            <end>{video_duration_frames}</end>')
        xml_lines.append('            <in>0</in>')
        xml_lines.append(f'            <out>{video_duration_frames}</out>')
        
        # Add file reference
        xml_lines.append('            <file id="file-1">')
        xml_lines.append(f'              <name>{self._escape_xml(video_filename)}</name>')
        xml_lines.append(f'              <pathurl>{self._escape_xml(video_url)}</pathurl>')
        xml_lines.append('              <rate>')
        xml_lines.append(f'                <timebase>{int(self.framerate)}</timebase>')
        xml_lines.append('                <ntsc>FALSE</ntsc>')
        xml_lines.append('              </rate>')
        xml_lines.append(f'              <duration>{video_duration_frames}</duration>')
        xml_lines.append('              <media>')
        xml_lines.append('                <video>')
        xml_lines.append('                  <samplecharacteristics>')
        xml_lines.append(f'                    <width>{video_info["width"]}</width>')
        xml_lines.append(f'                    <height>{video_info["height"]}</height>')
        xml_lines.append('                  </samplecharacteristics>')
        xml_lines.append('                </video>')
        xml_lines.append('              </media>')
        xml_lines.append('            </file>')
        xml_lines.append('          </clipitem>')
        xml_lines.append('        </track>')
        xml_lines.append('      </video>')
        xml_lines.append('    </media>')
        
        # Add markers at SEQUENCE level (this makes them appear in DaVinci Resolve!)
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
        
        return len(markers), video_info
    
    def _escape_xml(self, text):
        """Escape special XML characters"""
        text = text.replace('&', '&amp;')
        text = text.replace('<', '&lt;')
        text = text.replace('>', '&gt;')
        text = text.replace('"', '&quot;')
        text = text.replace("'", '&apos;')
        return text


class RoundedButton(tk.Canvas):
    """Modern button with rounded corners"""
    def __init__(self, parent, text, command, bg='#6366f1', hover_bg='#4f46e5', 
                 fg='white', width=280, height=50, corner_radius=12, **kwargs):
        super().__init__(parent, width=width, height=height, 
                        bg=parent['bg'], highlightthickness=0, **kwargs)
        
        self.command = command
        self.bg_color = bg
        self.hover_color = hover_bg
        self.fg_color = fg
        self.text = text
        self.width = width
        self.height = height
        self.radius = corner_radius
        
        # Create rounded rectangle
        self.rect = self._create_rounded_rect(4, 4, width-4, height-4, corner_radius, fill=bg)
        self.text_id = self.create_text(width//2, height//2, 
                                        text=text, fill=fg, 
                                        font=('SF Pro Display', 14, 'bold') if self._font_exists('SF Pro Display') else ('Arial', 14, 'bold'),
                                        tags='button')
        
        # Bind events
        self.tag_bind(self.rect, '<Enter>', self.on_enter)
        self.tag_bind(self.text_id, '<Enter>', self.on_enter)
        self.tag_bind(self.rect, '<Leave>', self.on_leave)
        self.tag_bind(self.text_id, '<Leave>', self.on_leave)
        self.tag_bind(self.rect, '<Button-1>', self.on_click)
        self.tag_bind(self.text_id, '<Button-1>', self.on_click)
        self.bind('<Enter>', self.on_enter)
        self.bind('<Leave>', self.on_leave)
        self.config(cursor='hand2')
        
    def _font_exists(self, font_name):
        import tkinter.font as tkfont
        return font_name in tkfont.families()
    
    def _create_rounded_rect(self, x1, y1, x2, y2, radius, **kwargs):
        points = [
            x1+radius, y1,
            x2-radius, y1,
            x2, y1,
            x2, y1+radius,
            x2, y2-radius,
            x2, y2,
            x2-radius, y2,
            x1+radius, y2,
            x1, y2,
            x1, y2-radius,
            x1, y1+radius,
            x1, y1
        ]
        return self.create_polygon(points, smooth=True, **kwargs)
    
    def on_enter(self, event):
        self.itemconfig(self.rect, fill=self.hover_color)
        
    def on_leave(self, event):
        self.itemconfig(self.rect, fill=self.bg_color)
        
    def on_click(self, event):
        self.command()


class RoundedCard(tk.Canvas):
    """Rounded corner card container"""
    def __init__(self, parent, width, height, corner_radius=16, bg='#252540', **kwargs):
        super().__init__(parent, width=width, height=height,
                        bg=parent['bg'], highlightthickness=0, **kwargs)
        
        self.bg_color = bg
        self.width = width
        self.height = height
        
        # Create rounded rectangle background
        self._create_rounded_rect(0, 0, width, height, corner_radius, fill=bg, outline='')
        
        # Create frame for content
        self.content_frame = tk.Frame(self, bg=bg)
        self.create_window(width//2, height//2, window=self.content_frame, width=width-40, height=height-40)
        
    def _create_rounded_rect(self, x1, y1, x2, y2, radius, **kwargs):
        points = [
            x1+radius, y1,
            x2-radius, y1,
            x2, y1,
            x2, y1+radius,
            x2, y2-radius,
            x2, y2,
            x2-radius, y2,
            x1+radius, y2,
            x1, y2,
            x1, y2-radius,
            x1, y1+radius,
            x1, y1
        ]
        return self.create_polygon(points, smooth=True, **kwargs)


class ConverterWithVideoGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Twitch to Resolve - With Video Link")
        self.root.geometry("680x680")
        self.root.resizable(False, False)
        
        self.csv_path = None
        self.video_path = None
        
        # Modern color scheme
        self.bg_primary = '#0f0f1e'
        self.bg_card = '#252540'
        self.bg_secondary = '#1a1a2e'
        self.accent_primary = '#6366f1'
        self.accent_hover = '#4f46e5'
        self.accent_green = '#10b981'
        self.text_primary = '#ffffff'
        self.text_secondary = '#a0a0b0'
        self.text_muted = '#6b6b80'
        
        self.root.configure(bg=self.bg_primary)
        self.create_widgets()
        
    def _font_exists(self, font_name):
        import tkinter.font as tkfont
        return font_name in tkfont.families()
        
    def create_widgets(self):
        # Main container
        main_container = tk.Frame(self.root, bg=self.bg_primary)
        main_container.pack(fill='both', expand=True, padx=30, pady=30)
        
        # Header
        tk.Label(
            main_container,
            text="🎬",
            font=('Arial', 52),
            bg=self.bg_primary,
            fg=self.text_primary
        ).pack(pady=(0, 8))
        
        tk.Label(
            main_container,
            text="Twitch to Resolve",
            font=('SF Pro Display', 24, 'bold') if self._font_exists('SF Pro Display') else ('Arial', 24, 'bold'),
            bg=self.bg_primary,
            fg=self.text_primary
        ).pack(pady=(0, 3))
        
        tk.Label(
            main_container,
            text="Timeline with Video & Markers",
            font=('SF Pro Display', 13) if self._font_exists('SF Pro Display') else ('Arial', 13),
            bg=self.bg_primary,
            fg=self.accent_green
        ).pack(pady=(0, 20))
        
        # Card
        card = RoundedCard(main_container, width=620, height=450, corner_radius=20, bg=self.bg_card)
        card.pack()
        
        card_content = card.content_frame
        card_content.configure(bg=self.bg_card)
        
        # Instructions
        tk.Label(
            card_content,
            text="Select Your Files",
            font=('SF Pro Display', 14, 'bold') if self._font_exists('SF Pro Display') else ('Arial', 14, 'bold'),
            bg=self.bg_card,
            fg=self.text_primary
        ).pack(pady=(15, 15))
        
        # CSV File button
        csv_btn_frame = tk.Frame(card_content, bg=self.bg_card)
        csv_btn_frame.pack(pady=(0, 10))
        
        self.csv_btn = RoundedButton(
            csv_btn_frame,
            text="1. Choose CSV Markers File",
            command=self.select_csv,
            bg=self.bg_secondary,
            hover_bg='#2a2a40',
            fg=self.text_primary,
            width=320,
            height=48,
            corner_radius=10
        )
        self.csv_btn.pack()
        
        self.csv_label = tk.Label(
            card_content,
            text="No file selected",
            font=('SF Pro Display', 10) if self._font_exists('SF Pro Display') else ('Arial', 10),
            bg=self.bg_card,
            fg=self.text_muted
        )
        self.csv_label.pack(pady=(5, 15))
        
        # Video File button
        video_btn_frame = tk.Frame(card_content, bg=self.bg_card)
        video_btn_frame.pack(pady=(0, 10))
        
        self.video_btn = RoundedButton(
            video_btn_frame,
            text="2. Choose Video File",
            command=self.select_video,
            bg=self.bg_secondary,
            hover_bg='#2a2a40',
            fg=self.text_primary,
            width=320,
            height=48,
            corner_radius=10
        )
        self.video_btn.pack()
        
        self.video_label = tk.Label(
            card_content,
            text="No file selected",
            font=('SF Pro Display', 10) if self._font_exists('SF Pro Display') else ('Arial', 10),
            bg=self.bg_card,
            fg=self.text_muted
        )
        self.video_label.pack(pady=(5, 20))
        
        # Divider
        tk.Frame(card_content, bg='#3a3a50', height=1).pack(fill='x', pady=15)
        
        # Convert button
        convert_btn = RoundedButton(
            card_content,
            text="3. Create XML with Video",
            command=self.convert,
            bg=self.accent_primary,
            hover_bg=self.accent_hover,
            fg='white',
            width=320,
            height=55,
            corner_radius=12
        )
        convert_btn.pack(pady=(10, 15))
        
        # Footer
        footer_frame = tk.Frame(main_container, bg=self.bg_primary)
        footer_frame.pack(pady=(20, 0))
        
        for text in [
            "✓ Video clip placed on timeline",
            "✓ Markers positioned on clip",
            "✓ Ready to edit immediately"
        ]:
            tk.Label(
                footer_frame,
                text=text,
                font=('SF Pro Display', 10) if self._font_exists('SF Pro Display') else ('Arial', 10),
                bg=self.bg_primary,
                fg=self.text_muted
            ).pack(pady=2)
    
    def select_csv(self):
        csv_path = filedialog.askopenfilename(
            title="Select Twitch CSV Marker File",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )
        
        if csv_path:
            self.csv_path = csv_path
            filename = Path(csv_path).name
            self.csv_label.configure(text=f"✓ {filename}", fg=self.accent_green)
    
    def select_video(self):
        video_path = filedialog.askopenfilename(
            title="Select Video File",
            filetypes=[
                ("Video files", "*.mp4 *.mov *.avi *.mkv *.flv *.webm *.mts *.m2ts"),
                ("All files", "*.*")
            ]
        )
        
        if video_path:
            self.video_path = video_path
            filename = Path(video_path).name
            self.video_label.configure(text=f"✓ {filename}", fg=self.accent_green)
    
    def convert(self):
        if not self.csv_path:
            messagebox.showerror("Missing File", "Please select a CSV markers file first.")
            return
        
        if not self.video_path:
            messagebox.showerror("Missing File", "Please select a video file first.")
            return
        
        try:
            csv_file = Path(self.csv_path)
            xml_path = csv_file.with_suffix('.xml')
            
            converter = TwitchToXMLWithVideoConverter()
            marker_count, video_info = converter.convert_csv_to_xml_with_video(
                self.csv_path, 
                self.video_path, 
                xml_path
            )
            
            messagebox.showinfo(
                "Conversion Successful",
                f"✓ Successfully created timeline!\n\n"
                f"Markers: {marker_count}\n"
                f"Video: {video_info['width']}x{video_info['height']} @ {video_info['fps']:.2f}fps\n"
                f"Duration: {video_info['duration']:.1f}s\n\n"
                f"File saved to:\n{xml_path}\n\n"
                f"Import into DaVinci Resolve:\n"
                f"File → Import → Timeline → Import AAF, EDL, XML...\n\n"
                f"Your video will already be on the timeline with markers!\n"
                f"Ready to edit immediately."
            )
            
        except Exception as e:
            messagebox.showerror("Conversion Error", f"Error:\n\n{str(e)}")


def main():
    root = tk.Tk()
    app = ConverterWithVideoGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
