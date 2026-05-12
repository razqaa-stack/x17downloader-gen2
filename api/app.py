import os
import time
import requests
from flask import Flask, request, send_file, jsonify, send_from_directory
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
    return "X17 ULTRA ENGINE V13 - SIPUTX + NEXRAY HYBRID 🚀"

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
        mode = data.get('mode', 'mp4')
        u = url.lower()

        # ═══════════════════════════════════════════════════════════
        #  INSTAGRAM STORY — SIPUTX PRIMARY + NEXRAY FALLBACK
        # ═══════════════════════════════════════════════════════════
        if "instagram.com/stories/" in u:
            # ── Coba SiputX dulu (lebih fresh untuk story) ──────
            try:
                # URL encode parameter URL biar ga error
                encoded_url = quote_plus(url)
                endpoint_siput = f"https://app.siputzx.my.id/api/d/igram?url={encoded_url}"
                
                headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    "Accept": "application/json, text/plain, */*",
                    "Accept-Language": "id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7",
                    "Referer": "https://app.siputzx.my.id/",
                    "Origin": "https://app.siputzx.my.id"
                }
                
                r = requests.get(endpoint_siput, headers=headers, timeout=12)
                
                # ── Cek apakah response valid JSON ──────────────
                content_type = r.headers.get('Content-Type', '')
                
                if 'application/json' not in content_type:
                    # Response bukan JSON (error page HTML) → fallback
                    raise Exception(f"SiputX HTML response (rate limit?): {content_type}")
                
                res = r.json()

                # ── Validasi structure response ─────────────────
                if not res.get('status'):
                    raise Exception(res.get('message', 'Story tidak tersedia'))
                
                data_siput = res.get('data', {})
                urls = data_siput.get('url', [])
                
                if not urls or len(urls) == 0:
                    raise Exception('Link download kosong dari SiputX')

                # ── Ekstrak data ─────────────────────────────────
                # Mode mp3 → cari audio dari DASH manifest atau url audio
                if mode == 'mp3':
                    # Cek apakah ada variant audio di array url
                    audio_url = None
                    for item in urls:
                        if item.get('type') == 'audio' or 'audio' in item.get('name', '').lower():
                            audio_url = item.get('url')
                            break
                    
                    # Kalau ga ada audio variant, ambil video terus client extract audionya
                    final_url = audio_url if audio_url else urls[0].get('url')
                else:
                    # Mode mp4 → ambil kualitas tertinggi
                    # Sort by quality descending
                    sorted_urls = sorted(urls, key=lambda x: x.get('quality', 0), reverse=True)
                    final_url = sorted_urls[0].get('url')

                meta = data_siput.get('meta', {})
                title = meta.get('title') or "Instagram Story"
                thumb = data_siput.get('thumb') or "https://api.nexray.web.id/favicon.ico"

                return jsonify({
                    'success': True,
                    'title': title,
                    'thumbnail': thumb,
                    'url': final_url,
                    'type': mode.upper(),
                    'platform': 'SiputX-Story'
                })

            except Exception as siput_error:
                # ── FALLBACK: NexRay Instagram v2 ───────────────
                # SiputX gagal → pakai NexRay (lebih stabil tapi kadang ga support story fresh)
                print(f"⚠️ SiputX failed: {siput_error}, fallback to NexRay...")
                
                try:
                    endpoint_nex = f"{NEX_BASE}/downloader/v2/instagram"
                    params_nex = {"url": url}
                    r_nex = requests.get(endpoint_nex, params=params_nex, timeout=20)
                    res_nex = r_nex.json()

                    if not res_nex.get('status'):
                        return jsonify({
                            'success': False, 
                            'error': f'SiputX & NexRay gagal. Story mungkin private atau expired.'
                        }), 400

                    result_nex = res_nex.get('result', {})
                    
                    # Ekstrak link
                    if mode == 'mp3':
                        # Coba ambil audio kalau ada
                        final_url_nex = result_nex.get('audio') or result_nex.get('url')
                    else:
                        # Video
                        media = result_nex.get('media', [])
                        if media and len(media) > 0:
                            final_url_nex = media[0].get('url')
                        else:
                            final_url_nex = result_nex.get('url')

                    title_nex = result_nex.get('title') or "Instagram Story (NexRay)"
                    thumb_nex = result_nex.get('thumbnail') or "https://api.nexray.web.id/favicon.ico"

                    return jsonify({
                        'success': True,
                        'title': title_nex,
                        'thumbnail': thumb_nex,
                        'url': final_url_nex,
                        'type': mode.upper(),
                        'platform': 'NexRay-Fallback'
                    })

                except Exception as nex_error:
                    return jsonify({
                        'success': False,
                        'error': f'Semua API gagal. SiputX: {str(siput_error)[:50]}, NexRay: {str(nex_error)[:50]}'
                    }), 500

        # ═══════════════════════════════════════════════════════════
        #  PLATFORM LAIN (YOUTUBE, TIKTOK, FB, dll) — NEXRAY
        # ═══════════════════════════════════════════════════════════
        
        # YouTube
        if any(x in u for x in ["youtube.com", "youtu.be"]):
            endpoint = f"{NEX_BASE}/downloader/v1/ytmp3" if mode == "mp3" else f"{NEX_BASE}/downloader/v1/ytmp4"
            params = {"url": url, "resolusi": "1080"}
        
        # Facebook
        elif "facebook.com" in u or "fb.watch" in u:
            endpoint = f"{NEX_BASE}/downloader/facebook"
            params = {"url": url}
        
        # Instagram (non-story: reel, post, IGTV)
        elif "instagram.com" in u:
            endpoint = f"{NEX_BASE}/downloader/v2/instagram"
            params = {"url": url}
        
        # TikTok
        elif "tiktok.com" in u:
            endpoint = f"{NEX_BASE}/downloader/tiktok"
            params = {"url": url}
        
        # Douyin
        elif "douyin.com" in u:
            endpoint = f"{NEX_BASE}/downloader/v1/douyin"
            params = {"url": url}
        
        # Spotify
        elif "spotify.com" in u:
            endpoint = f"{NEX_BASE}/downloader/spotify"
            params = {"url": url}
        
        # Pinterest
        elif "pinterest.com" in u or "pin.it" in u:
            endpoint = f"{NEX_BASE}/downloader/pinterest"
            params = {"url": url}
        
        # Scribd
        elif "scribd.com" in u:
            endpoint = f"{NEX_BASE}/downloader/scribd"
            params = {"url": url}
        
        # Twitter/X
        elif "twitter.com" in u or "x.com" in u:
            endpoint = f"{NEX_BASE}/downloader/twitter"
            params = {"url": url}
        
        # Videy
        elif "videy.co" in u:
            endpoint = f"{NEX_BASE}/downloader/videy"
            params = {"url": url}
        
        # All-in-one fallback
        else:
            endpoint = f"{NEX_BASE}/downloader/aio"
            params = {"url": url}

        # ── Execute NexRay API ──────────────────────────────────
        r = requests.get(endpoint, params=params, timeout=30)
        res = r.json()

        if not res.get('status'):
            return jsonify({
                'success': False, 
                'error': res.get('message', 'API NexRay gagal merespon')
            }), 400

        result = res.get('result', {})
        final_url = None
        title = result.get('title') or "X17 Downloader Result"
        thumb = result.get('thumbnail') or result.get('cover') or 'https://api.nexray.web.id/favicon.ico'

        # ── Ekstraksi link berdasarkan mode ────────────────────
        if mode == "mp3":
            # Audio priority: music_info > audio > url
            if "music_info" in result:
                final_url = result["music_info"].get("url")
            elif "audio" in result:
                final_url = result.get("audio")
            elif "url" in result:
                final_url = result.get("url")
            else:
                final_url = result.get("video") # Fallback ke video
        else:
            # Video priority: video_hd > media[0] > data > url > video
            if "video_hd" in result:
                final_url = result.get("video_hd")
            elif "media" in result and isinstance(result["media"], list) and len(result["media"]) > 0:
                final_url = result["media"][0].get("url")
            elif "data" in result:
                final_url = result.get("data")
            elif "url" in result:
                final_url = result.get("url")
            else:
                final_url = result.get("video")

        if not final_url:
            return jsonify({
                'success': False,
                'error': 'Link download tidak ditemukan di response API'
            }), 400

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

@app.route('/search_yt', methods=['GET'])
def search_youtube():
    query = request.args.get('query', '')
    if not query:
        return jsonify({"status": False, "message": "Query pencarian kosong!"})
    try:
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
    except Exception as e:
        return f"Error: {str(e)}", 500
    finally:
        if os.path.exists(v_path): os.remove(v_path)

@app.route('/wallpapers/<path:filename>')
def serve_wallpaper(filename):
    return send_from_directory(os.getcwd(), filename)

app = app
