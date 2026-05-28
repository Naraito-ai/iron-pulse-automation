import subprocess, os

inp  = r'D:\ai-instagram-automation\backend\assets\generated\test_pro_reel.mp4'
out  = r'D:\ai-instagram-automation\backend\assets\generated\caption_test_out.mp4'

# Try using PIL/Pillow to burn text ONTO frames instead of ffmpeg drawtext
# This is more reliable on Windows
from PIL import Image, ImageDraw, ImageFont
import tempfile

font_path = r'C:\Windows\Fonts\arialbd.ttf'
try:
    font_title = ImageFont.truetype(font_path, 80)
    font_body = ImageFont.truetype(font_path, 50)
    print("Font loaded OK")
except Exception as e:
    print("Font error:", e)
    font_title = ImageFont.load_default()

# Extract frame from video, add text, use as overlay
# Actually, use Python to add captions by drawing on EACH FRAME
# Better approach: use a PNG overlay with text, then ffmpeg overlay filter

overlay_path = r'D:\ai-instagram-automation\backend\assets\generated\text_overlay.png'
W, H = 1080, 1920

# Create transparent PNG overlay
overlay = Image.new('RGBA', (W, H), (0, 0, 0, 0))
draw = ImageDraw.Draw(overlay)

# Dark scrim
draw.rectangle([(0, int(H*0.65)), (W, H)], fill=(0, 0, 0, 178))  # 70% opacity
# Orange bar
draw.rectangle([(0, int(H*0.65)), (W, int(H*0.65)+8)], fill=(255, 85, 0, 255))
# Title text
draw.text((W//2, int(H*0.65)+30), 'IRON PULSE', font=font_title, fill=(255,255,255,255), anchor='mm')
draw.text((W//2, int(H*0.65)+130), 'Best Pre-Workout Powders 2025', font=font_body, fill=(255,136,0,255), anchor='mm')
# Brand badge
draw.text((50, 60), 'IRON PULSE', font=font_body, fill=(255,136,0,255))

overlay.save(overlay_path)
print(f"Overlay saved: {os.path.getsize(overlay_path)} bytes")

# Now overlay it on the video
cmd = [
    'ffmpeg', '-y',
    '-i', inp,
    '-i', overlay_path,
    '-filter_complex', '[0:v][1:v]overlay=0:0',
    '-c:v', 'libx264', '-pix_fmt', 'yuv420p',
    '-c:a', 'copy',
    out
]
r = subprocess.run(cmd, capture_output=True)
print('RC:', r.returncode)
if r.returncode != 0:
    print('ERR:', r.stderr.decode('utf-8', errors='replace')[-400:])
else:
    print('SUCCESS! Size:', os.path.getsize(out) // 1024, 'KB')
