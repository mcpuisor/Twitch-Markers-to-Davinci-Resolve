# Twitch Markers → DaVinci Resolve

Convert Twitch stream markers (CSV) into a DaVinci Resolve timeline (FCP7 XML) linked to your VOD video and audio. Videos longer than 24 hours are automatically split into chunks with ffmpeg, each with its own XML.

![Python](https://img.shields.io/badge/python-3.8%2B-blue) ![License](https://img.shields.io/badge/license-MIT-green) ![Platform](https://img.shields.io/badge/platform-macOS%20%7C%20Windows%20%7C%20Linux-lightgrey)

## Requirements

- **Python 3.8+** with Tkinter (included in the standard python.org installer)
- **FFmpeg** (provides `ffmpeg` and `ffprobe`)
  - macOS: `brew install ffmpeg`
  - Linux: `sudo apt install ffmpeg`
  - Windows: [ffmpeg.org/download](https://ffmpeg.org/download.html) (add to PATH)

## Get your markers from Twitch

1. Go to the [Twitch Creator Dashboard](https://dashboard.twitch.tv/)
2. **Content → Video Producer** → click your VOD
3. In the **Stream Markers** section, click **Download/Export** and save the CSV

The CSV looks like this (`timestamp,role,username,description`):

```csv
4:08:26,Broadcaster,StreamerJoe,Epic clutch moment!
4:58:22,Broadcaster,StreamerJoe,
10:12:55,Editor,EditorMike,
```

See [sample_markers.csv](sample_markers.csv) for a working example.

## Usage

### GUI (macOS app)

Install once, then launch **Twitch Markers** from Launchpad or Spotlight like any app:

```bash
./install.sh
```

This builds `Twitch Markers.app` with the script embedded, signs it, and installs it to `/Applications`. Re-run it after updating the script.

> Why install? macOS privacy protection blocks apps that run from iCloud-synced folders like Documents — installed apps work without prompts.

Or run the GUI from a terminal on any platform:

```bash
python3 twitch_markers_app.py
```

1. Pick your **Markers CSV** (required) — optionally add **Clips** and **Top Clips** CSVs
2. Pick your **Video** — resolution, framerate, duration and audio are detected automatically
3. Click **Create XML**

The XML is written next to your markers CSV. If the video is longer than 24 h, pick a chunk length and the app creates a `chunks/` folder with the video chunks and one XML per chunk.

The first time the app writes files, macOS may ask for access to the folder (e.g. Documents) — click **Allow**.

### CLI

```bash
python3 twitch_markers_app.py markers.csv video.mp4
python3 twitch_markers_app.py markers.csv video.mp4 clips.csv top_clips.csv
python3 twitch_markers_app.py markers.csv video.mp4 --segment-time 43200
```

`--segment-time` sets the chunk length in seconds for videos over 24 h: `3600` = 1 h, `7200` = 2 h, `21600` = 6 h (default), `43200` = 12 h. Clips and top clips are labeled `[CLIP]` / `[TOP CLIP]` in the marker names.

## Import into DaVinci Resolve

**File → Import → Timeline → Import AAF, EDL, XML…** → pick the generated `.xml`

The timeline opens with the video + audio placed and every marker at the right timecode. Note: Resolve ignores marker colors in FCP7 XML — all markers import as the default blue.

## Troubleshooting

**`ffprobe error: dyld: Library not loaded ... libx265.dylib`**
Your Homebrew FFmpeg is broken after a partial upgrade. Fix it with:

```bash
brew reinstall ffmpeg x265
```

**`ffprobe not found`**
Install FFmpeg (see Requirements). The app checks your PATH plus the standard Homebrew/MacPorts locations.

**No markers in the XML**
Check that your CSV rows match `h:mm:ss,role,username[,description]` — malformed rows are skipped.

**The app icon bounces in the Dock and closes immediately**
You launched the `Twitch Markers.app` template from the project folder. macOS blocks apps running from privacy-protected or iCloud-synced folders (like Documents). Run `./install.sh` and launch the installed app from Launchpad, Spotlight, or /Applications instead.

**"App is damaged" or won't open after downloading as a zip**
Downloaded (not cloned) copies are quarantined by macOS. Run `./install.sh` — it re-signs the app during install. Cloning with git avoids this entirely.

**No Python 3 with Tkinter found**
The launcher checks Homebrew, python.org and system Pythons. Install one with: `brew install python python-tk`

## Project structure

```
twitch_markers_app.py    # the whole app: converter + GUI + CLI (single file)
install.sh               # builds the .app with the script embedded and installs it
Twitch Markers.app/      # app bundle template (launcher, Info.plist, icon)
sample_markers.csv       # example input
```

A plain git repo — share it via GitHub, Gerrit, or any git remote. After pulling an update, re-run `./install.sh` to refresh the installed app.

## License

MIT
