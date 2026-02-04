# Recent Updates

## 🎉 New Features (Latest)

### 1. Marker Descriptions Now Included! 📝

**What changed:**
Twitch allows you to add custom text when creating a marker. Now this text appears in DaVinci Resolve!

**CSV Format:**
```csv
timestamp,role,username,description
4:08:26,Broadcaster,StreamerJoe,Epic clutch moment!
4:58:22,Broadcaster,StreamerJoe,Funny reaction
10:12:55,Editor,EditorMike,Good highlight clip
10:26:55,Moderator,ModSarah,
```

**In DaVinci Resolve, you'll see:**
```
Marker 1: "Epic clutch moment! - by StreamerJoe [Broadcaster]"
Marker 2: "Funny reaction - by StreamerJoe [Broadcaster]"
Marker 3: "Good highlight clip - by EditorMike [Editor]"
Marker 4: "by ModSarah [Moderator]"  (no description provided)
```

**Benefits:**
- ✅ See what each marker is about at a glance
- ✅ No need to remember why you marked that moment
- ✅ Better organization in your timeline
- ✅ Easier to find specific moments

---

### 2. Clean Framerate Values 🎯

**What changed:**
Videos with 60 fps, 30 fps, or 24 fps now show clean numbers instead of 59.94, 29.97, or 23.976.

**Before:**
```
Video: 1920x1080 @ 59.94fps
```

**After:**
```
Video: 1920x1080 @ 60.00fps
```

**Auto-rounding for common framerates:**
- 23.976 → 24.0
- 29.97 → 30.0
- 59.94 → 60.0
- Other framerates kept as detected

**Benefits:**
- ✅ Cleaner, more readable
- ✅ Matches what users expect
- ✅ Still accurate for timeline sync

---

## 📋 How to Use Marker Descriptions

### On Twitch (While Streaming):

1. Click "Add Stream Marker"
2. **Add descriptive text!** Examples:
   - "Epic play!"
   - "Funny moment"
   - "Good highlight"
   - "Start of raid"
   - "Subscriber milestone"
3. Continue streaming
4. Repeat for each important moment

### After Streaming:

1. Download your markers CSV
2. Run any of our converters
3. Import to DaVinci Resolve
4. See your descriptions in the markers!

---

## 🎬 Example Workflow

**During Stream:**
```
[Stream starts]
10 minutes in → Epic win! → Add marker: "Clutch 1v4"
25 minutes in → Funny bug → Add marker: "Flying car glitch"
45 minutes in → Subscriber → Add marker: "Thanks xXGamer420Xx"
[Stream ends]
```

**In DaVinci Resolve:**
```
Timeline Markers:
├─ 0:10:15 - "Clutch 1v4 - by StreamerJoe [Broadcaster]"
├─ 0:25:33 - "Flying car glitch - by StreamerJoe [Broadcaster]"
└─ 0:45:12 - "Thanks xXGamer420Xx - by StreamerJoe [Broadcaster]"
```

**Benefits:**
- You remember exactly what happened
- No scrubbing through video to find moments
- Descriptions help you prioritize clips
- Better organization = faster editing

---

## 💡 Pro Tips

### Tip 1: Use Consistent Naming
```
Good examples:
✓ "EPIC - 1v5 clutch"
✓ "FUNNY - Chat freakout"
✓ "MILESTONE - 1000 followers"
✓ "CLIP - For YouTube short"

Benefits:
- Easy to filter by category
- Quick visual scanning
- Better organization
```

### Tip 2: Add Context
```
Instead of: "Good moment"
Better:     "Insane AWP flick on dust2"

Instead of: "Funny"
Better:     "Streamer fails jump 5 times"

Benefits:
- Future you will thank you
- Easier to find specific clips
- Better for compilations
```

### Tip 3: Mark Clip Destinations
```
"YT SHORT - Funny fail"
"TIKTOK - Epic play"
"INSTAGRAM - Subscriber thanks"
"COMPILATION - Rage moment"

Benefits:
- Pre-organize your content
- Know where each clip goes
- Faster content distribution
```

### Tip 4: Timestamp References
```
"Continuation of 0:45:20 story"
"Callback to earlier joke"
"Setup for 2:15:00 punchline"

Benefits:
- Link related moments
- Better narrative flow
- Context for editors
```

---

## 🔧 Technical Details

### Marker Name Format:
```
With description:
  "{description} - by {username} [{role}]"
  
Without description:
  "by {username} [{role}]"
```

### Marker Comment Format:
```
With description:
  "{description} (Twitch marker by {username})"
  
Without description:
  "Twitch marker by {username}"
```

### Character Limits:
- DaVinci Resolve supports long marker names
- Twitch allows descriptions up to 140 characters
- Both name and comment fields are properly escaped for XML

---

## 📊 CSV Format Reference

### Complete Format:
```csv
timestamp,role,username,description
h:mm:ss,Role,Name,Optional text here
```

### Valid Roles:
- Broadcaster
- Editor
- Moderator
- (Any custom role Twitch provides)

### Examples:
```csv
4:08:26,Broadcaster,StreamerJoe,Epic clutch moment!
4:58:22,Broadcaster,StreamerJoe,
10:12:55,Editor,EditorMike,Good highlight clip
```

**Note:** The 4th column (description) is optional. Empty descriptions are perfectly fine!

---

## 🎯 Which Files Support These Features?

### ✅ All Converters Updated:
- `twitch_markers_xml_gui.py` ⭐
- `twitch_markers_xml_cli.py`
- `twitch_markers_with_video_gui.py` 🆕
- `twitch_markers_edl_gui.py`
- `twitch_markers_edl_cli.py`

All converters now:
- ✅ Read marker descriptions from CSV
- ✅ Include descriptions in XML output
- ✅ Show clean framerate values (with-video only)

---

## 🚀 Get Started

Just use the tools as before! The new features work automatically:

1. **Create markers on Twitch** (add descriptions!)
2. **Download CSV** from Twitch
3. **Run converter** (any version)
4. **Import to Resolve** 
5. **See your descriptions!** 🎉

No configuration needed - it just works!

---

## 📝 Migration Notes

**Upgrading from old version?**

Old CSV files (without descriptions) still work perfectly:
```csv
4:08:26,Broadcaster,StreamerJoe,
```
↓
```
Marker: "by StreamerJoe [Broadcaster]"
```

New CSV files (with descriptions) get enhanced markers:
```csv
4:08:26,Broadcaster,StreamerJoe,Epic play!
```
↓
```
Marker: "Epic play! - by StreamerJoe [Broadcaster]"
```

**No breaking changes!** Everything backward compatible. 🎯
