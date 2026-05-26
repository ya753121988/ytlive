import os
import subprocess
import signal
import logging
from flask import Flask
from threading import Thread
from telegram import Update
from telegram.ext import Updater, CommandHandler, CallbackContext

# ১. Render-এর পোর্ট সমস্যা সমাধানের জন্য Flask অ্যাপ
app = Flask('')

@app.route('/')
def home():
    return "Bot is alive and running!"

def run_flask():
    # Render অটোমেটিক একটি PORT এনভায়রনমেন্ট ভেরিয়েবল সেট করে দেয়
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run_flask)
    t.daemon = True
    t.start()

# ২. সেটিংস এবং এনভায়রনমেন্ট ভেরিয়েবল
TOKEN = os.getenv("BOT_TOKEN")
STREAM_KEY = os.getenv("STREAM_KEY")
# ইউটিউব আরটিএমপি ইউআরএল
RTMP_URL = f"rtmp://a.rtmp.youtube.com/live2/{STREAM_KEY}"
# কপিরাইট ফ্রি ব্যাকগ্রাউন্ড মিউজিক
BGM_URL = "https://www.bensound.com/bensound-music/bensound-creativeminds.mp3" 

# ৩. লগিং সেটআপ
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', 
    level=logging.INFO
)

# গ্লোবাল ভেরিয়েবল স্ট্রিমিং প্রসেস ট্র্যাক করার জন্য
streaming_process = None

# ৪. কমান্ড হ্যান্ডলার ফাংশনসমূহ
def start(update: Update, context: CallbackContext):
    update.message.reply_text(
        "🔥 প্রফেশনাল লাইভ স্ট্রিম বট চালু আছে!\n\n"
        "লাইভ শুরু করতে লিখুন:\n"
        "/live টাইটেল | পোস্টার_লিংক | ইউটিউব_লিংক\n\n"
        "লাইভ বন্ধ করতে লিখুন: /stop"
    )

def live(update: Update, context: CallbackContext):
    global streaming_process
    
    if streaming_process:
        update.message.reply_text("❌ অলরেডি একটি লাইভ চলছে। আগে সেটি /stop করুন।")
        return

    try:
        input_text = " ".join(context.args).split("|")
        if len(input_text) < 3:
            update.message.reply_text("সঠিক ফরম্যাট: /live টাইটেল | পোস্টার_লিংক | ইউটিউব_লিংক")
            return

        title = input_text[0].strip()
        yt_url = input_text[2].strip()

        update.message.reply_text(f"🚀 লাইভ প্রসেস শুরু হচ্ছে: {title}\nএটিতে কপিরাইট প্রটেকশন ফিল্টার লাগানো হচ্ছে...")

        # ১. yt-dlp দিয়ে ভিডিও সরাসরি ইউআরএল সংগ্রহ
        get_url_cmd = f"yt-dlp -g -f 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best' {yt_url}"
        video_url = subprocess.check_output(get_url_cmd, shell=True).decode("utf-8").strip()

        # ২. FFmpeg কমান্ড (ভিডিও এবং অডিও ফিল্টারসহ)
        ffmpeg_cmd = [
            'ffmpeg', '-re', '-i', video_url, '-i', BGM_URL,
            '-filter_complex', 
            "[0:v]scale=1280:720,hue=s=1.1:b=0.1,drawtext=text='LIVE STREAMING':x=10:y=10:fontsize=24:fontcolor=white:box=1:boxcolor=black@0.5[v];"
            "[0:a]rubberband=pitch=1.02[a1];[1:a]volume=0.15[a2];[a1][a2]amix=inputs=2:duration=first[a]",
            '-map', '[v]', '-map', '[a]',
            '-c:v', 'libx264', '-preset', 'veryfast', '-b:v', '3500k', '-maxrate', '4000k', '-bufsize', '8000k',
            '-pix_fmt', 'yuv420p', '-g', '50', '-c:a', 'aac', '-b:a', '160k', '-f', 'flv', RTMP_URL
        ]

        # ব্যাকগ্রাউন্ডে প্রসেস রান করা
        streaming_process = subprocess.Popen(
            ffmpeg_cmd, 
            stdout=subprocess.DEVNULL, 
            stderr=subprocess.DEVNULL
        )
        
        update.message.reply_text(f"✅ লাইভ এখন চলছে!\nআপনি অফলাইনে গেলেও এটি চলতে থাকবে।")

    except Exception as e:
        update.message.reply_text(f"❌ ভুল হয়েছে: {str(e)}")

def stop(update: Update, context: CallbackContext):
    global streaming_process
    if streaming_process:
        # প্রসেসটি বন্ধ করা
        os.kill(streaming_process.pid, signal.SIGTERM)
        streaming_process = None
        update.message.reply_text("🛑 লাইভ বন্ধ করা হয়েছে।")
    else:
        update.message.reply_text("⚠️ বর্তমানে কোনো লাইভ চলছে না।")

# ৫. মেইন ফাংশন
def main():
    # প্রথমে পোর্ট সমস্যা সমাধানের জন্য Flask চালু করুন
    print("Starting Flask Keep-Alive Server...")
    keep_alive()

    # টেলিগ্রাম বোট সেটআপ
    updater = Updater(TOKEN)
    dp = updater.dispatcher
    
    # কমান্ড রেজিস্টার করা
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("live", live))
    dp.add_handler(CommandHandler("stop", stop))
    
    print("Bot is polling...")
    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
