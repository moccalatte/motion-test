import os
import json
import asyncio
import subprocess
import wave
import struct
import math
import random
from PIL import Image, ImageDraw, ImageFilter
import edge_tts

WIDTH = 1080
HEIGHT = 1920

SCENES = [
    {
        "id": "scene1",
        "title": "Tragedi Karhutla di Indonesia",
        "text": "Pernahkah kalian melihat langit Indonesia berubah menjadi merah pekat karena kabut asap tebal?",
    },
    {
        "id": "scene2",
        "title": "Ancaman Lahan Gambut",
        "text": "Setiap musim kemarau, bencana Karhutla atau Kebakaran Hutan dan Lahan kembali melanda Sumatera dan Kalimantan.",
    },
    {
        "id": "scene3",
        "title": "Bencana di Bawah Tanah",
        "text": "Lahan gambut yang mengering terbakar hingga ke bawah tanah! Api sulit dipadamkan dan jutaan ton karbon terlepas ke atmosfer.",
    },
    {
        "id": "scene4",
        "title": "Dampak Mengerikan Bagi Kehidupan",
        "text": "Bukan hanya satwa langka yang kehilangan habitatnya, ratusan ribu saudara kita terserang ISPA dan aktivitas pun lumpuh total.",
    },
    {
        "id": "scene5",
        "title": "Jaga Hutan Kita Sekarang!",
        "text": "Hutan adalah paru-paru dunia. Jangan biarkan serakah membakar masa depan kita. Lindungi hutan Indonesia sekarang juga!",
    }
]

VOICE = "id-ID-ArdiNeural"

