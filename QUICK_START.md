# Quick Start Guide

## ✨ Good News: Framerate is Now Built-In!

**You don't need to manually edit scripts anymore!**

### XML Versions (Recommended)
- **GUI**: Select framerate from dropdown
- **CLI**: Enter framerate when prompted
- **Default**: 30 fps (most common for Twitch)

---

## Which Script Should I Use?

### ⭐ Recommended: XML GUI
**File:** `twitch_markers_xml_gui.py`
```bash
python3 twitch_markers_xml_gui.py
```
- Easiest to use
- Creates actual timeline markers (no clips)
- **Framerate dropdown with auto-detection**
- Best for most users

---

### If you don't have tkinter: XML CLI
**File:** `twitch_markers_xml_cli.py`
```bash
python3 twitch_markers_xml_cli.py your_file.csv
```
- No GUI needed
- Creates actual timeline markers (no clips)
- **Prompts for framerate when you run it**
- Perfect for automation

---

### Need EDL format: EDL GUI
**File:** `twitch_markers_edl_gui.py`
```bash
python3 twitch_markers_edl_gui.py
```
- Easy to use
- Creates 1-frame clips with markers
- For compatibility with other software

---

### EDL via command line: EDL CLI
**File:** `twitch_markers_edl_cli.py`
```bash
python3 twitch_markers_edl_cli.py your_file.csv
```
- No GUI needed
- Creates 1-frame clips with markers
- For compatibility with other software

---

## File Naming Explained

All files follow this pattern: `twitch_markers_[FORMAT]_[INTERFACE].py`

- **FORMAT:**
  - `xml` = Creates actual timeline markers (recommended)
  - `edl` = Creates 1-frame clips with markers (legacy)

- **INTERFACE:**
  - `gui` = Graphical user interface (click button)
  - `cli` = Command line interface (type command)

## Examples

- `twitch_markers_xml_gui.py` = XML format + GUI = ⭐ Recommended
- `twitch_markers_xml_cli.py` = XML format + CLI = No GUI needed
- `twitch_markers_edl_gui.py` = EDL format + GUI = Legacy/compatibility
- `twitch_markers_edl_cli.py` = EDL format + CLI = Legacy/compatibility

---

## Quick Decision Tree

```
Do you want actual markers (no clips)?
├─ Yes → Use XML format
│  ├─ Have tkinter? → twitch_markers_xml_gui.py
│  └─ No tkinter? → twitch_markers_xml_cli.py
│
└─ Need EDL for other software?
   ├─ Have tkinter? → twitch_markers_edl_gui.py
   └─ No tkinter? → twitch_markers_edl_cli.py
```

---

**Still unsure? Start with:** `twitch_markers_xml_gui.py` ⭐
