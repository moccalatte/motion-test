import os
import json
import math
import subprocess
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

FPS = 30
WIDTH = 1080
HEIGHT = 1920

# Load fonts
FONT_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT_REGULAR = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"

def load_font(path, size):
    try:
        return ImageFont.truetype(path, size)
    except Exception:
        return ImageFont.load_default()

font_title = load_font(FONT_BOLD, 36)
font_badge = load_font(FONT_BOLD, 28)
font_sub = load_font(FONT_BOLD, 38)
font_sub_small = load_font(FONT_BOLD, 24)

# Load Character frames
char_idle = Image.open("asset/character_idle.png").convert("RGBA")
char_talk = Image.open("asset/character_talk.png").convert("RGBA")

# Load scenes metadata
with open("asset/scenes.json", "r", encoding="utf-8") as f:
    scenes_data = json.load(f)

# Preload backgrounds
bgs = {
    "scene1": Image.open("asset/bg_scene1.jpg").convert("RGBA"),
    "scene2": Image.open("asset/bg_scene2.jpg").convert("RGBA"),
    "scene3": Image.open("asset/bg_scene3.jpg").convert("RGBA"),
    "scene4": Image.open("asset/bg_scene4.jpg").convert("RGBA"),
    "scene5": Image.open("asset/bg_scene5.jpg").convert("RGBA"),
}

