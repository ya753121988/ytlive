import os
import subprocess
import signal
import logging
import time
from flask import Flask
from threading import Thread
from telegram import Update
from telegram.ext import Updater, CommandHandler, CallbackContext

# ১. সেটিংস
TOKEN = os.getenv("BOT_TOKEN") # টেলিগ্রাম বোট টোকেন (Render এনভায়রনমেন্টে দিন)
# আপনার দেওয়া স্ট্রিম কি এবং ইউআরএল
STREAM_KEY = "qd0k-80ky-e170-hjvm-2zw8" 
RTMP_URL = f"rtmp://a.rtmp.youtube.com/live2/{STREAM_KEY}"
BGM_URL = "https://www.bensound.com/bensound-music/bensound-creativeminds.mp3"

# ২. Flask অ্যাপ (Render-এর জন্য)
app = Flask('')

@app.route('/')
def home():
    return "Bot is alive and running!"

def run_flask():
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run_flask)
    t.daemon = True
    t.start()

# ৩. লগিং সেটআপ
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', 
    level=logging.INFO
)

# গ্লোবাল ভেরিয়েবল
streaming_process = None

# ৪. কমান্ড হ্যান্ডলার ফাংশনসমূহ
def start(update: Update, context: CallbackContext):
    update.message.reply_text(
        "🔥 প্রফেশনাল লাইভ স্ট্রিম বট চালু আছে!\n\n"
        "লাইভ শুরু করতে লিখুন:\n"
        "/live টাইটেল | ইউটিউব_লিংক\n\n"
        "লাইভ বন্ধ করতে লিখুন: /stop"
    )

def live(update: Update, context: CallbackContext):
    global streaming_process
    
    if streaming_process:
        update.message.reply_text("❌ অলরেডি একটি লাইভ চলছে। আগে সেটি /stop করুন।")
        return

    try:
        # ইনপুট পার্স করা (টাইটেল | ইউটিউব_লিংক)
        input_text = " ".join(context.args).split("|")
        if len(input_text) < 2:
            update.message.reply_text("সঠিক ফরম্যাট: /live টাইটেল | ইউটিউব_লিংক")
            return

        title = input_text[0].strip()
        yt_url = input_text[1].strip()

        sent_msg = update.message.reply_text(f"🚀 লাইভ প্রসেস শুরু হচ্ছে: {title}...\nলিংক সংগ্রহ করা হচ্ছে...")

        # ১. yt-dlp দিয়ে ভিডিও সরাসরি ইউআরএল সংগ্রহ (Error handling সহ)
        try:
            get_url_cmd = ["yt-dlp", "-g", "-f", "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best", yt_url]
            video_url = subprocess.check_output(get_url_cmd).decode("utf-8").strip()
        except Exception as e:
            sent_msg.edit_text(f"❌ yt-dlp লিঙ্ক সংগ্রহ করতে ব্যর্থ হয়েছে। লিঙ্কটি সঠিক কি না চেক করুন।\nError: {str(e)}")
            return

        sent_msg.edit_text("✅ লিঙ্ক পাওয়া গেছে! কপিরাইট ফিল্টার সহ স্ট্রিমিং শুরু হচ্ছে...")

        # ২. FFmpeg কমান্ড
        # ফিল্টার: স্কেলিং, স্যাচুরেশন বৃদ্ধি (কপিরাইট এড়াতে), টেক্সট ওভারলে এবং অডিও মিক্সিং
        ffmpeg_cmd = [
            'ffmpeg', '-re', '-i', video_url, '-i', BGM_URL,
            '-filter_complex', 
            "[0:v]scale=1280:720,hue=s=1.2:b=0.1,drawtext=text='LIVE':x=10:y=10:fontsize=30:fontcolor=white:box=1:boxcolor=black@0.5[v];"
            "[0:a]rubberband=pitch=1.03[a1];[1:a]volume=0.10[a2];[a1][a2]amix=inputs=2:duration=first[a]",
            '-map', '[v]', '-map', '[a]',
            '-c:v', 'libx264', '-preset', 'veryfast', '-b:v', '3000k', '-maxrate', '3500k', '-bufsize', '7000k',
            '-pix_fmt', 'yuv420p', '-g', '50', '-c:a', 'aac', '-b:a', '128k', '-ar', '44100',
            '-f', 'flv', RTMP_URL
        ]

        # ব্যাকগ্রাউন্ডে প্রসেস রান করা
        streaming_process = subprocess.Popen(
            ffmpeg_cmd, 
            stdout=subprocess.DEVNULL, 
            stderr=subprocess.PIPE # ইরোর ট্র্যাক করার জন্য
        )
        
        update.message.reply_text(f"✅ লাইভ এখন ইউটিউবে চলছে!\nটাইটেল: {title}")

    except Exception as e:
        update.message.reply_text(f"❌ একটি বড় ভুল হয়েছে: {str(e)}")

def stop(update: Update, context: CallbackContext):
    global streaming_process
    if streaming_process:
        try:
            streaming_process.terminate()
            streaming_process.wait(timeout=5)
        except:
            streaming_process.kill()
        
        streaming_process = None
        update.message.reply_text("🛑 লাইভ স্ট্রিমিং বন্ধ করা হয়েছে।")
    else:
        update.message.reply_text("⚠️ বর্তমানে কোনো লাইভ চলছে না।")

# ৫. মেইন ফাংশন
def main():
    keep_alive()
    
    updater = Updater(TOKEN)
    dp = updater.dispatcher
    
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("live", live))
    dp.add_handler(CommandHandler("stop", stop))
    
    print("Bot is polling...")
    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
