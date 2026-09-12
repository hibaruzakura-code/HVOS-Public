"""
HVOS Base Edition - メインスクリプト

0.1【公開】260908
0.2【修正】260908
修正箇所（104行目付近）： APIモデル名を旧モデル（gemini-2.5-flash）から新モデル（gemini-3.6-flash）へ変更。
0.3【追加・修正】260911
1. 文字化け・エンコードエラー対策:
   sys.stdout / sys.stderr を UTF-8 に変更し、Windowsコンソールでの UnicodeEncodeError を防止。
2. 連打・長押しの防止:
   キーが完全に離されるまで待機するループを設置し、1回の押し込みにつき1回のみ反応。
3. 強制クールダウン & 重複スレッド生成の停止:
   一度実行されると 5秒間 は次のリクエストを受け付けず、is_processing 判定と合わせて無駄なスレッド生成とAPI重複呼び出しを物理的にブロック。
"""

import sys
import io

# 標準出力をUTF-8に変更（Windows環境でのUnicodeEncodeErrorを防止）
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

import os
import time
import socket
import threading
from datetime import datetime
from flask import Flask, render_template_string, jsonify
import pyautogui
import keyboard
import pygetwindow as gw
from PIL import Image
from google import genai

# ==========================================
# 🔑 APIキー設定（ここに取得したキーを貼り付けます）
# ==========================================
GEMINI_API_KEY = "ここに取得したAPIキーを入れる"

app = Flask(__name__)
gemini_client = genai.Client(api_key=GEMINI_API_KEY)

IMAGE_SAVE_DIR = "saved_captures"
if not os.path.exists(IMAGE_SAVE_DIR):
    os.makedirs(IMAGE_SAVE_DIR)

# スタンバイ完了時のメッセージ
latest_result = {
    "title": "HVOS Base Edition (MQ) - スタンバイ完了",
    "gemini_content": "【HVOS (MQ) スタンバイOK！】\nキーボードの【1】を押すと、目の前の景色をGeminiが撮影＆解析します。\n\n※このシステムを試してみた感想や『こんな機能を追加したよ！』というアイデア・フィードバックがあれば、ぜひnoteコメントやSNSで教えてくださいね！",
    "timestamp": ""
}

is_processing = False
processing_lock = threading.Lock()

def bring_meta_cast_to_front():
    try:
        all_wins = gw.getAllWindows()
        target_win = None
        for win in all_wins:
            title_lower = win.title.lower()
            if any(k in title_lower for k in ["meta casting", "casting", "oculus", "meta"]):
                target_win = win
                break

        if target_win:
            if target_win.isMinimized:
                target_win.restore()
                time.sleep(0.1)
            pyautogui.press('alt')
            target_win.activate()
            time.sleep(0.3)
            return target_win
    except Exception as e:
        print(f"⚠️ ウィンドウ制御エラー: {e}")
    return None

