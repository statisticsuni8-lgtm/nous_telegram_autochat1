import asyncio
import logging
import random
import requests
import os
from datetime import datetime
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

user_api_keys = {}

class ChatBot:
    def __init__(self, name, personality, emoji):
        self.name = name
        self.personality = personality
        self.emoji = emoji
    
    def get_response(self, message, history="", api_key=""):
        if not api_key:
            return "❌ API 키가 설정되지 않았습니다."
            
        url = "https://api.openai.com/v1/chat/completions"
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }
        
        system_prompt = f"""
당신은 {self.personality}

규칙:
1. 1-2문장으로 자연스럽게 대화하세요
2. 한국어로 대화하세요  
3. 상대방 말에 적절히 반응하세요
4. 가끔 새로운 주제를 제시하세요
5. 이모티콘을 적절히 사용하세요

최근 대화:
{history}
"""
        
        data = {
            "model": "gpt-3.5-turbo",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": message}
            ],
            "max_tokens": 100,
            "temperature": 0.9
        }
        
        try:
            response = requests.post(url, headers=headers, json=data, timeout=30)
            if response.status_code == 401:
                return "❌ API 키가 유효하지 않습니다. /setkey 로 다시 설정해주세요."
            response.raise_for_status()
            result = response.json()
            return result['choices'][0]['message']['content'].strip()
        except Exception as e:
            logger.error(f"API 오류: {e}")
            return "음... 잠깐만! 뭐라고 했지? 🤔"

bots = [
    ChatBot(
        name="민지", 
        personality="활발하고 재미있는 20대 대학생. 최신 트렌드와 K-pop을 좋아하고 항상 밝고 긍정적. 반말 사용하고 이모티콘 많이 씀.",
        emoji="😊"
    ),
    ChatBot(
        name="준호",
        personality="차분하고 사려깊은 직장인. 책과 영화를 좋아하고 깊이있는 대화를 선호. 정중하고 따뜻한 말투로 존댓말 사용.",
        emoji="🤔"
    )
]

active_chats = {}
waiting_for_api_key = {}

def check_api_key(user_id):
    return user_api_keys.get(user_id, None)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    api_key = check_api_key(user_id)
    
    if api_key:
        status = "✅ API 키 설정됨"
    else:
        status = "❌ API 키 필요"
    
    welcome = f"""
🎭 AI 자동 대화극장에 오신 것을 환영합니다! 🎭

현재 상태: {status}

👥 출연진:
😊 민지 - 활발한 20대 대학생
🤔 준호 - 차분한 직장인

📋 명령어:
/start - 극장 입장 🎭
/setkey - 🔑 OpenAI API 키 설정
/chat - 🎬 대화극 시작!
/stop - ⏹️ 대화 중단
/help - 📚 도움말

🚀 처음 사용법:
1. /setkey 명령어로 OpenAI API 키 설정
2. /chat 으로 자동 대화 시작!
3. 두 AI가 알아서 대화하는 걸 구경하세요! 🍿
"""
    await update.message.reply_text(welcome)