async def generate_speech_assets():
    print("1. Generating voiceover audio...")
    metadata = []
    total_duration = 0.0

    for idx, sc in enumerate(SCENES):
        mp3_path = f"asset/{sc['id']}.mp3"
        wav_path = f"asset/{sc['id']}.wav"
        srt_path = f"asset/{sc['id']}.srt"

        communicate = edge_tts.Communicate(sc["text"], VOICE, rate="+5%")
        submaker = edge_tts.SubMaker()

        with open(mp3_path, "wb") as f:
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    f.write(chunk["data"])
                elif chunk["type"] == "WordBoundary":
                    submaker.feed(chunk)

        with open(srt_path, "w", encoding="utf-8") as f:
            f.write(submaker.get_srt())

        subprocess.run(["ffmpeg", "-y", "-i", mp3_path, wav_path], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", wav_path]
        duration = float(subprocess.check_output(cmd).decode().strip())

        words = sc["text"].split()
        word_dur = duration / len(words)
        timed_words = []
        for widx, w in enumerate(words):
            timed_words.append({
                "word": w,
                "start": round(widx * word_dur, 2),
                "end": round((widx + 1) * word_dur, 2)
            })

        metadata.append({
            "id": sc["id"],
            "title": sc["title"],
            "text": sc["text"],
            "audioFile": f"{sc['id']}.wav",
            "duration": duration,
            "durationFrames": int(round(duration * 30)),
            "words": timed_words
        })
        total_duration += duration
        print(f"   Scene {idx+1} ({sc['id']}): {duration:.2f}s")

    with open("asset/scenes.json", "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)
    print(f"Total audio duration: {total_duration:.2f}s")

def generate_ambient_audio():
    print("2. Generating ambient disaster sound...")
    sample_rate = 44100
    duration = 40.0
    total_samples = int(sample_rate * duration)
    with wave.open("asset/ambient_fire.wav", "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        buf = bytearray()
        random.seed(42)
        for i in range(total_samples):
            t = i / sample_rate
            rumble = 0.2 * math.sin(2 * math.pi * 55 * t) + 0.15 * math.sin(2 * math.pi * 78 * t)
            noise = (random.random() * 2 - 1) * 0.05
            crackle = (random.random() * 0.4) if random.random() > 0.998 else 0
            val = (rumble + noise + crackle) * 0.25
            val = max(-1.0, min(1.0, val))
            sample_val = int(val * 32767)
            buf.extend(struct.pack('<h', sample_val))
        wf.writeframes(buf)

def create_gradient(top_color, bottom_color, width=WIDTH, height=HEIGHT):
    base = Image.new('RGBA', (width, height), top_color)
    top_r, top_g, top_b = top_color[:3]
    bot_r, bot_g, bot_b = bottom_color[:3]
    draw = ImageDraw.Draw(base)
    for y in range(height):
        ratio = y / float(height)
        r = int(top_r + (bot_r - top_r) * ratio)
        g = int(top_g + (bot_g - top_g) * ratio)
        b = int(top_b + (bot_b - top_b) * ratio)
        draw.line([(0, y), (width, y)], fill=(r, g, b, 255))
    return base

def generate_visual_backgrounds():
    print("3. Generating background visuals...")
    # Scene 1: Red Sky / Blood Sun / Forest Fire Smoke
    img1 = create_gradient((20, 2, 4), (180, 40, 15))
    sun = Image.new('RGBA', (WIDTH, HEIGHT), (0,0,0,0))
    s_draw = ImageDraw.Draw(sun)
    s_draw.ellipse([WIDTH//2 - 150, 450, WIDTH//2 + 150, 750], fill=(255, 90, 30, 200))
    sun = sun.filter(ImageFilter.GaussianBlur(40))
    img1.alpha_composite(sun)
    smoke = Image.new('RGBA', (WIDTH, HEIGHT), (0,0,0,0))
    sm_draw = ImageDraw.Draw(smoke)
    for i in range(12):
        cx = 100 + i * 90
        cy = 800 + (i % 4) * 80
        sm_draw.ellipse([cx - 250, cy - 180, cx + 250, cy + 180], fill=(120, 30, 10, 90))
    smoke = smoke.filter(ImageFilter.GaussianBlur(60))
    img1.alpha_composite(smoke)
    tree_layer = Image.new('RGBA', (WIDTH, HEIGHT), (0,0,0,0))
    t_draw = ImageDraw.Draw(tree_layer)
    for x in range(0, WIDTH + 60, 45):
        h = 550 + (x * 37) % 350
        t_draw.line([(x, HEIGHT), (x, HEIGHT - h)], fill=(35, 8, 8, 220), width=18)
    for x in range(-20, WIDTH + 80, 85):
        h = 750 + (x * 53) % 400
        t_draw.line([(x, HEIGHT), (x, HEIGHT - h)], fill=(15, 3, 3, 255), width=28)
    t_draw.rectangle([0, HEIGHT - 350, WIDTH, HEIGHT], fill=(10, 2, 2, 255))
    img1.alpha_composite(tree_layer)
    glow = Image.new('RGBA', (WIDTH, HEIGHT), (0,0,0,0))
    g_draw = ImageDraw.Draw(glow)
    g_draw.rectangle([0, HEIGHT - 320, WIDTH, HEIGHT], fill=(240, 90, 10, 130))
    glow = glow.filter(ImageFilter.GaussianBlur(50))
    img1.alpha_composite(glow)
    img1.convert('RGB').save('asset/bg_scene1.jpg', quality=95)

    # Scene 2: Indonesia Map & Fire Hotspots
    img2 = create_gradient((10, 15, 25), (35, 20, 20))
    grid = Image.new('RGBA', (WIDTH, HEIGHT), (0,0,0,0))
    gr_draw = ImageDraw.Draw(grid)
    for y in range(200, 1500, 80):
        gr_draw.line([(0, y), (WIDTH, y)], fill=(255, 255, 255, 15), width=1)
    for x in range(0, WIDTH, 80):
        gr_draw.line([(x, 200), (x, 1500)], fill=(255, 255, 255, 15), width=1)
    img2.alpha_composite(grid)
    map_layer = Image.new('RGBA', (WIDTH, HEIGHT), (0,0,0,0))
    m_draw = ImageDraw.Draw(map_layer)
    sumatera = [(150, 680), (220, 600), (320, 720), (390, 880), (360, 950), (280, 920), (200, 820), (140, 710)]
    m_draw.polygon(sumatera, fill=(40, 70, 50, 220), outline=(80, 180, 100, 240))
    kalimantan = [(410, 660), (510, 600), (600, 630), (630, 730), (580, 830), (460, 820), (400, 740)]
    m_draw.polygon(kalimantan, fill=(40, 70, 50, 220), outline=(80, 180, 100, 240))
    jawa = [(340, 990), (480, 990), (620, 1010), (610, 1030), (450, 1030), (330, 1010)]
    m_draw.polygon(jawa, fill=(35, 55, 45, 180), outline=(60, 120, 80, 200))
    sulawesi = [(680, 670), (740, 690), (720, 760), (760, 820), (730, 850), (690, 770), (660, 720)]
    m_draw.polygon(sulawesi, fill=(35, 55, 45, 180), outline=(60, 120, 80, 200))
    img2.alpha_composite(map_layer)
    hotspots = Image.new('RGBA', (WIDTH, HEIGHT), (0,0,0,0))
    h_draw = ImageDraw.Draw(hotspots)
    points = [
        (260, 720, 45), (310, 770, 60), (340, 830, 55), (280, 790, 40),
        (460, 730, 65), (510, 760, 70), (550, 780, 60), (480, 680, 50), (570, 720, 45)
    ]
    for hx, hy, r in points:
        h_draw.ellipse([hx - r, hy - r, hx + r, hy + r], fill=(255, 60, 10, 170))
        h_draw.ellipse([hx - r//2, hy - r//2, hx + r//2, hy + r//2], fill=(255, 230, 50, 220))
    hotspots_blur = hotspots.filter(ImageFilter.GaussianBlur(15))
    img2.alpha_composite(hotspots_blur)
    img2.alpha_composite(hotspots)
    img2.convert('RGB').save('asset/bg_scene2.jpg', quality=95)

    # Scene 3: Peatland Underground Burning
    img3 = create_gradient((30, 15, 10), (12, 6, 4))
    surface_y = 700
    fire_under = Image.new('RGBA', (WIDTH, HEIGHT), (0,0,0,0))
    fu_draw = ImageDraw.Draw(fire_under)
    for y in range(surface_y + 80, HEIGHT - 200, 120):
        for x in range(80, WIDTH - 80, 140):
            r = 70 + (x * 7 + y) % 60
            fu_draw.ellipse([x - r, y - r//2, x + r, y + r//2], fill=(230, 60, 10, 120))
            fu_draw.ellipse([x - r//2, y - r//4, x + r//2, y + r//4], fill=(255, 180, 20, 160))
    fire_under = fire_under.filter(ImageFilter.GaussianBlur(35))
    img3.alpha_composite(fire_under)
    peat = Image.new('RGBA', (WIDTH, HEIGHT), (0,0,0,0))
    p_draw = ImageDraw.Draw(peat)
    p_draw.rectangle([0, surface_y, WIDTH, HEIGHT], fill=(25, 12, 8, 210))
    for i in range(15):
        sx = 100 + i * 65
        p_draw.line([(sx, surface_y), (sx + 20, surface_y + 150), (sx - 15, surface_y + 350), (sx + 30, surface_y + 600)], fill=(255, 120, 20, 200), width=5)
    img3.alpha_composite(peat)
    smoke3 = Image.new('RGBA', (WIDTH, HEIGHT), (0,0,0,0))
    sm_draw3 = ImageDraw.Draw(smoke3)
    for i in range(8):
        sx = 120 + i * 115
        sm_draw3.ellipse([sx - 90, surface_y - 250, sx + 90, surface_y + 30], fill=(200, 180, 170, 75))
    smoke3 = smoke3.filter(ImageFilter.GaussianBlur(40))
    img3.alpha_composite(smoke3)
    img3.convert('RGB').save('asset/bg_scene3.jpg', quality=95)

    # Scene 4: Haze / ISPA Crisis
    img4 = create_gradient((45, 40, 30), (100, 75, 40))
    haze = Image.new('RGBA', (WIDTH, HEIGHT), (0,0,0,0))
    h_draw = ImageDraw.Draw(haze)
    for i in range(25):
        cx = (i * 137) % WIDTH
        cy = (i * 179) % (HEIGHT - 400) + 200
        rad = 220 + (i * 31) % 150
        h_draw.ellipse([cx - rad, cy - rad, cx + rad, cy + rad], fill=(180, 140, 80, 60))
    haze = haze.filter(ImageFilter.GaussianBlur(70))
    img4.alpha_composite(haze)
    wildlife = Image.new('RGBA', (WIDTH, HEIGHT), (0,0,0,0))
    w_draw = ImageDraw.Draw(wildlife)
    w_draw.line([(0, 850), (450, 720), (WIDTH, 790)], fill=(20, 15, 12, 230), width=35)
    w_draw.line([(450, 720), (520, 520)], fill=(20, 15, 12, 230), width=22)
    img4.alpha_composite(wildlife)
    vig = Image.new('RGBA', (WIDTH, HEIGHT), (0,0,0,0))
    v_draw = ImageDraw.Draw(vig)
    v_draw.rectangle([0, 0, WIDTH, HEIGHT], outline=(150, 20, 10, 180), width=40)
    vig = vig.filter(ImageFilter.GaussianBlur(30))
    img4.alpha_composite(vig)
    img4.convert('RGB').save('asset/bg_scene4.jpg', quality=95)

    # Scene 5: Lush Restored Rainforest
    img5 = create_gradient((20, 70, 110), (15, 60, 30))
    sun5 = Image.new('RGBA', (WIDTH, HEIGHT), (0,0,0,0))
    s_draw5 = ImageDraw.Draw(sun5)
    s_draw5.ellipse([WIDTH//2 - 250, 200, WIDTH//2 + 250, 700], fill=(255, 240, 180, 130))
    sun5 = sun5.filter(ImageFilter.GaussianBlur(50))
    img5.alpha_composite(sun5)
    forest = Image.new('RGBA', (WIDTH, HEIGHT), (0,0,0,0))
    f_draw = ImageDraw.Draw(forest)
    for x in range(30, WIDTH, 120):
        th = 1100 + (x * 31) % 300
        f_draw.line([(x, HEIGHT), (x, HEIGHT - th)], fill=(30, 20, 15, 240), width=32)
        f_draw.ellipse([x - 180, HEIGHT - th - 120, x + 180, HEIGHT - th + 180], fill=(35, 140, 60, 240))
        f_draw.ellipse([x - 120, HEIGHT - th - 70, x + 120, HEIGHT - th + 140], fill=(50, 180, 75, 220))
    img5.alpha_composite(forest)
    img5.convert('RGB').save('asset/bg_scene5.jpg', quality=95)

def generate_storyteller(mouth_open=False):
    W, H = 700, 950
    char = Image.new('RGBA', (W, H), (0,0,0,0))
    d = ImageDraw.Draw(char)
    cx, cy = W // 2, 450
    d.polygon([(cx - 140, 650), (cx + 140, 650), (cx + 260, H), (cx - 260, H)], fill=(40, 45, 42, 255))
    d.polygon([(cx - 55, 520), (cx + 55, 520), (cx + 70, 660), (cx - 70, 660)], fill=(215, 160, 125, 255))
    d.polygon([(cx - 70, 640), (cx - 150, 660), (cx - 250, H), (cx - 50, H), (cx - 30, 720)], fill=(65, 80, 55, 255))
    d.polygon([(cx + 70, 640), (cx + 150, 660), (cx + 250, H), (cx + 50, H), (cx + 30, 720)], fill=(65, 80, 55, 255))
    d.rectangle([cx + 90, 720, cx + 130, 735], fill=(220, 20, 20, 255))
    d.rectangle([cx + 90, 735, cx + 130, 750], fill=(245, 245, 245, 255))
    d.rectangle([cx + 89, 719, cx + 131, 751], outline=(30, 30, 30, 255), width=2)
    d.ellipse([cx - 155, cy - 30, cx - 105, cy + 50], fill=(205, 150, 115, 255))
    d.ellipse([cx + 105, cy - 30, cx + 155, cy + 50], fill=(205, 150, 115, 255))
    face_pts = [
        (cx - 120, cy - 110), (cx + 120, cy - 110),
        (cx + 130, cy + 30), (cx + 85, cy + 170),
        (cx, cy + 210),
        (cx - 85, cy + 170), (cx - 130, cy + 30)
    ]
    d.polygon(face_pts, fill=(230, 175, 138, 255))
    hair_pts = [
        (cx - 140, cy - 80), (cx - 150, cy - 160), (cx - 100, cy - 230),
        (cx - 30, cy - 260), (cx + 60, cy - 250), (cx + 130, cy - 210),
        (cx + 150, cy - 130), (cx + 135, cy - 60), (cx + 110, cy - 120),
        (cx + 40, cy - 150), (cx - 40, cy - 150), (cx - 110, cy - 120)
    ]
    d.polygon(hair_pts, fill=(35, 25, 25, 255))
    d.line([(cx - 95, cy - 60), (cx - 30, cy - 75)], fill=(40, 25, 25, 255), width=7)
    d.line([(cx + 95, cy - 60), (cx + 30, cy - 75)], fill=(40, 25, 25, 255), width=7)
    d.ellipse([cx - 85, cy - 40, cx - 35, cy - 10], fill=(255, 255, 255, 255))
    d.ellipse([cx + 35, cy - 40, cx + 85, cy - 10], fill=(255, 255, 255, 255))
    d.ellipse([cx - 68, cy - 38, cx - 48, cy - 14], fill=(55, 35, 25, 255))
    d.ellipse([cx + 48, cy - 38, cx + 68, cy - 14], fill=(55, 35, 25, 255))
    d.ellipse([cx - 62, cy - 34, cx - 56, cy - 26], fill=(255, 255, 255, 255))
    d.ellipse([cx + 54, cy - 34, cx + 60, cy - 26], fill=(255, 255, 255, 255))
    d.line([(cx, cy - 20), (cx - 12, cy + 40), (cx + 8, cy + 42)], fill=(185, 130, 95, 255), width=4)
    if mouth_open:
        d.ellipse([cx - 35, cy + 85, cx + 35, cy + 140], fill=(70, 20, 25, 255), outline=(170, 70, 70, 255), width=3)
        d.arc([cx - 28, cy + 88, cx + 28, cy + 115], start=0, end=180, fill=(245, 245, 245, 255), width=6)
        d.ellipse([cx - 20, cy + 120, cx + 20, cy + 140], fill=(210, 80, 90, 255))
    else:
        d.arc([cx - 32, cy + 85, cx + 32, cy + 115], start=20, end=160, fill=(160, 60, 60, 255), width=6)
        d.line([(cx - 30, cy + 105), (cx + 30, cy + 105)], fill=(130, 50, 50, 255), width=4)
    d.arc([cx - 130, cy - 140, cx + 130, cy + 60], start=170, end=370, fill=(40, 40, 40, 255), width=6)
    d.line([(cx - 120, cy + 30), (cx - 60, cy + 90), (cx - 35, cy + 105)], fill=(20, 20, 20, 255), width=5)
    d.ellipse([cx - 40, cy + 100, cx - 25, cy + 118], fill=(60, 60, 60, 255))
    shadow = Image.new('RGBA', (W, H), (0,0,0,0))
    s_draw = ImageDraw.Draw(shadow)
    s_draw.ellipse([cx - 200, H - 70, cx + 200, H - 10], fill=(0, 0, 0, 100))
    shadow = shadow.filter(ImageFilter.GaussianBlur(15))
    res = Image.new('RGBA', (W, H), (0,0,0,0))
    res.alpha_composite(shadow)
    res.alpha_composite(char)
    return res

async def main():
    await generate_speech_assets()
    generate_ambient_audio()
    generate_visual_backgrounds()
    print("4. Generating storyteller avatar...")
    char_idle = generate_storyteller(mouth_open=False)
    char_idle.save("asset/character_idle.png")
    char_talk = generate_storyteller(mouth_open=True)
    char_talk.save("asset/character_talk.png")
    print("All preparation completed successfully!")

if __name__ == "__main__":
    asyncio.run(main())
