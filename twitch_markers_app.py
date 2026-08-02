#!/usr/bin/env python3
"""
Twitch Markers → DaVinci Resolve

Converts Twitch stream markers (CSV) to an FCP7 XML timeline linked to your
VOD video + audio, ready to import into DaVinci Resolve. Videos longer than
24 hours are automatically split into chunks with ffmpeg, each with its own XML.

Run without arguments to launch the GUI, or pass files for CLI mode:

    python3 twitch_markers_app.py                          # GUI
    python3 twitch_markers_app.py markers.csv video.mp4    # CLI

CSV format: timestamp,role,username,description(optional)
Example:    4:08:26,Broadcaster,StreamerJoe,Epic clutch moment!
"""

import csv
import html
import json
import os
import shutil
import subprocess
import sys
import threading
from datetime import timedelta
from pathlib import Path
from urllib.parse import quote

import tkinter as tk
from tkinter import filedialog, messagebox


# ─── FFmpeg discovery ─────────────────────────────────────────────────────────

# GUI apps on macOS don't inherit the shell PATH, so also probe the usual
# package-manager locations.
_TOOL_DIRS = ("/opt/homebrew/bin", "/usr/local/bin", "/opt/local/bin")


def find_tool(name):
    path = shutil.which(name)
    if path:
        return path
    for d in _TOOL_DIRS:
        candidate = os.path.join(d, name)
        if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
            return candidate
    return None


def _tool_error(name, stderr=""):
    if "Library not loaded" in stderr or "dyld" in stderr:
        return (f"{name} is installed but broken (a linked library is missing).\n"
                "This usually happens after a partial Homebrew upgrade.\n"
                "Fix it by running:  brew reinstall ffmpeg x265")
    if not stderr:
        return (f"{name} not found. Install FFmpeg first:\n"
                "  macOS:  brew install ffmpeg\n"
                "  Linux:  sudo apt install ffmpeg")
    return f"{name} error: {stderr.strip()}"


# ─── Video info detection ─────────────────────────────────────────────────────

COMMON_FRAMERATES = {
    23.976: 24, 23.98: 24, 24.0: 24,
    25.0: 25,
    29.97: 30, 30.0: 30,
    50.0: 50,
    59.94: 60, 60.0: 60,
}


def round_framerate(fps):
    """Round detected framerate to the nearest common editing framerate."""
    fps_rounded = round(fps, 2)
    if fps_rounded in COMMON_FRAMERATES:
        return COMMON_FRAMERATES[fps_rounded]
    closest = min(COMMON_FRAMERATES.keys(), key=lambda x: abs(x - fps))
    if abs(closest - fps) < 1.0:
        return COMMON_FRAMERATES[closest]
    return int(round(fps))


def detect_video_info(video_path):
    """Use ffprobe to detect video properties."""
    ffprobe = find_tool("ffprobe")
    if not ffprobe:
        raise RuntimeError(_tool_error("ffprobe"))

    cmd = [ffprobe, '-v', 'quiet', '-print_format', 'json',
           '-show_streams', '-show_format', str(video_path)]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    except Exception as e:
        raise RuntimeError(f"Failed to run ffprobe: {e}")
    if result.returncode != 0:
        raise RuntimeError(_tool_error("ffprobe", result.stderr))

    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError:
        raise RuntimeError(_tool_error("ffprobe", result.stderr or "no output"))

    video_stream = None
    audio_stream = None
    for stream in data.get('streams', []):
        if stream.get('codec_type') == 'video' and video_stream is None:
            video_stream = stream
        elif stream.get('codec_type') == 'audio' and audio_stream is None:
            audio_stream = stream

    if not video_stream:
        raise RuntimeError("No video stream found in file")

    r_frame_rate = video_stream.get('r_frame_rate', '30/1')
    if '/' in r_frame_rate:
        num, den = map(int, r_frame_rate.split('/'))
        raw_fps = num / den if den != 0 else 30.0
    else:
        raw_fps = float(r_frame_rate)

    duration = float(data.get('format', {}).get('duration',
                     video_stream.get('duration', '0')))

    has_audio = audio_stream is not None
    audio_bit_depth = int(audio_stream.get('bits_per_sample', 16)) if has_audio else 16
    if audio_bit_depth == 0:
        audio_bit_depth = 16  # compressed formats (AAC) report 0

    return {
        'width': int(video_stream.get('width', 1920)),
        'height': int(video_stream.get('height', 1080)),
        'fps': round_framerate(raw_fps),
        'duration': duration,
        'has_audio': has_audio,
        'audio_channels': int(audio_stream.get('channels', 2)) if has_audio else 0,
        'audio_sample_rate': int(audio_stream.get('sample_rate', 48000)) if has_audio else 48000,
        'audio_bit_depth': audio_bit_depth,
    }


