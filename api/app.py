import os
import time
import requests
from flask import Flask, request, send_file, jsonify, send_from_directory, Response
from flask_cors import CORS
from moviepy.editor import VideoFileClip
from urllib.parse import quote_plus
os.environ["IMAGEIO_FFMPEG_EXE"] = "/usr/bin/ffmpeg"

app = Flask(__name__)
CORS(app)

NEX_BASE = "https://api.nexray.web.id"
TEMP_DIR = "/tmp"

@app.route('/')
def index():
    return "X17 ULTRA ENGINE V14 - SIPUTX + NEXRAY HYBRID 🚀"

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

@app.route('/proxy_siput', methods=['POST'])
def proxy_siput():
    """
    Frontend sudah panggil SiputX dan dapat response.
    Frontend parse sendiri, kirim ke sini dalam format:
    {
        "url": "https://...",
        "title": "...",
        "thumbnail": "https://...",
        "type": "MP4" / "MP3"
    }
    Backend cukup validate dan return balik — atau bisa
    dipakai sebagai titik untuk nge-proxy download nanti.
    """
    try:
        data = request.json
        url       = data.get('url', '').strip()
        title     = data.get('title', 'Instagram Story').strip()
        thumbnail = data.get('thumbnail', '').strip()
        file_type = data.get('type', 'MP4').upper()

        if not url:
            return jsonify({'success': False, 'error': 'URL kosong'}), 400

        return jsonify({
            'success':   True,
            'title':     title if title else 'Instagram Story',
            'thumbnail': thumbnail,
            'url':       url,
            'type':      file_type,
            'platform':  'SiputX-Story'
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/ig_story', methods=['POST'])
def ig_story():
    """
    Download Instagram Story via SiputZX dari sisi server (bypass CORS).
    Frontend kirim: { "url": "https://instagram.com/stories/...", "mode": "mp4" }
    """
    try:
        data = request.json
        story_url = data.get('url', '').strip()
        mode      = data.get('mode', 'mp4').lower()

        if not story_url:
            return jsonify({'success': False, 'error': 'URL kosong'}), 400

        # Tembak SiputZX dari server (tidak ada CORS di server-side)
        encoded  = requests.utils.quote(story_url, safe='')
        endpoint = f"https://app.siputzx.my.id/api/d/igram?url={encoded}"

        headers = {
            'Accept':          'application/json, text/plain, */*',
            'Referer':         'https://app.siputzx.my.id/',
            'Origin':          'https://app.siputzx.my.id',
            'User-Agent':      'Mozilla/5.0 (Linux; Android 12; Pixel 6) AppleWebKit/537.36 Chrome/120 Mobile Safari/537.36',
        }

        r = requests.get(endpoint, headers=headers, timeout=30)

        # Cek apakah response benar-benar JSON
        content_type = r.headers.get('Content-Type', '')
        if 'html' in content_type or r.text.strip().startswith('<!'):
            return jsonify({'success': False, 'error': 'SiputZX mengembalikan HTML, bukan JSON. Coba lagi.'}), 502

        res = r.json()

        if not res.get('status'):
            return jsonify({'success': False, 'error': res.get('message', 'Story tidak tersedia atau private')}), 400

        # ── Parse struktur response SiputZX igram ──────────────────
        # res['data']['url']  → list dict {url, name, type, ext, quality}
        # res['data']['thumb'] → thumbnail URL
        # res['data']['meta']  → {title, username, source, ...}
        # ───────────────────────────────────────────────────────────

        siput_data = res.get('data', {})
        url_list   = siput_data.get('url', [])
        meta       = siput_data.get('meta', {})
        thumbnail  = siput_data.get('thumb', '')

        # Judul
        title = ''
        if isinstance(meta, dict):
            title = meta.get('title', '')
            if not title:
                username = meta.get('username', '')
                title = f"Instagram Story @{username}" if username else "Instagram Story"

        # Pilih URL terbaik
        final_url = ''
        valid_urls = [x for x in url_list if x and x.get('url')]

        if mode == 'mp3':
            # Cari audio dulu, kalau gak ada fallback ke video
            audio = next((x for x in valid_urls if x.get('type') == 'audio' or 'audio' in (x.get('name') or '').lower()), None)
            final_url = audio['url'] if audio else (valid_urls[0]['url'] if valid_urls else '')
        else:
            # Pilih kualitas tertinggi (sort by quality desc)
            sorted_urls = sorted(valid_urls, key=lambda x: x.get('quality', 0), reverse=True)
            final_url   = sorted_urls[0]['url'] if sorted_urls else ''

        if not final_url:
            return jsonify({'success': False, 'error': 'Tidak ada URL video di response SiputZX'}), 400

        return jsonify({
            'success':   True,
            'title':     title,
            'thumbnail': thumbnail,
            'url':       final_url,
            'type':      mode.upper(),
            'platform':  'Instagram-Story'
        })

    except requests.exceptions.Timeout:
        return jsonify({'success': False, 'error': 'SiputZX timeout, coba lagi'}), 504
    except requests.exceptions.JSONDecodeError:
        return jsonify({'success': False, 'error': 'SiputZX return bukan JSON (mungkin sedang maintenance)'}), 502
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/get_video', methods=['POST'])
def get_video():
    try:
        data = request.json
        url  = data.get('url', '')
        mode = data.get('mode', 'mp4')
        u    = url.lower()

        # ── Deteksi Instagram Story → suruh frontend handle ──────
        if "instagram.com/stories/" in u:
            return jsonify({
                'success': False,
                'error': 'USE_FRONTEND_SIPUTX',
                'message': 'Instagram Story harus diproses dari frontend langsung ke SiputX'
            }), 400

        # ── Platform routing ─────────────────────────────────────
        if any(x in u for x in ["youtube.com", "youtu.be"]):
            endpoint = f"{NEX_BASE}/downloader/v1/ytmp3" if mode == "mp3" else f"{NEX_BASE}/downloader/v1/ytmp4"
            params   = {"url": url, "resolusi": "1080"}

        elif "facebook.com" in u or "fb.watch" in u:
            endpoint = f"{NEX_BASE}/downloader/facebook"
            params   = {"url": url}

        elif "instagram.com" in u:
            endpoint = f"{NEX_BASE}/downloader/v2/instagram"
            params   = {"url": url}

        elif "tiktok.com" in u:
            endpoint = f"{NEX_BASE}/downloader/tiktok"
            params   = {"url": url}

        elif "douyin.com" in u:
            endpoint = f"{NEX_BASE}/downloader/v1/douyin"
            params   = {"url": url}

        elif "spotify.com" in u:
            endpoint = f"{NEX_BASE}/downloader/spotify"
            params   = {"url": url}

        elif "pinterest.com" in u or "pin.it" in u:
            endpoint = f"{NEX_BASE}/downloader/pinterest"
            params   = {"url": url}

        elif "scribd.com" in u:
            endpoint = f"{NEX_BASE}/downloader/scribd"
            params   = {"url": url}

        elif "twitter.com" in u or "x.com" in u:
            endpoint = f"{NEX_BASE}/downloader/twitter"
            params   = {"url": url}

        elif "videy.co" in u:
            endpoint = f"{NEX_BASE}/downloader/videy"
            params   = {"url": url}

        else:
            endpoint = f"{NEX_BASE}/downloader/aio"
            params   = {"url": url}

        r   = requests.get(endpoint, params=params, timeout=30)
        res = r.json()

        if not res.get('status'):
            return jsonify({'success': False, 'error': res.get('message', 'API NexRay gagal')}), 400

        result    = res.get('result', {})
        final_url = None
        title     = result.get('title') or "X17 Downloader Result"
        thumb     = result.get('thumbnail') or result.get('cover') or ''

        if mode == "mp3":
            if "music_info" in result:
                final_url = result["music_info"].get("url")
            elif "audio" in result:
                final_url = result.get("audio")
            elif "url" in result:
                final_url = result.get("url")
            else:
                final_url = result.get("video")
        else:
            if "video_hd" in result:
                final_url = result.get("video_hd")
            elif "media" in result and isinstance(result["media"], list) and result["media"]:
                final_url = result["media"][0].get("url")
            elif "data" in result:
                final_url = result.get("data")
            elif "url" in result:
                final_url = result.get("url")
            else:
                final_url = result.get("video")

        if not final_url:
            return jsonify({'success': False, 'error': 'Link tidak ditemukan di response API'}), 400

        return jsonify({
            'success':   True,
            'title':     title,
            'thumbnail': thumb,
            'url':       final_url,
            'type':      mode.upper(),
            'platform':  endpoint.split('/')[-1]
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/get_transcript', methods=['POST'])
def get_transcript():
    try:
        data   = request.json
        yt_url = data.get('url', '')
        api_url = f"https://x.0cd.fun/tools/transcript/youtube?url={yt_url}"
        response = requests.get(api_url, timeout=30)
        return jsonify(response.json())
    except:
        return jsonify({"status": False})


@app.route('/search_yt', methods=['GET'])
def search_youtube():
    query = request.args.get('query', '')
    if not query:
        return jsonify({"status": False, "message": "Query pencarian kosong!"})
    try:
        url      = f"https://x.0cd.fun/search/youtube?query={query}"
        response = requests.get(url, timeout=15)
        if response.status_code == 200:
            return jsonify(response.json())
        else:
            return jsonify({"status": False, "message": "API YouTube sedang sibuk."})
    except Exception as e:
        return jsonify({"status": False, "message": str(e)})


@app.route('/convert', methods=['POST'])
def convert():
    ts     = str(int(time.time()))
    v_path = os.path.join(TEMP_DIR, f"v_{ts}.mp4")
    a_path = os.path.join(TEMP_DIR, f"a_{ts}.mp3")
    try:
        f = request.files['file']
        f.save(v_path)
        with VideoFileClip(v_path) as clip:
            clip.audio.write_audiofile(a_path, codec='libmp3lame', logger=None)
        return send_file(a_path, as_attachment=True, download_name="X17_Converted.mp3")
    except Exception as e:
        return f"Error: {str(e)}", 500
    finally:
        if os.path.exists(v_path): os.remove(v_path)


@app.route('/wallpapers/<path:filename>')
def serve_wallpaper(filename):
    return send_from_directory(os.getcwd(), filename)


app = app = app
