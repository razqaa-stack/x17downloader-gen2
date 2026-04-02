import os
import time
import requests
from flask import Flask, request, send_file, jsonify, send_from_directory
from flask_cors import CORS
from moviepy.editor import VideoFileClip
os.environ["IMAGEIO_FFMPEG_EXE"] = "/usr/bin/ffmpeg" 

app = Flask(__name__)
CORS(app)

TEMP_DIR = "/tmp"

@app.route('/')
def index():
    return "X17 ULTRA ENGINE V11 - LIVE ON RENDER"

# --- ROUTER AI GEMINI ---
@app.route('/chat_ai', methods=['POST'])
def chat_ai():
    try:
        data = request.json
        user_msg = data.get('message', '')
        if not user_msg:
            return jsonify({"success": False, "reply": "Pesan kosong nih!"})

        api_url = "https://x.0cd.fun/ai/model/gemini-3-flash"
        params = {
            "prompt": user_msg,
            "systemPrompt": "Jawab dengan Bahasa Indonesia. Singkat, padat, dan keren.",
            "sessionId": "XDOWNLOADER_AIGEMINIV4"
        }
        response = requests.get(api_url, params=params, timeout=30)
        res_json = response.json()
        return jsonify({"success": True, "reply": res_json['data']['text']})
    except Exception as e:
        return jsonify({"success": False, "reply": "AI lagi sibuk, coba lagi nanti."})

# --- ROUTER DOWNLOADER ---
@app.route('/get_video', methods=['POST'])
def get_video():
    try:
        data = request.json
        url = data.get('url', '')
        mode = data.get('mode', 'mp4')
        u = url.lower()

        if any(x in u for x in ["twitter.com", "x.com"]):
            p = "twitter"
        elif "instagram.com" in u:
            p = "instagram"
        elif any(x in u for x in ["tiktok.com", "vt.tiktok", "vm.tiktok"]):
            p = "tiktok"
        elif "v.douyin.com" in u:
            p = "douyin"
        elif any(x in u for x in ["facebook.com", "fb.watch"]):
            p = "facebook"
        elif "pin.it" in u or "pinterest.com" in u:
            p = "pinterest"
        elif "open.spotify.com" in u:
            p = "spotify"
        elif any(x in u for x in ["youtube.com", "youtu.be"]):
            p = "youtube"
        else:
            return jsonify({'success': False, 'error': 'Platform tidak didukung'}), 400

        BASE = "https://lol.cyvera.me"
        params = {"url": url}

        if p == "youtube":
            params["type"] = "mp3" if mode == "mp3" else "video"
            params["quality"] = "128kbps" if mode == "mp3" else "720p"
            api_url = f"{BASE}/yt"
        else:
            api_url = f"{BASE}/{p}"

        response = requests.get(api_url, params=params, timeout=30)
        res_data = response.json()

        if not res_data.get('status'):
            return jsonify({'success': False, 'error': 'API Gagal'}), 400

        d = res_data.get('result', {})

        if p == "tiktok":
            final_url = d.get('video')
        elif p == "youtube":
            final_url = d.get('url')
        elif p == "facebook":
            final_url = d.get('url')
        elif p == "spotify":
            final_url = d.get('url')
        elif p == "pinterest":
            media = d.get('media', [])
            final_url = media[0].get('url') if media else None
        elif p in ["instagram", "twitter"]:
            final_url = d[0].get('url') if isinstance(d, list) and d else None
        elif p == "douyin":
            final_url = d.get('video')
        else:
            final_url = None

        if not final_url:
            return jsonify({'success': False, 'error': 'Gagal ambil link'}), 404

        return jsonify({
            'success': True,
            'title': d.get('title', 'Result'),
            'thumbnail': d.get('thumbnail') or 'https://placehold.co/600x400',
            'url': final_url,
            'type': mode,
            'quality': 'HD',
            'platform': p
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