# ─── Converter ────────────────────────────────────────────────────────────────

SPLIT_THRESHOLD = 86400   # split videos longer than 24h
DEFAULT_SEGMENT = 21600   # 6h chunks


class TwitchMarkersConverter:
    def __init__(self):
        self.framerate = 30

    # DaVinci Resolve ignores marker colors in FCP7 XML, so every marker
    # imports as the default Blue regardless of what we emit here.
    MARKER_RGB = (0, 102, 255)

    def parse_timestamp(self, timestamp_str):
        """Parse timestamp from format h:mm:ss or hh:mm:ss."""
        parts = timestamp_str.strip().split(':')
        if len(parts) == 3:
            return timedelta(hours=int(parts[0]), minutes=int(parts[1]),
                             seconds=int(parts[2]))
        raise ValueError(f"Invalid timestamp format: {timestamp_str}")

    def timedelta_to_frames(self, td):
        return int(td.total_seconds() * self.framerate)

    def read_markers(self, csv_path, marker_type="marker"):
        """Read markers from a CSV file. marker_type: 'marker', 'clip' or 'top_clip'."""
        markers = []
        with open(csv_path, 'r', encoding='utf-8-sig') as f:
            for row in csv.reader(f):
                if len(row) >= 3 and row[0].strip():
                    try:
                        td = self.parse_timestamp(row[0].strip())
                    except (ValueError, IndexError):
                        continue
                    markers.append({
                        'timestamp': row[0].strip(),
                        'timedelta': td,
                        'role': row[1].strip(),
                        'username': row[2].strip(),
                        'description': row[3].strip() if len(row) > 3 else '',
                        'type': marker_type,
                    })
        return markers

    def read_markers_and_clips(self, markers_csv_path, clips_csv_path=None,
                               top_clips_csv_path=None):
        """Read and merge markers, clips and top clips, sorted by time."""
        all_markers = []
        if markers_csv_path:
            all_markers.extend(self.read_markers(markers_csv_path, "marker"))
        if clips_csv_path:
            all_markers.extend(self.read_markers(clips_csv_path, "clip"))
        if top_clips_csv_path:
            all_markers.extend(self.read_markers(top_clips_csv_path, "top_clip"))
        all_markers.sort(key=lambda m: m['timedelta'])
        return all_markers

    def video_path_to_url(self, video_path):
        """Convert file path to file://localhost/ URL (FCP7 XML standard)."""
        return "file://localhost" + quote(os.path.abspath(video_path), safe="/:")

    def generate_xml(self, csv_path, video_path, output_path, clips_csv_path=None,
                     top_clips_csv_path=None, segment_time=DEFAULT_SEGMENT):
        """Generate FCP7 XML with video, audio and markers.
        Videos longer than 24h are split into chunks with ffmpeg first."""
        video_info = detect_video_info(video_path)
        self.framerate = video_info['fps']

        if video_info['duration'] > SPLIT_THRESHOLD:
            return self._generate_chunks_and_xmls(
                csv_path, video_path, output_path, clips_csv_path,
                top_clips_csv_path, video_info, segment_time)
        return self._generate_single_xml(
            csv_path, video_path, output_path, clips_csv_path,
            top_clips_csv_path, video_info)

    def _run_ffmpeg_split(self, video_path, chunks_dir, segment_time):
        """Split the video into chunks with ffmpeg. Returns chunk filenames."""
        ffmpeg = find_tool("ffmpeg")
        if not ffmpeg:
            raise RuntimeError(_tool_error("ffmpeg"))

        video_stem = Path(video_path).stem
        video_ext = Path(video_path).suffix
        chunk_pattern = os.path.join(chunks_dir, f"{video_stem}_chunk_%03d{video_ext}")

        cmd = [
            ffmpeg, '-i', str(video_path),
            '-c:v', 'copy',
            '-c:a', 'copy',
            '-map', '0',
            '-segment_time', str(segment_time),
            '-f', 'segment',
            '-reset_timestamps', '1',
            '-fflags', '+genpts',
            '-movflags', '+faststart',
            '-y',
            chunk_pattern
        ]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
        except Exception as e:
            raise RuntimeError(f"Failed to split video: {e}")
        if result.returncode != 0:
            raise RuntimeError(_tool_error("ffmpeg", result.stderr))

        return sorted(f for f in os.listdir(chunks_dir)
                      if f.startswith(f"{video_stem}_chunk_"))

    def _generate_chunks_and_xmls(self, csv_path, video_path, output_path,
                                  clips_csv_path, top_clips_csv_path,
                                  video_info, segment_time):
        """Split the video with ffmpeg, then generate one XML per chunk."""
        chunks_dir = os.path.join(os.path.dirname(output_path), "chunks")
        os.makedirs(chunks_dir, exist_ok=True)

        chunk_files = self._run_ffmpeg_split(video_path, chunks_dir, segment_time)
        if not chunk_files:
            raise RuntimeError("No chunks were created by ffmpeg")

        all_markers = self.read_markers_and_clips(csv_path, clips_csv_path,
                                                  top_clips_csv_path)
        if not all_markers:
            raise ValueError("No valid markers/clips found in CSV files")

        chunk_info_list = []
        for idx, chunk_file in enumerate(chunk_files):
            chunk_path = os.path.join(chunks_dir, chunk_file)
            chunk_start_td = timedelta(seconds=idx * segment_time)
            chunk_end_td = timedelta(seconds=(idx + 1) * segment_time)

            chunk_info = detect_video_info(chunk_path)

            # Keep markers inside this chunk, re-based to the chunk start.
            chunk_markers = []
            for marker in all_markers:
                if chunk_start_td <= marker['timedelta'] < chunk_end_td:
                    m = dict(marker)
                    m['timedelta'] = marker['timedelta'] - chunk_start_td
                    total = int(m['timedelta'].total_seconds())
                    m['timestamp'] = f"{total // 3600}:{(total % 3600) // 60:02d}:{total % 60:02d}"
                    chunk_markers.append(m)

            xml_filename = f"{Path(csv_path).stem}_chunk_{idx:03d}_with_video.xml"
            xml_path = os.path.join(chunks_dir, xml_filename)
            self._write_xml_file(
                xml_path, chunk_markers, chunk_path,
                self.video_path_to_url(chunk_path),
                int(chunk_info['duration'] * self.framerate),
                chunk_info, chunk_file,
                timeline_name=f"{Path(csv_path).stem}_chunk_{idx:03d}")

            chunk_info_list.append({
                'chunk_file': chunk_file,
                'chunk_path': chunk_path,
                'xml_file': xml_filename,
                'xml_path': xml_path,
                'markers_count': len(chunk_markers),
                'start_time': chunk_start_td,
                'duration': chunk_info['duration'],
            })

        return {
            'total_markers': len(all_markers),
            'chunks': chunk_info_list,
            'video_info': video_info,
            'split': True,
            'chunks_dir': chunks_dir,
        }

    def _generate_single_xml(self, csv_path, video_path, output_path,
                             clips_csv_path, top_clips_csv_path, video_info):
        markers = self.read_markers_and_clips(csv_path, clips_csv_path,
                                              top_clips_csv_path)
        if not markers:
            raise ValueError("No valid markers/clips found in CSV files")

        self._write_xml_file(
            output_path, markers, video_path,
            self.video_path_to_url(video_path),
            int(video_info['duration'] * self.framerate),
            video_info, os.path.basename(video_path),
            timeline_name=Path(csv_path).stem + "_with_video")

        return {
            'total_markers': len(markers),
            'output_path': output_path,
            'video_info': video_info,
            'split': False,
        }

    def _write_xml_file(self, output_path, markers, video_path, video_url,
                        video_duration_frames, video_info, video_filename,
                        start_frame=0, timeline_name=None):
        has_audio = video_info['has_audio']
        audio_channels = video_info['audio_channels'] if has_audio else 2
        audio_sample_rate = video_info['audio_sample_rate']
        audio_bit_depth = video_info['audio_bit_depth']

        if not timeline_name:
            timeline_name = Path(video_path).stem + "_with_video"

        tb = int(self.framerate)
        esc = lambda text: html.escape(str(text), quote=True)

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
        type_label = {"clip": "[CLIP]", "top_clip": "[TOP CLIP]"}
        r, g, b = self.MARKER_RGB
        for marker in markers:
            frame_pos = self.timedelta_to_frames(marker['timedelta'])
            label = type_label.get(marker['type'], "")
            suffix = (" " + label) if label else ""
            if marker['description']:
                mname = f"{marker['description']} - by {marker['username']} [{marker['role']}]{suffix}"
                mcomment = f"{marker['description']} (Twitch marker by {marker['username']})"
            else:
                mname = f"by {marker['username']} [{marker['role']}]{suffix}"
                mcomment = f"Twitch marker by {marker['username']}"
            a('    <marker>')
            a('      <name>' + esc(mname) + '</name>')
            a('      <comment>' + esc(mcomment) + '</comment>')
            a('      <in>' + str(frame_pos) + '</in>')
            a('      <out>' + str(frame_pos + 1) + '</out>')
            a('      <color>')
            a('        <alpha>255</alpha>')
            a('        <red>' + str(r) + '</red>')
            a('        <green>' + str(g) + '</green>')
            a('        <blue>' + str(b) + '</blue>')
            a('      </color>')
            a('    </marker>')

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
        a('          <clipitem id="clipitem-1" frameBlend="FALSE">')
        a('            <name>' + esc(video_filename) + '</name>')
        a('            <duration>' + str(video_duration_frames) + '</duration>')
        a('            <rate>')
        a('              <timebase>' + str(tb) + '</timebase>')
        a('              <ntsc>FALSE</ntsc>')
        a('            </rate>')
        a('            <start>0</start>')
        a('            <end>' + str(video_duration_frames) + '</end>')
        a('            <in>' + str(start_frame) + '</in>')
        a('            <out>' + str(start_frame + video_duration_frames) + '</out>')
        a('            <file id="file-1">')
        a('              <name>' + esc(video_filename) + '</name>')
        a('              <pathurl>' + esc(video_url) + '</pathurl>')
        a('              <rate>')
        a('                <timebase>' + str(tb) + '</timebase>')
        a('                <ntsc>FALSE</ntsc>')
        a('              </rate>')
        a('              <duration>' + str(int(video_info["duration"] * self.framerate)) + '</duration>')
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
        a('            <sourcetrack>')
        a('              <mediatype>video</mediatype>')
        a('              <trackindex>1</trackindex>')
        a('            </sourcetrack>')
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

        # AUDIO TRACK (single stereo track, same file)
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
            a('            <in>' + str(start_frame) + '</in>')
            a('            <out>' + str(start_frame + video_duration_frames) + '</out>')
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

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write("\n".join(L))


