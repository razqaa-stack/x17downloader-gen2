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
    Download Instagram Story dengan multi-fallback API.
    Frontend kirim: { "url": "https://instagram.com/stories/...", "mode": "mp4" }
    """
    try:
        data      = request.json
        story_url = data.get('url', '').strip()
        mode      = data.get('mode', 'mp4').lower()

        if not story_url:
            return jsonify({'success': False, 'error': 'URL kosong'}), 400

        # Helper: cek apakah response JSON valid (bukan HTML error page)
        def is_json_ok(r):
            ct   = r.headers.get('Content-Type', '')
            text = r.text.strip()
            if 'html' in ct: return False
            if text.startswith('<!') or text.startswith('<html'): return False
            if r.status_code != 200: return False
            return True

        # Helper: parse struktur SiputZX igram
        def parse_siputzx(res_json, mode):
            d         = res_json.get('data', {})
            url_list  = d.get('url', [])
            meta      = d.get('meta', {})
            thumbnail = d.get('thumb', '')
            title     = ''
            if isinstance(meta, dict):
                title = meta.get('title', '') or ''
                if not title:
                    uname = meta.get('username', '')
                    title = f"Instagram Story @{uname}" if uname else "Instagram Story"
            valid = [x for x in url_list if x and x.get('url')]
            if mode == 'mp3':
                pick = next((x for x in valid if x.get('type') == 'audio'), None)
                url  = pick['url'] if pick else (valid[0]['url'] if valid else '')
            else:
                srt  = sorted(valid, key=lambda x: x.get('quality', 0), reverse=True)
                url  = srt[0]['url'] if srt else ''
            return title, thumbnail, url

        encoded = requests.utils.quote(story_url, safe='')

        # ── FALLBACK 1: api.siputzx.my.id (subdomain API) ──
        try:
            r = requests.get(
                f"https://api.siputzx.my.id/api/d/igram?url={encoded}",
                headers={'User-Agent': 'Mozilla/5.0', 'Accept': 'application/json'},
                timeout=20
            )
            if is_json_ok(r):
                res = r.json()
                if res.get('status') or res.get('success'):
                    title, thumb, url = parse_siputzx(res, mode)
                    if url:
                        return jsonify({'success': True, 'title': title, 'thumbnail': thumb,
                                        'url': url, 'type': mode.upper(), 'platform': 'SiputZX'})
        except Exception as e:
            print(f"[FB1] {e}")

        # ── FALLBACK 2: app.siputzx.my.id dengan UA mobile ──
        try:
            r = requests.get(
                f"https://app.siputzx.my.id/api/d/igram?url={encoded}",
                headers={
                    'User-Agent': 'Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 Chrome/124 Mobile Safari/537.36',
                    'Accept':     'application/json, */*',
                    'Referer':    'https://app.siputzx.my.id/',
                    'Origin':     'https://app.siputzx.my.id',
                },
                timeout=20
            )
            if is_json_ok(r):
                res = r.json()
                if res.get('status') or res.get('success'):
                    title, thumb, url = parse_siputzx(res, mode)
                    if url:
                        return jsonify({'success': True, 'title': title, 'thumbnail': thumb,
                                        'url': url, 'type': mode.upper(), 'platform': 'SiputZX-App'})
        except Exception as e:
            print(f"[FB2] {e}")

        # ── FALLBACK 3: NexRay web.id v2 instagram ──
        try:
            r = requests.get(
                "https://api.nexray.web.id/downloader/v2/instagram",
                params={'url': story_url},
                timeout=20
            )
            if is_json_ok(r):
                res = r.json()
                if res.get('status'):
                    result = res.get('result', {})
                    title  = result.get('title') or 'Instagram Story'
                    thumb  = result.get('thumbnail') or result.get('cover') or ''
                    media  = result.get('media', [])
                    url    = (media[0].get('url') if isinstance(media, list) and media else '') or \
                              result.get('url') or result.get('video') or result.get('data') or ''
                    if url:
                        return jsonify({'success': True, 'title': title, 'thumbnail': thumb,
                                        'url': url, 'type': mode.upper(), 'platform': 'NexRay'})
        except Exception as e:
            print(f"[FB3] {e}")

        # ── FALLBACK 4: NexRay eu.cc ──
        try:
            r = requests.get(
                "https://api.nexray.eu.cc/downloader/instagram",
                params={'url': story_url},
                timeout=20
            )
            if is_json_ok(r):
                res = r.json()
                if res.get('status'):
                    result = res.get('result', {})
                    title  = result.get('title') or 'Instagram Story'
                    thumb  = result.get('thumbnail') or result.get('cover') or ''
                    media  = result.get('media', [])
                    url    = (media[0].get('url') if isinstance(media, list) and media else '') or \
                              result.get('url') or result.get('video') or ''
                    if url:
                        return jsonify({'success': True, 'title': title, 'thumbnail': thumb,
                                        'url': url, 'type': mode.upper(), 'platform': 'NexRay-EU'})
        except Exception as e:
            print(f"[FB4] {e}")

        return jsonify({
            'success': False,
            'error':   'Semua API gagal. Story mungkin sudah expired (>24 jam), private, atau semua server down.'
        }), 502

    except Exception as e:
        return jsonify({'success': False, 'error': f'Server error: {str(e)}'}), 500

@app.route('/proxy_download', methods=['GET'])
def proxy_download():
    """
    Proxy download file dari URL eksternal.
    WebView fetch endpoint ini → Flask stream file → onDownloadStart() kepanggil di Android.
    
    Query params:
      url      = URL file asli (encoded)
      filename = nama file yang diinginkan (opsional)
    """
    try:
        file_url  = request.args.get('url', '').strip()
        filename  = request.args.get('filename', '').strip()

        if not file_url:
            return jsonify({'error': 'URL kosong'}), 400

        # Tebak ekstensi dari URL kalau filename kosong
        if not filename:
            from urllib.parse import urlparse
            path = urlparse(file_url).path
            basename = path.split('/')[-1].split('?')[0]
            # Ambil ekstensi, default mp4
            ext = basename.split('.')[-1] if '.' in basename else 'mp4'
            # Batasi ekstensi yang valid
            if ext.lower() not in ['mp4', 'mp3', 'jpg', 'jpeg', 'png', 'gif', 'webm', 'mov']:
                ext = 'mp4'
            filename = f"X17_Download_{int(time.time())}.{ext}"

        # Tentukan MIME type
        ext_lower = filename.split('.')[-1].lower()
        mime_map = {
            'mp4':  'video/mp4',
            'mp3':  'audio/mpeg',
            'jpg':  'image/jpeg',
            'jpeg': 'image/jpeg',
            'png':  'image/png',
            'gif':  'image/gif',
            'webm': 'video/webm',
            'mov':  'video/quicktime',
        }
        mime_type = mime_map.get(ext_lower, 'application/octet-stream')

        # Stream dari sumber ke client
        headers_req = {
            'User-Agent': 'Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 Chrome/124 Mobile Safari/537.36',
            'Accept': '*/*',
            'Referer': 'https://www.instagram.com/',
        }

        upstream = requests.get(file_url, headers=headers_req, stream=True, timeout=60)

        if upstream.status_code not in [200, 206]:
            return jsonify({'error': f'Upstream error {upstream.status_code}'}), 502

        # Ambil content-length kalau ada
        content_length = upstream.headers.get('Content-Length')

        def generate():
            for chunk in upstream.iter_content(chunk_size=1024 * 64):  # 64KB chunks
                if chunk:
                    yield chunk

        response_headers = {
            'Content-Disposition': f'attachment; filename="{filename}"',
            'Content-Type': mime_type,
            'Access-Control-Allow-Origin': '*',
            'Cache-Control': 'no-cache',
        }
        if content_length:
            response_headers['Content-Length'] = content_length

        return Response(
            generate(),
            headers=response_headers,
            status=200
        )

    except requests.exceptions.Timeout:
        return jsonify({'error': 'Timeout mengambil file'}), 504
    except Exception as e:
        return jsonify({'error': str(e)}), 500

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
