import os
import time
import requests
from flask import Flask, request, send_file, jsonify, send_from_directory
from flask_cors import CORS
from moviepy.editor import VideoFileClip
os.environ["IMAGEIO_FFMPEG_EXE"] = "/usr/bin/ffmpeg" 

app = Flask(__name__)
CORS(app)

# Base URL API NexRay
NEX_BASE = "https://api.nexray.web.id"
TEMP_DIR = "/tmp"

@app.route('/')
def index():
    return "X17 ULTRA ENGINE V12 - 11 PLATFORMS ACTIVE"

@app.route('/chat_ai', methods=['POST'])
def chat_ai():
    try:
        data = request.json
        user_msg = data.get('message', '')
        api_url = f"{NEX_BASE}/ai/gemini"
        response = requests.get(api_url, params={"text": user_msg}, timeout=20)
        res_json = response.json()
        return jsonify({"success": True, "reply": res_json.get("result")})
    except:
        return jsonify({"success": False, "reply": "AI Offline."})

@app.route('/get_video', methods=['POST'])
def get_video():
    try:
        data = request.json
        url = data.get('url', '')
        mode = data.get('mode', 'mp4') # 'mp4' atau 'mp3'
        u = url.lower()

        # --- MAPPING 11 API NEXRAY ---
        if any(x in u for x in ["youtube.com", "youtu.be"]):
            # Khusus YT ada endpoint v1 terpisah buat mp3/mp4
            endpoint = f"{NEX_BASE}/downloader/v1/ytmp3" if mode == "mp3" else f"{NEX_BASE}/downloader/v1/ytmp4"
            params = {"url": url, "resolusi": "1080"} # Default 1080p for YT Video
        elif "facebook.com" in u or "fb.watch" in u:
            endpoint = f"{NEX_BASE}/downloader/facebook"
            params = {"url": url}
        elif "instagram.com" in u:
            endpoint = f"{NEX_BASE}/downloader/v2/instagram"
            params = {"url": url}
        elif "tiktok.com" in u:
            endpoint = f"{NEX_BASE}/downloader/tiktok"
            params = {"url": url}
        elif "douyin.com" in u:
            endpoint = f"{NEX_BASE}/downloader/v1/douyin"
            params = {"url": url}
        elif "spotify.com" in u:
            endpoint = f"{NEX_BASE}/downloader/spotify"
            params = {"url": url}
        elif "pinterest.com" in u or "pin.it" in u:
            endpoint = f"{NEX_BASE}/downloader/pinterest"
            params = {"url": url}
        elif "scribd.com" in u:
            endpoint = f"{NEX_BASE}/downloader/scribd"
            params = {"url": url}
        elif "twitter.com" in u or "x.com" in u:
            endpoint = f"{NEX_BASE}/downloader/twitter"
            params = {"url": url}
        elif "videy.co" in u:
            endpoint = f"{NEX_BASE}/downloader/videy"
            params = {"url": url}
        else:
            # All-in-one fallback
            endpoint = f"{NEX_BASE}/downloader/v1/aio"
            params = {"url": url}

        r = requests.get(endpoint, params=params, timeout=30)
        res = r.json()

        if not res.get('status'):
            return jsonify({'success': False, 'error': 'API NexRay gagal merespon'}), 400

        result = res.get('result')
        final_url = None
        title = result.get('title') or "X17 Downloader Result"
        thumb = result.get('thumbnail') or result.get('cover') or 'https://api.nexray.web.id/favicon.ico'

        # --- LOGIKA EKSTRAKSI LINK (Sesuai Respon JSON lo) ---
        if mode == "mp3":
            if "music_info" in result: # TikTok Audio
                final_url = result["music_info"].get("url")
            elif "audio" in result: # Facebook / YT MP3 v1
                final_url = result.get("audio")
            elif "url" in result and ("spotify" in u or "ytmp3" in endpoint): # Spotify / YT MP3
                final_url = result.get("url")
            else:
                # Jika mode mp3 dipilih tapi link audio ga ketemu, kasih url utama
                final_url = result.get("url")
        else:
            # Mode MP4 / Video / File
            if "video_hd" in result: # Facebook HD
                final_url = result.get("video_hd")
            elif "media" in result and isinstance(result["media"], list): # Instagram
                final_url = result["media"][0].get("url")
            elif "data" in result and "tiktok" in u: # TikTok Video
                final_url = result.get("data")
            else:
                final_url = result.get("url") or result.get("video")

        return jsonify({
            'success': True,
            'title': title,
            'thumbnail': thumb,
            'url': final_url,
            'type': mode.upper(),
            'platform': endpoint.split('/')[-1]
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
        
@app.route('/get_transcript', methods=['POST'])
def get_transcript():
    try:
        data = request.json
        yt_url = data.get('url', '')
        api_url = f"https://x.0cd.fun/tools/transcript/youtube?url={yt_url}"
        response = requests.get(api_url, timeout=30)
        return jsonify(response.json())
    except:
        return jsonify({"status": False})

# --- ROUTER YOUTUBE SEARCH ---
@app.route('/search_yt', methods=['GET'])
def search_youtube():
    # Ambil parameter ?query= dari URL
    query = request.args.get('query', '')
    
    if not query:
        return jsonify({"status": False, "message": "Query pencarian kosong!"})
        
    try:
        # Tembak API eksternal
        url = f"https://x.0cd.fun/search/youtube?query={query}"
        response = requests.get(url, timeout=15)
        
        if response.status_code == 200:
            return jsonify(response.json())
        else:
            return jsonify({"status": False, "message": "API YouTube sedang sibuk."})
            
    except Exception as e:
        return jsonify({"status": False, "message": str(e)})
                           

@app.route('/convert', methods=['POST'])
def convert():
    ts = str(int(time.time()))
    v_path = os.path.join(TEMP_DIR, f"v_{ts}.mp4")
    a_path = os.path.join(TEMP_DIR, f"a_{ts}.mp3")
    try:
        f = request.files['file']
        f.save(v_path)
        with VideoFileClip(v_path) as clip:
            clip.audio.write_audiofile(a_path, codec='libmp3lame', logger=None)
        return send_file(a_path, as_attachment=True, download_name="X17_Converted.mp3")
    except Exception as e: return f"Error: {str(e)}", 500
    finally:
        if os.path.exists(v_path): os.remove(v_path)

@app.route('/wallpapers/<path:filename>')
def serve_wallpaper(filename):
    return send_from_directory(os.getcwd(), filename)

# Ganti bagian paling bawah (hapus if __name__ == '__main__')
# Cukup sisakan baris ini saja di paling bawah:
app = app 