def build_output_path(markers_csv_path, clips_csv_path, top_clips_csv_path):
    """Output XML path next to the markers CSV, suffixed by what's included."""
    suffix_parts = []
    if clips_csv_path:
        suffix_parts.append("clips")
    if top_clips_csv_path:
        suffix_parts.append("top_clips")
    suffix = ("_and_" + "_and_".join(suffix_parts)) if suffix_parts else ""
    return str(Path(markers_csv_path).with_suffix('')) + suffix + "_with_video.xml"


# ─── GUI ──────────────────────────────────────────────────────────────────────

class Theme:
    BG = "#131316"
    CARD = "#1C1C21"
    CARD_HOVER = "#26262D"
    BORDER = "#2E2E36"
    TEXT = "#EDEDF0"
    MUTED = "#8B8B94"
    FAINT = "#5C5C66"
    ACCENT = "#9146FF"        # Twitch purple
    ACCENT_HOVER = "#A970FF"
    OK = "#3DDC84"
    WARN = "#F5A623"
    ERROR = "#FF5C5C"

    @staticmethod
    def font(size, weight="normal"):
        family = "Helvetica Neue" if sys.platform == "darwin" else "Segoe UI"
        return (family, size, weight)


class AccentButton(tk.Canvas):
    """Flat rounded button drawn on a canvas (renders consistently on macOS)."""

    def __init__(self, parent, text, command, width=280, height=44,
                 bg=Theme.ACCENT, hover=Theme.ACCENT_HOVER, fg="#FFFFFF",
                 font=None, radius=10):
        super().__init__(parent, width=width, height=height,
                         bg=parent["bg"], highlightthickness=0)
        self._command = command
        self._bg, self._hover = bg, hover
        self._enabled = True
        r = radius
        w, h = width, height
        # Rounded rectangle as a smoothed polygon
        points = (r, 0, w - r, 0, w, 0, w, r, w, h - r, w, h, w - r, h,
                  r, h, 0, h, 0, h - r, 0, r, 0, 0)
        self._rect = self.create_polygon(points, smooth=True, fill=bg)
        self._label = self.create_text(w // 2, h // 2, text=text, fill=fg,
                                       font=font or Theme.font(13, "bold"))
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<Button-1>", self._on_click)
        self.configure(cursor="hand2")

    def _on_enter(self, _):
        if self._enabled:
            self.itemconfig(self._rect, fill=self._hover)

    def _on_leave(self, _):
        if self._enabled:
            self.itemconfig(self._rect, fill=self._bg)

    def _on_click(self, _):
        if self._enabled and self._command:
            self._command()

    def set_enabled(self, enabled):
        self._enabled = enabled
        self.itemconfig(self._rect, fill=self._bg if enabled else Theme.BORDER)
        self.configure(cursor="hand2" if enabled else "arrow")


