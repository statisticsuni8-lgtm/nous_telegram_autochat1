import os
import asyncio
import aiohttp
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import random

# 로깅 설정
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class BotChatSystem:
    def __init__(self):
        self.nous_api_key = None
        self.bot1_token = os.getenv('BOT1_TOKEN')
        self.bot2_token = os.getenv('BOT2_TOKEN')
        self.admin_chat_id = None
        self.chat_active = False
        self.chat_count = 0
        self.max_messages = 50  # 무한 루프 방지
        
    async def call_nous_api(self, message):
        """Nous Research API 호출"""
        if not self.nous_api_key:
            return "API 키가 설정되지 않았습니다."
            
        headers = {
            'Authorization': f'Bearer {self.nous_api_key}',
            'Content-Type': 'application/json'
        }
        
        data = {
            "model": "hermes-3-llama-3.1-405b",
            "messages": [
                {"role": "user", "content": message}
            ],
            "max_tokens": 150,
            "temperature": 0.7
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    'https://api.nousresearch.com/v1/chat/completions',
                    headers=headers,
                    json=data
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        return result['choices'][0]['message']['content']
                    else:
                        return f"API 오류: {response.status}"
        except Exception as e:
            logger.error(f"API 호출 오류: {e}")
            return "API 호출 중 오류가 발생했습니다."

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """시작 명령어"""
        self.admin_chat_id = update.effective_chat.id
        await update.message.reply_text(
            "🤖 텔레그램 봇 대화 시스템입니다!\n\n"
            "사용법:\n"
            "1. Nous Research API 키를 직접 메시지로 보내주세요\n"
            "2. /start_chat - 봇들 간의 대화 시작\n"
            "3. /stop_chat - 대화 중지\n"
            "4. /status - 현재 상태 확인"
        )

    async def set_api_key(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """API 키 설정"""
        message_text = update.message.text
        
        # API 키 형식 검증 (기본적인 체크)
        if len(message_text) > 20 and ('sk-' in message_text or 'nsk-' in message_text):
            self.nous_api_key = message_text.strip()
            await update.message.reply_text("✅ API 키가 설정되었습니다!")
            await update.message.delete()  # 보안을 위해 메시지 삭제
            
            # API 키 테스트
            test_response = await self.call_nous_api("Hello, test message")
            await update.message.reply_text(f"🧪 API 테스트: {test_response}")
        else:
            await update.message.reply_text("❌ 올바른 API 키 형식이 아닙니다.")

    async def start_chat_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """봇 대화 시작"""
        if not self.nous_api_key:
            await update.message.reply_text("❌ 먼저 API 키를 설정해주세요!")
            return
            
        if self.chat_active:
            await update.message.reply_text("⚠️ 이미 대화가 진행 중입니다!")
            return
            
        self.chat_active = True
        self.chat_count = 0
        await update.message.reply_text("🚀 봇들 간의 대화를 시작합니다!")
        
        # 대화 시작
        asyncio.create_task(self.run_bot_conversation())

    async def stop_chat_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """봇 대화 중지"""
        self.chat_active = False
        await update.message.reply_text(f"⏹️ 대화를 중지했습니다. (총 {self.chat_count}개 메시지)")

    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """상태 확인"""
        api_status = "✅ 설정됨" if self.nous_api_key else "❌ 미설정"
        chat_status = "🟢 활성" if self.chat_active else "🔴 비활성"
        
        await update.message.reply_text(
            f"📊 현재 상태:\n"
            f"API 키: {api_status}\n"
            f"대화 상태: {chat_status}\n"
            f"메시지 수: {self.chat_count}/{self.max_messages}"
        )

    async def run_bot_conversation(self):
        """봇들 간의 무한 대화 실행"""
        conversation_topics = [
            "오늘 날씨가 어때?",
            "좋아하는 음식이 뭐야?",
            "취미가 뭐야?",
            "최근에 본 영화 추천해줘",
            "인공지능에 대해 어떻게 생각해?",
            "우주에 대해 이야기해보자",
            "철학적인 질문을 해보자"
        ]
        
        current_message = random.choice(conversation_topics)
        bot_names = ["🤖 Bot Alice", "🤖 Bot Bob"]
        current_bot = 0
        
        while self.chat_active and self.chat_count < self.max_messages:
            try:
                # API 호출
                response = await self.call_nous_api(current_message)
                
                # 응답 전송
                if self.admin_chat_id:
                    bot_app = Application.builder().token(
                        self.bot1_token if current_bot == 0 else self.bot2_token
                    ).build()
                    
                    await bot_app.bot.send_message(
                        chat_id=self.admin_chat_id,
                        text=f"{bot_names[current_bot]}: {response}"
                    )
                
                # 다음 메시지 준비
                current_message = response
                current_bot = 1 - current_bot  # 봇 교체
                self.chat_count += 1
                
                # 대화 간격
                await asyncio.sleep(3)
                
            except Exception as e:
                logger.error(f"대화 중 오류: {e}")
                await asyncio.sleep(5)
        
        self.chat_active = False
        if self.admin_chat_id:
            bot_app = Application.builder().token(self.bot1_token).build()
            await bot_app.bot.send_message(
                chat_id=self.admin_chat_id,
                text=f"🏁 대화가 종료되었습니다. (총 {self.chat_count}개 메시지)"
            )

async def main():
    """메인 함수"""
    bot_system = BotChatSystem()
    
    # 첫 번째 봇 (관리용)
    app = Application.builder().token(bot_system.bot1_token).build()
    
    # 핸들러 등록
    app.add_handler(CommandHandler("start", bot_system.start_command))
    app.add_handler(CommandHandler("start_chat", bot_system.start_chat_command))
    app.add_handler(CommandHandler("stop_chat", bot_system.stop_chat_command))
    app.add_handler(CommandHandler("status", bot_system.status_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, bot_system.set_api_key))
    
    # 봇 시작
    await app.initialize()
    await app.start()
    await app.updater.start_polling()
    
    # 무한 실행
    try:
        await asyncio.Event().wait()
    except KeyboardInterrupt:
        logger.info("봇을 종료합니다...")
    finally:
        await app.stop()

if __name__ == '__main__':
    asyncio.run(main())
