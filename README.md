# 🎬 Twitch to DaVinci Resolve Marker Converter

Convert Twitch stream markers to DaVinci Resolve timeline markers in seconds.

![Python](https://img.shields.io/badge/python-3.6%2B-blue) ![License](https://img.shields.io/badge/license-MIT-green) ![Platform](https://img.shields.io/badge/platform-macOS%20%7C%20Windows%20%7C%20Linux-lightgrey)

---

## 📥 Step 1: Get Your Markers from Twitch

### Export Markers from Twitch

1. **Go to Twitch Creator Dashboard**
   - Visit: https://dashboard.twitch.tv/
   - Login to your account

2. **Navigate to Content → Video Producer**
   - Left sidebar → `Content`
   - Click on `Video Producer`

3. **Find Your VOD**
   - Locate the stream you want to edit
   - Click on the video thumbnail

4. **Download Stream Markers**
   - Look for the "**Stream Markers**" section
   - Click "**Download**" or "**Export**" button
   - Save the CSV file to your computer

**What you'll get:**
```csv
4:08:26,Broadcaster,YourName,
4:58:22,Broadcaster,YourName,
10:12:55,Editor,EditorName,
```

---

## ⚡ Step 2: Convert to DaVinci Resolve Format

### Quick Start

**GUI Version** (Easiest):
```bash
python3 twitch_markers_video_gui.py
```
1. Select the .csv accordingly
2. Select the video file.
3. You get the .xml that you can import in DaVinci as described below.

**CLI Version** (No GUI needed):
```bash
python3 twitch_markers_xml_cli.py your_markers.csv
```


**That's it!** Your `.xml` file is created.

---

## 🎯 Step 3: Import to DaVinci Resolve

### Import Process

```
DaVinci Resolve
  ↓
File → Import → Timeline → Import AAF, EDL, XML...
  ↓
Select your .xml file
  ↓
✅ Timeline created with markers!
```

### Add Your Video

1. Import your Twitch VOD to Media Pool
2. Drag it onto the timeline
3. Markers align perfectly with your video!

### Navigate Markers

- **M** - Next marker
- **Shift+M** - Previous marker

---

## 📦 Available Tools

| Tool | Description | Use When |
|------|-------------|----------|
| `twitch_markers_with_video_gui.py` 🆕⭐ | **NEW:** Timeline with video + markers | Want video already placed - ready to edit! |
| `twitch_markers_xml_gui.py` | GUI with framerate selector | You want easy point-and-click |
| `twitch_markers_xml_cli.py` | CLI with framerate prompt | No GUI or automation |
| `twitch_markers_edl_gui.py` | EDL format GUI | Need EDL compatibility |
| `twitch_markers_edl_cli.py` | EDL format CLI | EDL + automation |
| `check_video_framerate.py` | Framerate detector | Check video fps first |

### 🆕 NEW: Timeline with Video Already Placed! ⭐

**Use `twitch_markers_with_video_gui.py` for the fastest workflow!**

This new tool works differently from the standard converters:

**Standard Workflow:**
```
Convert CSV → Import XML → Empty timeline with markers
→ You manually add video → Markers align
```

**NEW "With Video" Workflow:**
```
Convert CSV + Video → Import XML → Timeline with video ALREADY there!
→ Markers already positioned → Start editing immediately!
```

**Key Differences:**
- ✅ **Auto-detects framerate** from your video (no manual selection needed!)
- ✅ **Video already placed** on timeline
- ✅ **Markers already positioned** on the clip
- ✅ **Ready to edit immediately** - no extra steps
- ⚠️ **Requires:** Both CSV file AND video file as input
- ⚠️ **Requires:** ffprobe installed (comes with ffmpeg)

**How to Use:**
```bash
python3 twitch_markers_with_video_gui.py

1. Choose your CSV markers file
2. Choose your source video file
3. Click "Create XML with Video"
4. Import to Resolve: File → Import → Timeline → Import XML
5. Timeline appears with video + markers already there!
6. Start editing immediately! 🎬
```

**When to Use:**
- ✅ You want the absolute fastest workflow
- ✅ You have the video file ready
- ✅ You want to skip manual video placement
- ✅ You're working with multiple stream clips

**Use standard converter if:**
- You don't have the video file yet
- You want maximum flexibility
- You prefer adding video manually

---

### Which Format?

| Format | Creates | Recommended |
|--------|---------|-------------|
| **XML** | Pure markers (no clips) | ✅ **YES** - Use this! |
| **EDL** | 1-frame clips + markers | ⚠️ Only for compatibility |

---

## 🚀 Installation

### Requirements

```bash
# Check Python version (need 3.6+)
python3 --version

# For GUI versions, install tkinter if needed:
# macOS:
brew install python-tk@3.12

# Ubuntu/Linux:
sudo apt-get install python3-tk
```

### Get the Tools

```bash
git clone https://github.com/yourusername/twitch-to-resolve-markers.git
cd twitch-to-resolve-markers
```

**No pip packages needed!** Uses Python standard library only.

---

## ⚙️ Framerate Guide

### Why Framerate Matters

**Wrong framerate = Markers at wrong times!**

Example: 1-hour video
- ✅ Correct (30 fps) → Markers perfect
- ❌ Wrong (60 fps) → Markers off by 30+ minutes

### Built-in Framerate Selection

**GUI:**
- Select from dropdown (30 fps default)
- Click "Check Video Framerate" to auto-detect

**CLI:**
- Enter framerate when prompted
- Press Enter for default (30 fps)

### Check Your Video Framerate

**Quick check:**
```bash
# Option 1: Use our tool
python3 check_video_framerate.py your_video.mp4

# Option 2: Use ffmpeg
ffmpeg -i your_video.mp4 2>&1 | grep fps
```

**Common Twitch framerates:**
- 30 fps - Standard streaming (most common)
- 60 fps - High-motion gaming

---

## 🎨 Usage Examples

### Example 1: GUI Workflow

```bash
# 1. Launch GUI
python3 twitch_markers_xml_gui.py

# 2. In the window:
#    - Select framerate: 30 fps
#    - Click "CHOOSE CSV & CONVERT"
#    - Select your markers.csv file
#
# 3. Done! Import .xml to DaVinci Resolve
```

### Example 2: CLI Workflow

```bash
# 1. Run converter
python3 twitch_markers_xml_cli.py stream_markers.csv

# 2. When prompted:
#    Enter framerate [default: 30]: 60
#
# 3. Done! Import .xml to DaVinci Resolve
```

### Example 3: Batch Processing

```bash
# Convert all CSV files in folder
for file in *.csv; do
    python3 twitch_markers_xml_cli.py "$file"
done
# Note: You'll be prompted for framerate for each file
```

---

## 🔧 Troubleshooting

### Markers at Wrong Times
- **Fix:** Change framerate and reconvert
- **GUI:** Select different framerate from dropdown
- **CLI:** Run again and enter correct framerate

### "No module named 'tkinter'"
- **Fix:** Use CLI version instead
  ```bash
  python3 twitch_markers_xml_cli.py your_markers.csv
  ```
- **Or install tkinter** (see Installation section)

### GUI Button Not Visible
- **Fix:** Use CLI version
  ```bash
  python3 twitch_markers_xml_cli.py your_markers.csv
  ```

### "No valid markers found"
- **Check CSV format** - Should be: `timestamp,role,username,`
- **Check timestamps** - Should be: `h:mm:ss` format

---

## 📊 Complete Workflow

```
┌─────────────────────────────────────────────────────┐
│                                                     │
│  1. Stream on Twitch                               │
│     └─→ Create markers during stream                │
│                                                     │
│  2. Download CSV from Twitch Dashboard              │
│     └─→ Content → Video Producer → Download         │
│                                                     │
│  3. Check video framerate (if unsure)               │
│     └─→ ffmpeg or check_video_framerate.py          │
│                                                     │
│  4. Run converter                                   │
│     └─→ Select/enter framerate                      │
│     └─→ Choose CSV file                             │
│     └─→ Get .xml output                             │
│                                                     │
│  5. Import to DaVinci Resolve                       │
│     └─→ File → Import → Timeline → XML              │
│                                                     │
│  6. Add your video to timeline                      │
│     └─→ Markers align perfectly!                    │
│                                                     │
│  7. Edit using markers                              │
│     └─→ Press M to jump between markers             │
│                                                     │
└─────────────────────────────────────────────────────┘
```

---

## 📝 CSV Input Format

Your Twitch CSV should look like:

```csv
4:08:26,Broadcaster,StreamerName,Epic clutch moment!
4:58:22,Broadcaster,StreamerName,Funny reaction
10:12:55,Editor,EditorName,Good highlight clip
10:26:55,Moderator,ModName,
```

**Format:** `timestamp,role,username,description`
- **Timestamp:** `h:mm:ss` or `hh:mm:ss`
- **Role:** Broadcaster, Editor, Moderator, etc.
- **Username:** Person who created marker
- **Description:** Optional text (shows in DaVinci Resolve!) ⭐

**In DaVinci Resolve, you'll see:**
- With description: `"Epic clutch moment! - by StreamerName [Broadcaster]"`
- Without description: `"by ModName [Moderator]"`

**Pro tip:** Add descriptions when creating markers on Twitch - they help you remember what each marker is about!

---

## 🎯 XML vs EDL Format

### XML Format (Recommended) ⭐

```
Timeline created:
├── Marker at 4:08:26 "by StreamerName [Broadcaster]"
├── Marker at 4:58:22 "by StreamerName [Broadcaster]"
└── Marker at 10:12:55 "by EditorName [Editor]"

[Empty timeline - add your video]
```

**Pros:**
- ✅ Creates actual markers
- ✅ No cleanup needed
- ✅ Professional workflow

### EDL Format (Legacy)

```
Timeline created:
├── [1-frame clip] + Marker "by StreamerName"
├── [1-frame clip] + Marker "by StreamerName"
└── [1-frame clip] + Marker "by EditorName"

[May need to delete clips]
```

**Pros:**
- ✅ Compatible with other NLE software

**Use XML unless you specifically need EDL!**

---

## 💡 Tips & Tricks

### DaVinci Resolve Tips

- **Color markers:** Right-click marker → Change color
- **Rename markers:** Right-click marker → Edit
- **View all markers:** Window → Markers panel
- **Export markers:** Can export back to EDL/XML if needed

### Workflow Tips

- **Check framerate first** - Saves time reconverting
- **Use 30 fps default** - Most Twitch streams are 30 fps
- **Batch convert** - Process multiple streams at once
- **Verify first marker** - Quick check it aligns with video

---

## 🤝 Contributing

Contributions welcome! Ideas:
- Support for other streaming platforms
- Additional output formats
- Marker color customization
- Marker duration options

---

## 📄 License

MIT License - Free to use and modify

---

## 🙏 Credits

Created for the Twitch streaming and video editing community.

---

## ⚠️ Platform Testing

**Primary testing environment:** macOS

The tools should work on Windows and Linux, but have been primarily developed and tested on macOS. If you encounter platform-specific issues:

- **Windows users:** May need to adjust file paths and ensure ffmpeg is in PATH
- **Linux users:** Install tkinter via package manager if using GUI
- **All platforms:** CLI versions are most reliable across platforms

Please report any platform-specific issues on GitHub!

---

**🎬 Happy editing!**

Questions? Open an issue on GitHub.
