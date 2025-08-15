import os
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from openai import OpenAI

# 로깅 설정
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# 환경 변수에서 토큰과 API 키 가져오기
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
CHANNEL_ID = os.getenv('CHANNEL_ID', '@anju_nous_talk')  
NOUS_API_KEY = os.getenv('NOUS_API_KEY')

# Nous Research API 클라이언트 설정
def create_client(api_key):
    """API 클라이언트 생성 (여러 엔드포인트 시도)"""
    endpoints = [
        "https://api.nousresearch.com/v1",
        "https://api.nous.computer/v1", 
        "https://nous.nousresearch.com/v1",
        "https://api.openai.com/v1"  # fallback
    ]
    
    for endpoint in endpoints:
        try:
            client = OpenAI(api_key=api_key, base_url=endpoint)
            logging.info(f"클라이언트 생성 성공: {endpoint}")
            return client, endpoint
        except Exception as e:
            logging.warning(f"엔드포인트 {endpoint} 실패: {e}")
    
    return None, None

# 전역 클라이언트 초기화
client = None
current_endpoint = None

if NOUS_API_KEY:
    client, current_endpoint = create_client(NOUS_API_KEY)

# 사용자별 대화 상태 저장
user_conversations = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """시작 명령어"""
    welcome_msg = """
🤖 **Nous Research AI 챗봇**에 오신 것을 환영합니다!

📋 **명령어:**
• `/start` - 봇 시작
• `/setkey [API키]` - API 키 설정
• `/stop` - 대화 종료
• `/status` - 현재 상태 확인

💬 **사용법:**
그냥 메시지를 보내시면 AI가 답변해드려요!
    """
    await update.message.reply_text(welcome_msg)

async def setkey(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """API 키 설정 명령어"""
    global client, current_endpoint
    
    if not context.args:
        await update.message.reply_text("❌ 사용법: `/setkey 당신의_API_키`")
        return
    
    api_key = context.args[0]
    
    try:
        new_client, endpoint = create_client(api_key)
        if new_client:
            client = new_client
            current_endpoint = endpoint
            await update.message.reply_text(f"✅ API 키가 설정되었습니다!\n🔗 엔드포인트: `{endpoint}`")
        else:
            await update.message.reply_text("❌ API 키 설정에 실패했습니다. 키를 확인해주세요.")
    except Exception as e:
        await update.message.reply_text(f"❌ API 키 설정 중 오류: {str(e)}")

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """현재 상태 확인"""
    status_msg = f"""
📊 **봇 상태:**

🔑 **API 키**: {'✅ 설정됨' if client else '❌ 미설정'}
🔗 **엔드포인트**: `{current_endpoint if current_endpoint else '없음'}`
💬 **활성 대화**: {len(user_conversations)}개
📺 **채널 ID**: `{CHANNEL_ID}`

{'🟢 정상 작동' if client else '🔴 API 키 필요'}
    """
    await update.message.reply_text(status_msg)

async def stop_conversation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """대화 종료 명령어"""
    user_id = update.effective_user.id
    
    if user_id in user_conversations:
        del user_conversations[user_id]
        await update.message.reply_text("🛑 대화가 종료되었습니다!")
    else:
        await update.message.reply_text("💭 진행 중인 대화가 없습니다.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """메시지 처리"""
    user_id = update.effective_user.id
    user_message = update.message.text
    username = update.effective_user.username or update.effective_user.first_name
    
    # 채널에 메시지 복사
    try:
        channel_msg = f"👤 **{username}**: {user_message}"
        await context.bot.send_message(chat_id=CHANNEL_ID, text=channel_msg)
    except Exception as e:
        logging.error(f"채널 메시지 전송 실패: {e}")
    
    # API 키 확인
    if not client:
        await update.message.reply_text("❌ API 키가 설정되지 않았습니다.\n`/setkey 당신의_API_키`로 설정해주세요.")
        return
    
    # 사용자별 대화 히스토리 관리
    if user_id not in user_conversations:
        user_conversations[user_id] = []
    
    user_conversations[user_id].append({"role": "user", "content": user_message})
    
    # 대화 히스토리가 너무 길면 줄이기 (메모리 관리)
    if len(user_conversations[user_id]) > 20:
        user_conversations[user_id] = user_conversations[user_id][-10:]
    
    try:
        # 여러 모델명 시도
        models_to_try = [
            "nous-hermes-2-mixtral-8x7b",
            "nous-hermes-2-mixtral", 
            "nous-hermes-2",
            "hermes-2-pro",
            "mixtral-8x7b-instruct",
            "mixtral-8x7b",
            "llama-2-70b-chat",
            "gpt-3.5-turbo",  # OpenAI fallback
            "gpt-4"  # OpenAI fallback
        ]
        
        response = None
        used_model = None
        
        for model in models_to_try:
            try:
                # 응답 생성 시작 알림
                await update.message.reply_text("🤖 생각 중...")
                
                response = client.chat.completions.create(
                    model=model,
                    messages=user_conversations[user_id],
                    max_tokens=1000,
                    temperature=0.7,
                    stream=False
                )
                used_model = model
                break
                
            except Exception as model_error:
                logging.warning(f"모델 {model} 실패: {model_error}")
                continue
        
        if response and response.choices:
            ai_response = response.choices[0].message.content
            user_conversations[user_id].append({"role": "assistant", "content": ai_response})
            
            # 응답 전송
            response_msg = f"🤖 **{used_model}**:\n\n{ai_response}"
            await update.message.reply_text(response_msg)
            
            # 채널에도 응답 복사
            try:
                await context.bot.send_message(chat_id=CHANNEL_ID, text=response_msg)
            except Exception as e:
                logging.error(f"채널 응답 전송 실패: {e}")
                
        else:
            error_msg = "❌ 모든 모델에서 응답 생성에 실패했습니다.\n\n🔧 해결 방법:\n• API 키 확인\n• `/setkey`로 다시 설정\n• 잠시 후 다시 시도"
            await update.message.reply_text(error_msg)
            
    except Exception as e:
        error_msg = f"""
❌ **AI 응답 생성 실패**

🔍 **오류 내용**: {str(e)}

🔧 **해결 방법**:
• `/setkey 새로운_API_키`로 재설정
• API 키가 유효한지 확인
• 잠시 후 다시 시도
• `/status`로 현재 상태 확인
        """
        await update.message.reply_text(error_msg)
        logging.error(f"API 에러: {e}")

def main():
    """메인 함수"""
    if not TELEGRAM_TOKEN:
        logging.error("TELEGRAM_TOKEN이 설정되지 않았습니다!")
        return
    
    # 애플리케이션 생성
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    
    # 핸들러 등록
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("setkey", setkey))
    application.add_handler(CommandHandler("status", status))
    application.add_handler(CommandHandler("stop", stop_conversation))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # 봇 시작
    logging.info("봇이 시작됩니다...")
    application.run_polling()

if __name__ == '__main__':
    main()
