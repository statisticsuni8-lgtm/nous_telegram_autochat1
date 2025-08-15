import os
import logging
import asyncio
import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# 로깅 설정
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# 환경 변수 읽기
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
NOUS_API_KEY = os.getenv("NOUS_API_KEY")
CHANNEL_ID = os.getenv("CHANNEL_ID", "@anju_nous_talk")

# 사용자별 대화 진행 여부
active_conversations = {}

# Nous API 호출 함수
def call_nous_api(message, history=None):
    """
    Nous Research API 호출
    """
    url = "https://api.nousmodel.ai/v1/chat/completions"  # 실제 엔드포인트로 변경 필요 가능성 있음
    headers = {
        "Authorization": f"Bearer {NOUS_API_KEY}",
        "Content-Type": "application/json"
    }
    messages = history if history else [{"role": "user", "content": message}]
    payload = {
        "model": "nous-hermes-2",  # 사용 가능한 모델명으로 수정 가능
        "messages": messages,
        "max_tokens": 512,
        "temperature": 0.7
    }

    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        return data.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
    except Exception as e:
        logging.error(f"Nous API 오류: {e}")
        return f"❌ API 호출 오류: {e}"

# /start → 무한 대화 시작
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    active_conversations[user_id] = True
    await update.message.reply_text("🤖 무한 봇 대화를 시작합니다. '/stop' 입력 시 종료됩니다.")

    # 대화 초기 문장
    bot_a_message = "안녕, 나는 봇A야!"
    while active_conversations.get(user_id, False):
        # 봇A → 봇B
        bot_b_reply = call_nous_api(bot_a_message)
        await update.message.reply_text(f"봇B: {bot_b_reply}")
        try:
            await context.bot.send_message(chat_id=CHANNEL_ID, text=f"봇B: {bot_b_reply}")
        except:
            pass

        # 봇B → 봇A
        bot_a_message = call_nous_api(bot_b_reply)
        await update.message.reply_text(f"봇A: {bot_a_message}")
        try:
            await context.bot.send_message(chat_id=CHANNEL_ID, text=f"봇A: {bot_a_message}")
        except:
            pass

        await asyncio.sleep(1)  # 요청 빈도 제어 (API 부하 방지)

# /stop → 대화 종료
async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    active_conversations[user_id] = False
    await update.message.reply_text("🛑 무한 대화가 종료되었습니다.")

# 실행 상태 확인
async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    is_active = active_conversations.get(user_id, False)
    await update.message.reply_text(
        f"상태: {'🟢 대화 중' if is_active else '🔴 대화 아님'}\n"
        f"API Key: {'✅ 있음' if NOUS_API_KEY else '❌ 없음'}\n"
        f"채널: {CHANNEL_ID}"
    )

# 메인 실행
def main():
    if not TELEGRAM_TOKEN:
        logging.error("❌ TELEGRAM_BOT_TOKEN 환경변수를 설정하세요.")
        return
    if not NOUS_API_KEY:
        logging.error("❌ NOUS_API_KEY 환경변수를 설정하세요.")
        return

    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("stop", stop))
    app.add_handler(CommandHandler("status", status))

    logging.info("🚀 봇 시작됨")
    app.run_polling()

if __name__ == "__main__":
    main()