class FileRow(tk.Frame):
    """A clickable card row: title + selected filename. Click to browse."""

    def __init__(self, parent, title, required, on_pick, filetypes, dialog_title):
        super().__init__(parent, bg=Theme.CARD, padx=16, pady=12,
                         highlightbackground=Theme.BORDER, highlightthickness=1)
        self._on_pick = on_pick
        self._filetypes = filetypes
        self._dialog_title = dialog_title
        self.path = None

        top = tk.Frame(self, bg=Theme.CARD)
        top.pack(fill='x')
        tk.Label(top, text=title, font=Theme.font(12, "bold"),
                 bg=Theme.CARD, fg=Theme.TEXT).pack(side='left')
        badge = "required" if required else "optional"
        badge_fg = Theme.ACCENT_HOVER if required else Theme.FAINT
        tk.Label(top, text=badge, font=Theme.font(9),
                 bg=Theme.CARD, fg=badge_fg).pack(side='right')

        self._value = tk.Label(self, text="Click to choose a file…",
                               font=Theme.font(10), bg=Theme.CARD,
                               fg=Theme.FAINT, anchor='w')
        self._value.pack(fill='x', pady=(4, 0))

        for w in (self, top, *top.winfo_children(), self._value):
            w.bind("<Button-1>", self._browse)
            w.bind("<Enter>", lambda e: self._set_bg(Theme.CARD_HOVER))
            w.bind("<Leave>", lambda e: self._set_bg(Theme.CARD))
        self.configure(cursor="hand2")

    def _set_bg(self, color):
        self.configure(bg=color)
        for w in self.winfo_children():
            w.configure(bg=color)
            for c in w.winfo_children():
                c.configure(bg=color)

    def _browse(self, _=None):
        path = filedialog.askopenfilename(title=self._dialog_title,
                                          filetypes=self._filetypes)
        if path:
            self.path = path
            self._value.config(text=os.path.basename(path), fg=Theme.TEXT)
            self._on_pick(path)