async def set_api_key(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    waiting_for_api_key[user_id] = True
    
    guide = """
🔑 OpenAI API 키를 설정해주세요!

📋 API 키 받는 방법:
1. https://platform.openai.com 접속
2. 회원가입/로그인
3. 휴대폰 번호 인증 (필수)
4. 왼쪽 메뉴 "API Keys" 클릭
5. "Create new secret key" 클릭
6. 생성된 키 복사

💬 키 입력 방법:
sk-로 시작하는 키를 그대로 보내주세요

👇 지금 API 키를 보내주세요!
"""
    await update.message.reply_text(guide)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    message_text = update.message.text.strip()
    
    if user_id in waiting_for_api_key and waiting_for_api_key[user_id]:
        if message_text.startswith('sk-') and len(message_text) > 20:
            user_api_keys[user_id] = message_text
            waiting_for_api_key[user_id] = False
            
            try:
                await context.bot.delete_message(
                    chat_id=update.effective_chat.id,
                    message_id=update.message.message_id
                )
            except:
                pass
            
            await update.message.reply_text(
                "✅ API 키가 성공적으로 설정되었습니다!\n\n"
                "🎬 이제 /chat 명령어로 자동 대화를 시작할 수 있습니다!"
            )
        else:
            await update.message.reply_text(
                "❌ 올바른 API 키 형식이 아닙니다.\n\n"
                "sk-로 시작하는 키를 정확히 복사해서 보내주세요."
            )
            waiting_for_api_key[user_id] = False
    else:
        await update.message.reply_text(
            "안녕하세요! 😊\n\n"
            "/start - 시작하기\n"
            "/help - 도움말"
        )

async def start_auto_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    
    api_key = check_api_key(user_id)
    if not api_key:
        await update.message.reply_text(
            "❌ OpenAI API 키가 설정되지 않았습니다!\n\n"
            "🔑 /setkey 명령어로 먼저 API 키를 설정해주세요."
        )
        return
    
    if chat_id in active_chats and active_chats[chat_id]['active']:
        await update.message.reply_text("❌ 이미 대화극이 진행 중입니다! /stop 으로 먼저 중단해주세요.")
        return
    
    active_chats[chat_id] = {
        'active': True,
        'conversation': [],
        'turn': 0,
        'api_key': api_key
    }
    
    start_topics = [
        "안녕! 오늘 하루 어땠어?",
        "요즘 재밌는 일 있어?", 
        "날씨가 정말 좋네요!",
        "혹시 좋아하는 음악 있나요?",
        "최근에 본 영화 추천해주실래요?"
    ]
    
    current_message = random.choice(start_topics)
    
    await update.message.reply_text(
        f"🎬 자동 대화극 시작!\n\n"
        f"💭 첫 대사: '{current_message}'\n\n"
        f"🍿 편안히 관람하세요!"
    )
    
    asyncio.create_task(auto_conversation_loop(chat_id, current_message, context))

async def stop_auto_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    
    if chat_id not in active_chats or not active_chats[chat_id]['active']:
        await update.message.reply_text("❌ 현재 진행 중인 대화극이 없습니다.")
        return
    
    active_chats[chat_id]['active'] = False
    turn_count = active_chats[chat_id]['turn']
    
    await update.message.reply_text(f"🎭 대화극이 종료되었습니다!\n\n📊 총 {turn_count}번의 대화!")

async def auto_conversation_loop(chat_id, current_message, context):
    try:
        while active_chats[chat_id]['active']:
            turn = active_chats[chat_id]['turn']
            speaker = bots[turn % 2]
            api_key = active_chats[chat_id]['api_key']
            
            recent_history = "\n".join(active_chats[chat_id]['conversation'][-6:])
            
            response = speaker.get_response(current_message, recent_history, api_key)
            
            time_stamp = datetime.now().strftime("%H:%M")
            formatted_msg = f"[{time_stamp}] {speaker.emoji} **{speaker.name}**: {response}"
            
            await context.bot.send_message(
                chat_id=chat_id,
                text=formatted_msg,
                parse_mode='Markdown'
            )
            
            active_chats[chat_id]['conversation'].append(f"{speaker.name}: {response}")
            active_chats[chat_id]['turn'] += 1
            
            current_message = response
            
            wait_time = random.uniform(4, 10)
            await asyncio.sleep(wait_time)
            
            if (turn + 1) == 20:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text="🎉 20턴 달성! 대화가 재밌게 흘러가네요!"
                )
                
    except Exception as e:
        logger.error(f"대화 루프 오류: {e}")
        if chat_id in active_chats:
            active_chats[chat_id]['active'] = False

def main():
    print("🚀 AI 자동 대화극장 오픈!")
    
    if not TELEGRAM_BOT_TOKEN:
        print("❌ TELEGRAM_BOT_TOKEN 환경변수가 설정되지 않았습니다.")
        return
    
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("setkey", set_api_key))
    app.add_handler(CommandHandler("chat", start_auto_chat))
    app.add_handler(CommandHandler("stop", stop_auto_chat))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    print("✅ 극장이 개장했습니다!")
    
    app.run_polling()

if __name__ == '__main__':
    main()
