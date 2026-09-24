YouTube Backup Downloader for Mac
=================================

WHAT IT DOES
------------
This local app downloads publicly viewable YouTube content as either:
- MP4 video
- MP3 audio only

It accepts:
- A single YouTube video URL
- A YouTube Shorts URL
- A playlist URL
- A channel's Videos URL

HOW TO OPEN IT
--------------
1. Open the "YouTube-Backup-Downloader-MP3-MP4" folder.
2. Double-click "Open YouTube Backup Downloader.command".
3. The first launch installs the required local components.
4. Your browser opens the app automatically.
5. Paste the YouTube URL.
6. Choose MP4 or MP3.
7. If MP4 is selected, choose the video quality.
8. Click Download MP4 or Download MP3.

If macOS says it cannot verify the launcher:
1. Control-click "Open YouTube Backup Downloader.command".
2. Choose Open.
3. Choose Open again.

DEFAULT SAVE LOCATION
---------------------
Downloads/YouTube Channel Backup

You can choose a different folder inside the app.

DOWNLOAD HISTORY
----------------
MP4 downloads continue using:
.youtube-backup-downloaded.txt

MP3 downloads use a separate history file:
.youtube-backup-downloaded-mp3.txt

This means downloading something as MP4 will not stop you from downloading the same URL later as MP3.

IMPORTANT LIMITATIONS
---------------------
- Public videos can be downloaded.
- Unlisted videos require their direct URLs.
- Private videos cannot be recovered without access to the owning account.
- Deleted videos cannot be downloaded from YouTube.
- YouTube sometimes asks for account verification or blocks automated access.
- Use the app only for videos you own or have permission to save.

REQUIREMENTS
------------
- macOS
- Internet connection
- Python 3.10 or newer