class TwitchMarkersApp:
    CSV_TYPES = [("CSV files", "*.csv"), ("All files", "*.*")]
    VIDEO_TYPES = [("Video files", "*.mp4 *.mkv *.mov *.avi *.webm *.ts *.flv *.m4v"),
                   ("All files", "*.*")]
    SEGMENT_CHOICES = {"1 hour": 3600, "2 hours": 7200,
                       "6 hours": 21600, "12 hours": 43200}

    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Twitch Markers → DaVinci Resolve")
        self.root.configure(bg=Theme.BG)
        self.root.resizable(False, False)

        self.video_path = None
        self.video_info = None
        self.converter = TwitchMarkersConverter()
        self._build_ui()

    def _build_ui(self):
        pad = dict(fill='x', padx=28)

        header = tk.Frame(self.root, bg=Theme.BG)
        header.pack(pady=(26, 18), **pad)
        tk.Label(header, text="Twitch Markers → DaVinci Resolve",
                 font=Theme.font(17, "bold"), bg=Theme.BG,
                 fg=Theme.TEXT).pack(anchor='w')
        tk.Label(header, text="CSV markers to an XML timeline with video + audio",
                 font=Theme.font(11), bg=Theme.BG, fg=Theme.MUTED).pack(anchor='w')

        self.markers_row = FileRow(self.root, "Markers CSV", True,
                                   lambda p: self._clear_status(),
                                   self.CSV_TYPES, "Choose Twitch Markers CSV")
        self.markers_row.pack(pady=(0, 8), **pad)

        self.clips_row = FileRow(self.root, "Clips CSV", False,
                                 lambda p: self._clear_status(),
                                 self.CSV_TYPES, "Choose Clips CSV")
        self.clips_row.pack(pady=(0, 8), **pad)

        self.top_clips_row = FileRow(self.root, "Top Clips CSV", False,
                                     lambda p: self._clear_status(),
                                     self.CSV_TYPES, "Choose Top Clips CSV")
        self.top_clips_row.pack(pady=(0, 8), **pad)

        self.video_row = FileRow(self.root, "Video", True, self._on_video_picked,
                                 self.VIDEO_TYPES, "Choose Video File")
        self.video_row.pack(pady=(0, 8), **pad)

        self.info_label = tk.Label(self.root, text="", font=Theme.font(10),
                                   bg=Theme.BG, fg=Theme.MUTED,
                                   anchor='w', justify='left')

        # Chunk-length picker, shown only for videos > 24h
        self.segment_frame = tk.Frame(self.root, bg=Theme.BG)
        tk.Label(self.segment_frame, text="Chunk length",
                 font=Theme.font(10), bg=Theme.BG,
                 fg=Theme.MUTED).pack(side='left')
        self.segment_var = tk.StringVar(value="6 hours")
        opt = tk.OptionMenu(self.segment_frame, self.segment_var,
                            *self.SEGMENT_CHOICES.keys())
        opt.config(font=Theme.font(10), bg=Theme.CARD, fg=Theme.TEXT,
                   activebackground=Theme.CARD_HOVER, activeforeground=Theme.TEXT,
                   highlightthickness=0, relief='flat')
        opt["menu"].config(bg=Theme.CARD, fg=Theme.TEXT,
                           activebackground=Theme.ACCENT)
        opt.pack(side='left', padx=(10, 0))

        self.convert_btn = AccentButton(self.root, "Create XML", self._convert)
        self.convert_btn.pack(pady=(18, 0))

        self.status_label = tk.Label(self.root, text=" ", font=Theme.font(10),
                                     bg=Theme.BG, fg=Theme.MUTED, wraplength=520,
                                     justify='left')
        self.status_label.pack(pady=(10, 6), **pad)

        tk.Label(self.root,
                 text="CSV format:  timestamp,role,username,description   ·   "
                      "videos over 24 h are auto-split",
                 font=Theme.font(9), bg=Theme.BG,
                 fg=Theme.FAINT).pack(pady=(0, 20), **pad)

        self.root.update_idletasks()
        self.root.minsize(560, self.root.winfo_reqheight())

    def _clear_status(self):
        self.status_label.config(text=" ", fg=Theme.MUTED)

    def _set_status(self, text, color=Theme.MUTED):
        self.status_label.config(text=text, fg=color)

    def _on_video_picked(self, path):
        self.video_path = path
        self._set_status("Detecting video properties…")
        self.root.update_idletasks()
        try:
            info = detect_video_info(path)
        except Exception as e:
            self.video_info = None
            self.info_label.pack_forget()
            self.segment_frame.pack_forget()
            self._set_status(str(e), Theme.ERROR)
            return

        self.video_info = info
        audio = "no audio"
        if info['has_audio']:
            audio = f"{info['audio_channels']}ch {info['audio_sample_rate']} Hz audio"
        text = (f"{info['width']}×{info['height']}  ·  {info['fps']} fps  ·  "
                f"{timedelta(seconds=int(info['duration']))}  ·  {audio}")
        self.info_label.config(text=text)
        self.info_label.pack(fill='x', padx=32, pady=(0, 8))

        if info['duration'] > SPLIT_THRESHOLD:
            self.segment_frame.pack(fill='x', padx=32, pady=(0, 8))
            self._set_status("Video is longer than 24 h — it will be split into "
                             "chunks, each with its own XML.", Theme.WARN)
        else:
            self.segment_frame.pack_forget()
            self._clear_status()

    def _convert(self):
        if not self.markers_row.path:
            messagebox.showwarning("Missing file", "Please select a Markers CSV file.")
            return
        if not self.video_path:
            messagebox.showwarning("Missing file", "Please select a video file.")
            return

        segment_time = self.SEGMENT_CHOICES[self.segment_var.get()]
        output_path = build_output_path(self.markers_row.path,
                                        self.clips_row.path,
                                        self.top_clips_row.path)

        self.convert_btn.set_enabled(False)
        splitting = self.video_info and self.video_info['duration'] > SPLIT_THRESHOLD
        self._set_status("Splitting video and generating XMLs — this can take "
                         "a while…" if splitting else "Generating XML…", Theme.WARN)

        threading.Thread(target=self._do_convert,
                         args=(output_path, segment_time), daemon=True).start()

    def _do_convert(self, output_path, segment_time):
        try:
            result = self.converter.generate_xml(
                self.markers_row.path, self.video_path, output_path,
                clips_csv_path=self.clips_row.path,
                top_clips_csv_path=self.top_clips_row.path,
                segment_time=segment_time)
            self.root.after(0, self._on_convert_done, result)
        except Exception as e:
            self.root.after(0, self._on_convert_error, str(e))

    def _on_convert_done(self, result):
        self.convert_btn.set_enabled(True)
        resolve_hint = ("Import in DaVinci Resolve:\n"
                        "File → Import → Timeline → Import AAF, EDL, XML…")

        if result['split']:
            chunks = result['chunks']
            summary = "\n".join(
                f"  {c['chunk_file']}  ({timedelta(seconds=int(c['duration']))}, "
                f"{c['markers_count']} markers)" for c in chunks)
            self._set_status(f"Done — {len(chunks)} chunks + XMLs in "
                             f"{result['chunks_dir']}", Theme.OK)
            messagebox.showinfo(
                "Video chunked",
                f"Created {len(chunks)} chunks ({result['total_markers']} markers "
                f"total) in:\n{result['chunks_dir']}\n\n{summary}\n\n"
                f"Each chunk has its own _with_video.xml.\n\n{resolve_hint}")
        else:
            info = result['video_info']
            audio = f"{info['audio_channels']} channels" if info['has_audio'] else "none"
            self._set_status(f"Done — {result['total_markers']} markers → "
                             f"{os.path.basename(result['output_path'])}", Theme.OK)
            messagebox.showinfo(
                "XML created",
                f"{os.path.basename(result['output_path'])}\n\n"
                f"Markers: {result['total_markers']}\n"
                f"Video: {info['width']}×{info['height']} @ {info['fps']} fps\n"
                f"Duration: {timedelta(seconds=int(info['duration']))}\n"
                f"Audio: {audio}\n\n{resolve_hint}")

    def _on_convert_error(self, message):
        self.convert_btn.set_enabled(True)
        self._set_status(message, Theme.ERROR)
        messagebox.showerror("Error", message)

    def run(self):
        # Tk windows open behind other apps when launched from Finder;
        # briefly toggle topmost to bring the window to the front.
        self.root.lift()
        self.root.attributes('-topmost', True)
        self.root.after(200, lambda: self.root.attributes('-topmost', False))
        self.root.mainloop()


