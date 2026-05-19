# Updated Features - Markers & Clips Support

## What's New

The script now supports **merging both Markers and Clips CSV files** into a single timeline XML!

### Key Features:

✅ **Dual CSV Support**: Select both markers and clips CSV files (or just markers)
✅ **Color Coding**: 
   - 🔵 **BLUE markers** = Regular stream markers
   - 🟠 **ORANGE markers** = Clip highlights
✅ **Auto-sorted Timeline**: All markers and clips are automatically sorted by timestamp
✅ **Automatic Output Naming**: 
   - `markers.csv` alone → `markers_with_video.xml`
   - `markers.csv` + `clips.csv` → `markers_and_clips.csv_with_video.xml`

---

## Usage

### GUI Mode (Easiest)

```bash
python3 twitch_markers_with_video_gui.py
```

Then:
1. Select **Markers CSV** (required)
2. Select **Clips CSV** (optional)
3. Select **Video File**
4. Click "🚀 Create XML with Video + Audio"

### CLI Mode

**With markers only:**
```bash
python3 twitch_markers_with_video_gui.py markers.csv video.mp4
```

**With both markers and clips:**
```bash
python3 twitch_markers_with_video_gui.py markers.csv video.mp4 clips.csv
```

**With custom output name:**
```bash
python3 twitch_markers_with_video_gui.py markers.csv video.mp4 clips.csv output.xml
```

---

## Example from Your Folder

```bash
cd "/Volumes/Extreme SSD/Giulia/00_Streams/03_Italia/2026-05-02/"

python3 /Users/Roberto/Documents/01_Scripts/Twitch2DavinciResolve/Twitch-Markers-to-Davinci-Resolve/twitch_markers_with_video_gui.py \
  markers.csv \
  2762178516-601213281-8353b4fb-c82d-42e7-ac67-3304b6c0e022.mp4 \
  clips.csv
```

---

## Results

The generated XML will:
- ✅ Include your video with embedded audio on the timeline
- ✅ Have all 26 markers (BLUE) and 8 clips (ORANGE) at their correct timestamps
- ✅ Detect video properties automatically (resolution, FPS, audio channels)
- ✅ Be ready to import directly into DaVinci Resolve

### Import into DaVinci Resolve:
1. Open DaVinci Resolve
2. Go to **File → Import → Timeline**
3. Choose **Import AAF, EDL, XML...**
4. Select your `markers_and_clips.csv_with_video.xml` file
5. Your entire timeline with video, audio, and color-coded markers will appear!

---

## CSV Format

Both markers.csv and clips.csv use the same format:
```
timestamp,role,username,description(optional)
```

**Example:**
```
0:46:57,Broadcaster,StudyTme,welcome to Naples
2:15:50,Editor,Jallford,important moment
3:40:22,Broadcaster,StudyTme,SPEEDRUNNING NAPOLI 🇮🇹
```

---

## Technical Details

- **Markers are:** Sorted chronologically and merged
- **Colors in DaVinci:** Blue = #0080FF | Orange = #FF8000 (or your theme's orange)
- **Clips are labeled:** `[CLIP]` in the marker name for easy identification
- **Video detection:** Uses ffprobe to detect resolution, FPS, audio properties
- **Frame accuracy:** All timestamps converted to frames based on detected FPS