def execute_analysis():
    global latest_result, is_processing

    with processing_lock:
        if is_processing:
            print("⚠️ 解析処理中のためスキップします。")
            return
        is_processing = True

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    latest_result["title"] = "解析中..."
    latest_result["gemini_content"] = "画像を分析しています...数秒お待ちください。"
    latest_result["timestamp"] = now_str

    saved_img_path = os.path.join(IMAGE_SAVE_DIR, f"cap_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")

    try:
        cast_win = bring_meta_cast_to_front()
        screenshot = pyautogui.screenshot()

        if cast_win and cast_win.width > 0 and cast_win.height > 0:
            left, top = max(0, cast_win.left), max(0, cast_win.top)
            right = min(screenshot.width, cast_win.right)
            bottom = min(screenshot.height, cast_win.bottom)
            w, h = right - left, bottom - top
            cropped_img = screenshot.crop((left + int(w * 0.02), top + int(h * 0.08), left + int(w * 0.98), bottom - int(h * 0.02)))
        else:
            w, h = screenshot.size
            cropped_img = screenshot.crop((int(w * 0.05), int(h * 0.05), int(w * 0.95), int(h * 0.95)))

        cropped_img.save(saved_img_path)

        # 旅を100倍楽しくするプロンプト設定（600文字程度）
        prompt = (
            "あなたは最高のバーチャルツアーガイドです。このVR画像に写っている景色・場所について、以下の構成で600文字程度で魅力的に解説してください。\n\n"
            "1. 【場所の特定と概要】：ここがどこか、何という施設・景色か\n"
            "2. 【歴史と背景】：この場所にまつわる深い歴史やストーリー、建築のこだわりなど\n"
            "3. 【ここだけの魅力・おすすめポイント】：訪れた人が『ワクワクする』豆知識や見どころ\n"
            "4. 【周囲のおすすめ・楽しみ方】：もし実際にここを歩くなら立ち寄るべき周辺スポットや楽しみ方\n\n"
            "語り口は親しみやすく、聞いているだけで旅に出たくなるようなワクワクする文章でまとめてください。文末には必ず『（文字数：〇〇文字）』と実際に生成した文字数を記載してください。"
        )
        img = Image.open(saved_img_path)
        
        # ★ 最新推奨モデル 'gemini-2.5-flash'から'gemini-3.6-flash' に修整
        response = gemini_client.models.generate_content(
            model='gemini-3.6-flash',
            contents=[prompt, img]
        )

        latest_result["title"] = "HVOS ガイド解説"
        latest_result["gemini_content"] = response.text

    except Exception as e:
        print(f"❌ エラー発生: {e}")
        latest_result["title"] = "エラー発生"
        latest_result["gemini_content"] = f"処理エラー: {e}"

    finally:
        with processing_lock:
            is_processing = False

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        body { background-color: #0f172a; color: #f8fafc; font-family: sans-serif; padding: 15px; margin: 0; }
        .header { font-size: 1rem; font-weight: bold; color: #818cf8; border-bottom: 1px solid #334155; padding-bottom: 6px; display: flex; justify-content: space-between; }
        .card { background: #1e293b; border-radius: 8px; padding: 15px; margin-top: 12px; border-top: 4px solid #38bdf8; }
        .content { font-size: 0.9rem; line-height: 1.6; white-space: pre-wrap; }
    </style>
    <script>
        setInterval(async () => {
            try {
                const res = await fetch('/api/data');
                const data = await res.json();
                document.getElementById('ui-title').innerText = data.title;
                document.getElementById('ui-timestamp').innerText = data.timestamp;
                document.getElementById('ui-gemini').innerText = data.gemini_content;
            } catch (e) {}
        }, 1000);
    </script>
</head>
<body>
    <div class="header">
        <span id="ui-title">{{ title }}</span>
        <span id="ui-timestamp" style="font-size:0.75rem; color:#64748b;">{{ timestamp }}</span>
    </div>
    <div class="card">
        <div id="ui-gemini" class="content">{{ gemini_content }}</div>
    </div>
</body>
</html>
"""

@app.route('/')
def home():
    return render_template_string(HTML_TEMPLATE, title=latest_result["title"], timestamp=latest_result["timestamp"], gemini_content=latest_result["gemini_content"])

@app.route('/api/data')
def get_data():
    return jsonify(latest_result)

def start_keyboard_listener():
    print("▶ 【1】キーの監視を開始しました。")
    last_execution_time = 0
    cooldown_seconds = 5.0  # 強制クールダウン時間（5秒間は次のリクエストを遮断）

    while True:
        if keyboard.is_pressed("1") or keyboard.is_pressed("num 1"):
            current_time = time.time()
            
            # 【強制クールダウン & 無駄なスレッド生成の停止】
            # 前回の実行から5秒以上経過している場合のみ処理を開始する
            if current_time - last_execution_time > cooldown_seconds:
                last_execution_time = current_time
                
                # 現在解析処理中でなければ、新しいスレッドを起動して解析を実行
                if not is_processing:
                    threading.Thread(target=execute_analysis).start()
            
            # 【連打・長押しの防止】
            # キーが押されている間はループを止め、完全に指が離されるまで待機する
            while keyboard.is_pressed("1") or keyboard.is_pressed("num 1"):
                time.sleep(0.05)

        time.sleep(0.05)

if __name__ == '__main__':
    threading.Thread(target=start_keyboard_listener, daemon=True).start()

    hostname = socket.gethostname()
    try:
        local_ip = socket.gethostbyname(hostname)
    except Exception:
        local_ip = "127.0.0.1"

    print(f"\n==========================================")
    print(f"=== HVOS Base Edition (MQ) 稼働中 ===")
    print(f"・Questブラウザ用URL: http://{local_ip}:5000")
    print(f"==========================================\n")

    app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)