# ─── CLI mode ─────────────────────────────────────────────────────────────────

def cli_mode():
    args = sys.argv[1:]
    if len(args) < 2 or args[0] in ("-h", "--help"):
        print("Usage: python3 twitch_markers_app.py <markers.csv> <video> "
              "[clips.csv] [top_clips.csv] [--segment-time SECONDS]")
        print("       python3 twitch_markers_app.py              (launches GUI)")
        print("\nSegment time (for videos > 24h): 3600=1h, 7200=2h, "
              "21600=6h (default), 43200=12h")
        sys.exit(0 if args and args[0] in ("-h", "--help") else 1)

    segment_time = DEFAULT_SEGMENT
    if '--segment-time' in args:
        idx = args.index('--segment-time')
        try:
            segment_time = int(args[idx + 1])
            del args[idx:idx + 2]
        except (ValueError, IndexError):
            sys.exit("Error: --segment-time requires a number of seconds")

    markers_csv_path, video_path = args[0], args[1]
    extra_csvs = [a for a in args[2:] if a.lower().endswith('.csv')]
    clips_csv_path = extra_csvs[0] if len(extra_csvs) >= 1 else None
    top_clips_csv_path = extra_csvs[1] if len(extra_csvs) >= 2 else None

    for label, p in (("Markers CSV", markers_csv_path), ("Video", video_path),
                     ("Clips CSV", clips_csv_path),
                     ("Top Clips CSV", top_clips_csv_path)):
        if p and not os.path.exists(p):
            sys.exit(f"Error: {label} file not found: {p}")

    output_path = build_output_path(markers_csv_path, clips_csv_path,
                                    top_clips_csv_path)
    converter = TwitchMarkersConverter()
    result = converter.generate_xml(
        markers_csv_path, video_path, output_path,
        clips_csv_path=clips_csv_path,
        top_clips_csv_path=top_clips_csv_path,
        segment_time=segment_time)

    if result['split']:
        print(f"Created {len(result['chunks'])} video chunks in "
              f"{result['chunks_dir']}/:")
        for c in result['chunks']:
            print(f"  {c['chunk_file']}  "
                  f"({timedelta(seconds=int(c['duration']))}, "
                  f"{c['markers_count']} markers)")
    else:
        print(f"Created {result['output_path']} "
              f"({result['total_markers']} markers)")

    info = result['video_info']
    print(f"\nVideo: {info['width']}x{info['height']} @ {info['fps']}fps, "
          f"duration {timedelta(seconds=int(info['duration']))}, "
          f"audio: {'yes' if info['has_audio'] else 'no'}")
    print("\nImport in DaVinci Resolve:")
    print("  File → Import → Timeline → Import AAF, EDL, XML… → pick the .xml")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        cli_mode()
    else:
        TwitchMarkersApp().run()