def render_frame(scene_idx, frame_in_scene, total_scene_frames):
    scene = scenes_data[scene_idx]
    bg_orig = bgs[scene["id"]]
    time_sec = frame_in_scene / FPS
    progress = frame_in_scene / total_scene_frames

    # 1. Background Camera Motion (Zoom & Pan)
    zoom_scale = 1.0 + 0.08 * progress
    crop_w = int(WIDTH / zoom_scale)
    crop_h = int(HEIGHT / zoom_scale)
    crop_x = int((WIDTH - crop_w) / 2)
    crop_y = int((HEIGHT - crop_h) * (0.3 + 0.4 * progress))

    bg_cropped = bg_orig.crop((crop_x, crop_y, crop_x + crop_w, crop_y + crop_h))
    frame_img = bg_cropped.resize((WIDTH, HEIGHT), Image.Resampling.BILINEAR)

    # 2. Dynamic Floating Particles / Smoke Orbs
    overlay_effects = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    eff_draw = ImageDraw.Draw(overlay_effects)
    for p in range(25):
        seed_x = (p * 149 + scene_idx * 311) % WIDTH
        seed_speed = 35 + (p * 17) % 55
        p_y = (HEIGHT - int(time_sec * seed_speed * 12 + p * 97)) % (HEIGHT + 100) - 50
        p_x = (seed_x + int(math.sin(time_sec * 2 + p) * 30)) % WIDTH
        p_rad = 12 + (p * 5) % 25
        if scene_idx in [0, 1, 2]: # Fire embers / red ash
            eff_draw.ellipse([p_x - p_rad, p_y - p_rad, p_x + p_rad, p_y + p_rad], fill=(255, 140, 30, 45))
        elif scene_idx == 3: # Dense grey toxic haze
            eff_draw.ellipse([p_x - p_rad*2, p_y - p_rad*2, p_x + p_rad*2, p_y + p_rad*2], fill=(200, 180, 160, 35))
        else: # Scene 5 lush green spores / sunlight
            eff_draw.ellipse([p_x - p_rad, p_y - p_rad, p_x + p_rad, p_y + p_rad], fill=(180, 255, 180, 40))

    frame_img.alpha_composite(overlay_effects)

    # 3. Top Banner / Header (TikTok Style Topic Banner)
    hud = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    hud_draw = ImageDraw.Draw(hud)

    # Topic Badge
    badge_text = "EDUKASI BENCANA ALAM"
    badge_bbox = hud_draw.textbbox((0, 0), badge_text, font=font_badge)
    badge_w = badge_bbox[2] - badge_bbox[0]
    hud_draw.rounded_rectangle([70, 140, 70 + badge_w + 50, 205], radius=18, fill=(220, 38, 38, 235), outline=(255, 255, 255, 220), width=2)
    hud_draw.text((95, 155), badge_text, fill=(255, 255, 255, 255), font=font_badge)

    # Main Scene Title Banner (Dynamic width & centered or padded)
    title_text = scene["title"].upper()
    title_bbox = hud_draw.textbbox((0, 0), title_text, font=font_title)
    title_w = title_bbox[2] - title_bbox[0]
    box_w = max(title_w + 60, WIDTH - 140)
    hud_draw.rounded_rectangle([70, 225, 70 + title_w + 60, 315], radius=22, fill=(15, 15, 20, 225), outline=(255, 200, 50, 200), width=3)
    hud_draw.text((100, 247), title_text, fill=(255, 235, 80, 255), font=font_title)

    # Scene Specific Infographics
    info_map = {
        1: ("ZONA MERAH: RIAU & KALTENG", (255, 120, 60, 255), (255, 90, 40, 220)),
        2: ("KEDALAMAN API: HINGGA 4 METER", (255, 80, 80, 255), (255, 50, 50, 220)),
        3: ("DARURAT KESEHATAN ISPA PM2.5", (255, 220, 60, 255), (230, 180, 40, 220)),
        4: ("JAGA HUTAN, JAGA MASA DEPAN", (100, 255, 140, 255), (50, 220, 100, 220))
    }
    if scene_idx in info_map:
        info_text, text_col, border_col = info_map[scene_idx]
        ibbox = hud_draw.textbbox((0, 0), info_text, font=font_badge)
        iw = ibbox[2] - ibbox[0]
        hud_draw.rounded_rectangle([70, 335, 70 + iw + 50, 405], radius=16, fill=(25, 25, 35, 225), outline=border_col, width=2)
        hud_draw.text((95, 352), info_text, fill=text_col, font=font_badge)

    frame_img.alpha_composite(hud)

    # 4. Animated Storyteller Character
    # Storyteller bobs up and down with breathing
    bob_y = int(math.sin(time_sec * 4.5) * 8)
    char_base_y = 1040 + bob_y
    char_base_x = WIDTH - 470 # Positioned on bottom right

    # Storyteller talks: alternate frames every 4-6 frames while speech is ongoing
    is_talking = (frame_in_scene % 10) < 6
    cur_char = char_talk if is_talking else char_idle

    # Scale character slightly for TikTok view
    scaled_w, scaled_h = 490, 665
    char_resized = cur_char.resize((scaled_w, scaled_h), Image.Resampling.BILINEAR)

    # Character speech tag (Storyteller Name)
    char_tag = Image.new("RGBA", (scaled_w, scaled_h + 100), (0, 0, 0, 0))
    char_tag.alpha_composite(char_resized, (0, 60))
    ct_draw = ImageDraw.Draw(char_tag)
    tag_label = "STORYTELLER"
    t_bbox = ct_draw.textbbox((0, 0), tag_label, font=font_badge)
    tw = t_bbox[2] - t_bbox[0]
    ct_draw.rounded_rectangle([135, 10, 135 + tw + 40, 65], radius=15, fill=(18, 22, 28, 235), outline=(59, 130, 246, 230), width=2)
    ct_draw.text((155, 22), tag_label, fill=(147, 197, 253, 255), font=font_badge)

    frame_img.alpha_composite(char_tag, (char_base_x, char_base_y - 60))

    # 5. TikTok Style Dynamic Subtitles (Active Word Highlight + Bounding Box)
    # Determine active word based on time_sec
    words = scene["words"]
    active_idx = 0
    for w_idx, w_data in enumerate(words):
        if w_data["start"] <= time_sec <= w_data["end"]:
            active_idx = w_idx
            break
        elif time_sec > w_data["end"]:
            active_idx = w_idx

    # Display 4 words per subtitle chunk centered on active word to prevent overflow
    chunk_size = 4
    start_chunk = (active_idx // chunk_size) * chunk_size
    end_chunk = min(start_chunk + chunk_size, len(words))
    sub_chunk_words = words[start_chunk:end_chunk]

    sub_canvas = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    sub_draw = ImageDraw.Draw(sub_canvas)

    # Subtitle container card
    box_y1 = 1550
    box_y2 = 1770
    sub_draw.rounded_rectangle([50, box_y1, WIDTH - 50, box_y2], radius=28, fill=(10, 10, 14, 240), outline=(255, 255, 255, 80), width=3)

    # Subtitle words layout
    sub_draw.text((80, box_y1 + 35), "NARASI:", fill=(160, 175, 190, 255), font=font_sub_small)

    # Word by word render with active word highlighted in bold neon yellow
    curr_x = 80
    curr_y = box_y1 + 95
    for w_obj in sub_chunk_words:
        w_text = w_obj["word"]
        is_active = (w_obj["word"] == words[active_idx]["word"] and w_obj["start"] <= time_sec <= w_obj["end"] + 0.1)

        # Measure text width
        bbox = sub_draw.textbbox((curr_x, curr_y), w_text + " ", font=font_sub)
        w_w = bbox[2] - bbox[0]

        if is_active:
            # Active word background glow & yellow color
            sub_draw.rounded_rectangle([curr_x - 6, curr_y - 6, curr_x + w_w - 4, curr_y + 50], radius=10, fill=(250, 204, 21, 240))
            sub_draw.text((curr_x, curr_y), w_text + " ", fill=(15, 23, 42, 255), font=font_sub)
        else:
            sub_draw.text((curr_x, curr_y), w_text + " ", fill=(255, 255, 255, 255), font=font_sub)

        curr_x += w_w

    frame_img.alpha_composite(sub_canvas)

    # Convert to RGB numpy array for OpenCV
    return cv2.cvtColor(np.array(frame_img.convert("RGB")), cv2.COLOR_RGB2BGR)

def main():
    print("Starting TikTok 9:16 Video Synthesis...")
    os.makedirs("asset", exist_ok=True)
    temp_video = "asset/temp_video.mp4"
    final_output = "asset/karhutla_tiktok.mp4"

    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    out = cv2.VideoWriter(temp_video, fourcc, FPS, (WIDTH, HEIGHT))

    total_frames = sum([sc["durationFrames"] for sc in scenes_data])
    frame_counter = 0

    for sc_idx, sc in enumerate(scenes_data):
        sc_frames = sc["durationFrames"]
        print(f"Rendering {sc['id']} ({sc_frames} frames)...")
        for f in range(sc_frames):
            frame = render_frame(sc_idx, f, sc_frames)
            out.write(frame)
            frame_counter += 1
            if frame_counter % 90 == 0:
                print(f"  Frame {frame_counter}/{total_frames} ({(frame_counter/total_frames)*100:.1f}%)")

    out.release()
    print("Video track rendered! Concatenating scene audios...")

    # Combine voiceovers
    concat_list = "asset/audio_list.txt"
    with open(concat_list, "w") as f:
        for sc in scenes_data:
            f.write(f"file '{sc['id']}.wav'\n")

    combined_voice = "asset/combined_voice.wav"
    subprocess.run([
        "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", concat_list,
        "-c", "copy", combined_voice
    ], check=True)

    # Mux video, voiceover, and ambient fire background track
    print("Muxing final video with audio & ambient sound...")
    cmd = [
        "ffmpeg", "-y",
        "-i", temp_video,
        "-i", combined_voice,
        "-i", "asset/ambient_fire.wav",
        "-filter_complex",
        "[1:a]volume=1.0[voice];[2:a]volume=0.18[ambient];[voice][ambient]amix=inputs=2:duration=first[aout]",
        "-map", "0:v:0",
        "-map", "[aout]",
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-b:a", "192k",
        "-shortest",
        final_output
    ]
    subprocess.run(cmd, check=True)

    # Clean up temp files
    if os.path.exists(temp_video):
        os.remove(temp_video)
    if os.path.exists(concat_list):
        os.remove(concat_list)

    print(f"\nSUCCESS! Final TikTok video generated at: {final_output}")

if __name__ == "__main__":
    main()
