#!/usr/bin/env python3
"""
Twitch CSV to DaVinci Resolve Markers (FCP XML Format - GUI)
Converts Twitch stream markers from CSV format to FCP XML format for DaVinci Resolve
"""

import csv
import os
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox
from datetime import datetime, timedelta


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
                    markers.append({
                        'timestamp': timestamp,
                        'role': role,
                        'username': username
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
            marker_name = f"by {marker['username']} [{marker['role']}]"
            
            xml_lines.append('    <marker>')
            xml_lines.append(f'      <n>{self._escape_xml(marker_name)}</n>')
            xml_lines.append(f'      <comment>Twitch marker by {self._escape_xml(marker["username"])}</comment>')
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
        """Check if a font exists"""
        import tkinter.font as tkfont
        return font_name in tkfont.families()
    
    def _create_rounded_rect(self, x1, y1, x2, y2, radius, **kwargs):
        """Create a rounded rectangle"""
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


class ModernDropdown(tk.Canvas):
    """Custom dropdown with rounded corners"""
    def __init__(self, parent, options, default, callback, width=200, height=40, **kwargs):
        super().__init__(parent, width=width, height=height,
                        bg=parent['bg'], highlightthickness=0, **kwargs)
        
        self.options = options
        self.current = default
        self.callback = callback
        self.width = width
        self.height = height
        self.is_open = False
        
        self.bg_color = '#1a1a2e'
        self.hover_color = '#252540'
        self.text_color = '#ffffff'
        
        # Create main dropdown button
        self.rect = self._create_rounded_rect(0, 0, width, height, 10, 
                                               fill=self.bg_color, outline='')
        self.text_id = self.create_text(20, height//2, 
                                        text=default, 
                                        fill=self.text_color,
                                        font=('SF Pro Display', 12) if self._font_exists('SF Pro Display') else ('Arial', 12),
                                        anchor='w')
        
        # Arrow
        arrow_x = width - 20
        arrow_y = height // 2
        self.arrow = self.create_polygon(
            arrow_x-4, arrow_y-3,
            arrow_x+4, arrow_y-3,
            arrow_x, arrow_y+3,
            fill=self.text_color,
            tags='arrow'
        )
        
        # Bind events
        self.tag_bind(self.rect, '<Button-1>', self.toggle_menu)
        self.tag_bind(self.text_id, '<Button-1>', self.toggle_menu)
        self.tag_bind(self.arrow, '<Button-1>', self.toggle_menu)
        self.tag_bind(self.rect, '<Enter>', lambda e: self.itemconfig(self.rect, fill=self.hover_color))
        self.tag_bind(self.rect, '<Leave>', lambda e: self.itemconfig(self.rect, fill=self.bg_color) if not self.is_open else None)
        self.config(cursor='hand2')
        
        self.menu_window = None
        
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
    
    def toggle_menu(self, event=None):
        if self.is_open:
            self.close_menu()
        else:
            self.open_menu()
    
    def open_menu(self):
        if self.menu_window:
            return
            
        self.is_open = True
        self.itemconfig(self.rect, fill=self.hover_color)
        
        # Create menu window
        self.menu_window = tk.Toplevel(self)
        self.menu_window.withdraw()
        self.menu_window.overrideredirect(True)
        
        # Position below dropdown
        x = self.winfo_rootx()
        y = self.winfo_rooty() + self.height + 5
        
        # Create menu frame with rounded appearance
        menu_canvas = tk.Canvas(self.menu_window, width=self.width, height=len(self.options)*36,
                               bg=self.bg_color, highlightthickness=0)
        menu_canvas.pack()
        
        # Draw rounded background
        menu_canvas.create_polygon(
            self._get_rounded_points(0, 0, self.width, len(self.options)*36, 10),
            fill=self.bg_color, outline='#3a3a50', smooth=True
        )
        
        # Add options
        for i, option in enumerate(self.options):
            y_pos = i * 36
            
            btn_frame = tk.Frame(menu_canvas, bg=self.bg_color)
            btn_window = menu_canvas.create_window(0, y_pos, window=btn_frame, anchor='nw', 
                                                   width=self.width, height=36)
            
            btn = tk.Label(
                btn_frame,
                text=option,
                bg=self.bg_color,
                fg=self.text_color,
                font=('SF Pro Display', 11) if self._font_exists('SF Pro Display') else ('Arial', 11),
                cursor='hand2',
                padx=15,
                pady=8,
                anchor='w'
            )
            btn.pack(fill='both', expand=True)
            
            def on_enter(e, b=btn):
                b.configure(bg=self.hover_color)
            
            def on_leave(e, b=btn):
                b.configure(bg=self.bg_color)
            
            def on_click(e, opt=option):
                self.select_option(opt)
            
            btn.bind('<Enter>', on_enter)
            btn.bind('<Leave>', on_leave)
            btn.bind('<Button-1>', on_click)
        
        self.menu_window.geometry(f"{self.width}x{len(self.options)*36}+{x}+{y}")
        self.menu_window.deiconify()
        
        # Close menu when clicking outside
        self.menu_window.bind('<FocusOut>', lambda e: self.close_menu())
        self.menu_window.focus_set()
    
    def _get_rounded_points(self, x1, y1, x2, y2, radius):
        return [
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
    
    def close_menu(self):
        if self.menu_window:
            self.menu_window.destroy()
            self.menu_window = None
        self.is_open = False
        self.itemconfig(self.rect, fill=self.bg_color)
    
    def select_option(self, option):
        self.current = option
        self.itemconfig(self.text_id, text=option)
        self.callback(option)
        self.close_menu()
    
    def get(self):
        return self.current


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


class ConverterGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Twitch to DaVinci Resolve")
        self.root.geometry("680x720")
        self.root.resizable(False, False)
        
        self.framerate = 30
        
        # Modern color scheme
        self.bg_primary = '#0f0f1e'
        self.bg_card = '#252540'
        self.bg_secondary = '#1a1a2e'
        self.accent_primary = '#6366f1'
        self.accent_hover = '#4f46e5'
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
            font=('Arial', 56),
            bg=self.bg_primary,
            fg=self.text_primary
        ).pack(pady=(0, 10))
        
        tk.Label(
            main_container,
            text="Twitch to DaVinci Resolve",
            font=('SF Pro Display', 26, 'bold') if self._font_exists('SF Pro Display') else ('Arial', 26, 'bold'),
            bg=self.bg_primary,
            fg=self.text_primary
        ).pack(pady=(0, 5))
        
        tk.Label(
            main_container,
            text="Convert stream markers to timeline markers",
            font=('SF Pro Display', 13) if self._font_exists('SF Pro Display') else ('Arial', 13),
            bg=self.bg_primary,
            fg=self.text_secondary
        ).pack(pady=(0, 25))
        
        # Card
        card = RoundedCard(main_container, width=620, height=420, corner_radius=20, bg=self.bg_card)
        card.pack()
        
        card_content = card.content_frame
        card_content.configure(bg=self.bg_card)
        
        # Framerate section
        tk.Label(
            card_content,
            text="Video Framerate",
            font=('SF Pro Display', 13, 'bold') if self._font_exists('SF Pro Display') else ('Arial', 13, 'bold'),
            bg=self.bg_card,
            fg=self.text_primary,
            anchor='w'
        ).pack(fill='x', pady=(15, 10))
        
        # Dropdown
        fps_frame = tk.Frame(card_content, bg=self.bg_card)
        fps_frame.pack(fill='x', pady=(0, 8))
        
        self.fps_dropdown = ModernDropdown(
            fps_frame,
            options=['23.976', '24', '25', '29.97', '30', '50', '59.94', '60'],
            default='30',
            callback=self.on_fps_change,
            width=150,
            height=42
        )
        self.fps_dropdown.pack(side='left')
        
        tk.Label(
            fps_frame,
            text="fps",
            font=('SF Pro Display', 12) if self._font_exists('SF Pro Display') else ('Arial', 12),
            bg=self.bg_card,
            fg=self.text_secondary
        ).pack(side='left', padx=(10, 0))
        
        
        # Divider
        tk.Frame(card_content, bg='#3a3a50', height=1).pack(fill='x', pady=15)
        
        # Auto-detect button
        detect_btn = RoundedButton(
            card_content,
            text="📊  Auto-Detect Framerate",
            command=self.check_video_framerate,
            bg=self.bg_secondary,
            hover_bg='#2a2a40',
            fg=self.accent_primary,
            width=260,
            height=42,
            corner_radius=10
        )
        detect_btn.pack(pady=(0, 20))
        
        # Main convert button
        convert_btn = RoundedButton(
            card_content,
            text="Choose CSV & Convert",
            command=self.select_and_convert,
            bg=self.accent_primary,
            hover_bg=self.accent_hover,
            fg='white',
            width=300,
            height=55,
            corner_radius=12
        )
        convert_btn.pack(pady=(5, 15))
        
        # Footer
        footer_frame = tk.Frame(main_container, bg=self.bg_primary)
        footer_frame.pack(pady=(20, 0))
        
        for text in [
            "✓ Creates actual timeline markers",
            "✓ No clips or cleanup needed",
            "✓ Perfect for DaVinci Resolve"
        ]:
            tk.Label(
                footer_frame,
                text=text,
                font=('SF Pro Display', 10) if self._font_exists('SF Pro Display') else ('Arial', 10),
                bg=self.bg_primary,
                fg=self.text_muted
            ).pack(pady=2)
    
    def on_fps_change(self, value):
        self.framerate = float(value)
    
    def check_video_framerate(self):
        video_path = filedialog.askopenfilename(
            title="Select Video File to Check Framerate",
            filetypes=[
                ("Video files", "*.mp4 *.mov *.avi *.mkv *.flv *.webm"),
                ("All files", "*.*")
            ]
        )
        
        if not video_path:
            return
        
        try:
            import subprocess
            
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
                    fps_str = result.stdout.strip()
                    if '/' in fps_str:
                        num, den = fps_str.split('/')
                        fps = float(num) / float(den)
                        
                        if abs(fps - 23.976) < 0.1:
                            fps_set = '23.976'
                        elif abs(fps - 29.97) < 0.1:
                            fps_set = '29.97'
                        elif abs(fps - 59.94) < 0.1:
                            fps_set = '59.94'
                        else:
                            fps_set = str(round(fps))
                        
                        self.fps_dropdown.select_option(fps_set)
                        
                        messagebox.showinfo(
                            "Framerate Detected",
                            f"✓ Video framerate: {fps:.2f} fps\n\n"
                            f"Framerate has been set to {fps_set} fps."
                        )
                        return
            except FileNotFoundError:
                pass
            
            try:
                result = subprocess.run(
                    ['ffmpeg', '-i', video_path],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                
                import re
                for line in result.stderr.split('\n'):
                    if 'fps' in line.lower() and 'Stream' in line:
                        match = re.search(r'(\d+\.?\d*)\s*fps', line)
                        if match:
                            fps = float(match.group(1))
                            fps_set = str(round(fps))
                            self.fps_dropdown.select_option(fps_set)
                            
                            messagebox.showinfo(
                                "Framerate Detected",
                                f"✓ Video framerate: {fps} fps\n\n"
                                f"Framerate set to {fps_set}."
                            )
                            return
            except FileNotFoundError:
                pass
            
            messagebox.showerror(
                "Cannot Detect Framerate",
                "Could not detect framerate.\n\n"
                "Please install ffmpeg or set manually."
            )
            
        except Exception as e:
            messagebox.showerror("Error", f"Error: {str(e)}")
        
    def select_and_convert(self):
        try:
            self.framerate = float(self.fps_dropdown.get())
        except ValueError:
            messagebox.showerror("Invalid Framerate", "Please select a valid framerate.")
            return
        
        csv_path = filedialog.askopenfilename(
            title="Select Twitch CSV Marker File",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )
        
        if not csv_path:
            return
        
        try:
            csv_file = Path(csv_path)
            xml_path = csv_file.with_suffix('.xml')
            
            converter = TwitchToXMLConverter(framerate=self.framerate)
            marker_count = converter.convert_csv_to_xml(csv_path, xml_path)
            
            messagebox.showinfo(
                "Conversion Successful",
                f"✓ Successfully converted {marker_count} markers!\n"
                f"✓ Using framerate: {self.framerate} fps\n\n"
                f"File saved to:\n{xml_path}\n\n"
                f"Import: File → Import → Timeline → Import XML"
            )
            
        except Exception as e:
            messagebox.showerror("Conversion Error", f"Error:\n\n{str(e)}")


def main():
    root = tk.Tk()
    app = ConverterGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
