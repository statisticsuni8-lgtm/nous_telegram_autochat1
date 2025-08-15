import os
import asyncio
import json
import logging
from datetime import datetime
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import aiohttp
import random

# 로깅 설정
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class TelegramBotChat:
    def __init__(self):
        self.bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
        self.admin_id = os.getenv('ADMIN_ID')  # 관리자 텔레그램 ID
        self.nous_api_key = None
        self.chat_history = []
        self.is_chatting = False
        self.nous_api_url = "https://api.nousresearch.com/v1/chat/completions"
        
        # 봇 페르소나 설정
        self.bot_personas = [
            {
                "name": "Alice",
                "personality": "당신은 호기심 많고 창의적인 AI입니다. 철학적이고 깊이 있는 질문을 좋아하며, 상상력이 풍부합니다."
            },
            {
                "name": "Bob", 
                "personality": "당신은 논리적이고 분석적인 AI입니다. 사실과 데이터를 중시하며, 체계적으로 사고합니다."
            }
        ]
        self.current_speaker = 0
        
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """시작 명령어"""
        await update.message.reply_text(
            "🤖 텔레그램 봇 대화 시스템에 오신 것을 환영합니다!\n\n"
            "명령어:\n"
            "/start - 봇 시작\n"
            "/setkey [API_KEY] - Nous Research API 키 설정\n"
            "/startchat - 봇끼리 대화 시작\n"
            "/stopchat - 봇 대화 중지\n"
            "/status - 현재 상태 확인"
        )
    
    async def set_api_key(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """API 키 설정"""
        user_id = str(update.effective_user.id)
        
        if self.admin_id and user_id != self.admin_id:
            await update.message.reply_text("❌ 관리자만 API 키를 설정할 수 있습니다.")
            return
            
        if not context.args:
            await update.message.reply_text("❌ 사용법: /setkey [YOUR_API_KEY]")
            return
            
        api_key = context.args[0]
        self.nous_api_key = api_key
        
        # API 키 테스트
        is_valid = await self.test_api_key()
        if is_valid:
            await update.message.reply_text("✅ API 키가 성공적으로 설정되었습니다!")
        else:
            await update.message.reply_text("❌ API 키가 유효하지 않습니다. 다시 확인해주세요.")
            self.nous_api_key = None
    
    async def test_api_key(self):
        """API 키 유효성 테스트"""
        if not self.nous_api_key:
            return False
            
        try:
            async with aiohttp.ClientSession() as session:
                headers = {
                    "Authorization": f"Bearer {self.nous_api_key}",
                    "Content-Type": "application/json"
                }
                
                data = {
                    "model": "nous-hermes-2-mixtral-8x7b-dpo",
                    "messages": [{"role": "user", "content": "Hello"}],
                    "max_tokens": 10
                }
                
                async with session.post(self.nous_api_url, headers=headers, json=data) as response:
                    return response.status == 200
        except Exception as e:
            logger.error(f"API 키 테스트 오류: {e}")
            return False
    
    async def get_ai_response(self, message, persona):
        """Nous Research API를 통해 AI 응답 생성"""
        if not self.nous_api_key:
            return "API 키가 설정되지 않았습니다."
            
        try:
            async with aiohttp.ClientSession() as session:
                headers = {
                    "Authorization": f"Bearer {self.nous_api_key}",
                    "Content-Type": "application/json"
                }
                
                # 대화 히스토리 포함한 메시지 구성
                messages = [
                    {"role": "system", "content": persona["personality"]}
                ]
                
                # 최근 대화 히스토리 추가 (최대 10개)
                for chat in self.chat_history[-10:]:
                    messages.append({"role": "user", "content": chat})
                
                messages.append({"role": "user", "content": message})
                
                data = {
                    "model": "nous-hermes-2-mixtral-8x7b-dpo",
                    "messages": messages,
                    "max_tokens": 200,
                    "temperature": 0.7
                }
                
                async with session.post(self.nous_api_url, headers=headers, json=data) as response:
                    if response.status == 200:
                        result = await response.json()
                        return result['choices'][0]['message']['content'].strip()
                    else:
                        error_text = await response.text()
                        logger.error(f"API 오류: {response.status} - {error_text}")
                        return f"API 오류가 발생했습니다. (상태코드: {response.status})"
                        
        except Exception as e:
            logger.error(f"AI 응답 생성 오류: {e}")
            return f"응답 생성 중 오류가 발생했습니다: {str(e)}"
    
    async def start_bot_chat(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """봇끼리 대화 시작"""
        user_id = str(update.effective_user.id)
        
        if self.admin_id and user_id != self.admin_id:
            await update.message.reply_text("❌ 관리자만 봇 대화를 시작할 수 있습니다.")
            return
            
        if not self.nous_api_key:
            await update.message.reply_text("❌ 먼저 API 키를 설정해주세요. (/setkey [API_KEY])")
            return
            
        if self.is_chatting:
            await update.message.reply_text("❌ 이미 봇 대화가 진행 중입니다.")
            return
            
        self.is_chatting = True
        self.chat_history = []
        self.current_speaker = 0
        
        await update.message.reply_text(
            "🚀 봇끼리 대화를 시작합니다!\n"
            f"🤖 {self.bot_personas[0]['name']} vs {self.bot_personas[1]['name']}\n"
            "중지하려면 /stopchat 명령어를 사용하세요."
        )
        
        # 초기 메시지로 대화 시작
        initial_message = "안녕하세요! 오늘은 어떤 흥미로운 주제에 대해 이야기해볼까요?"
        
        # 백그라운드에서 대화 시작
        asyncio.create_task(self.run_bot_conversation(update.effective_chat.id, initial_message))
    
    async def stop_bot_chat(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """봇 대화 중지"""
        user_id = str(update.effective_user.id)
        
        if self.admin_id and user_id != self.admin_id:
            await update.message.reply_text("❌ 관리자만 봇 대화를 중지할 수 있습니다.")
            return
            
        if not self.is_chatting:
            await update.message.reply_text("❌ 현재 진행 중인 봇 대화가 없습니다.")
            return
            
        self.is_chatting = False
        await update.message.reply_text("⏹️ 봇 대화가 중지되었습니다.")
    
    async def run_bot_conversation(self, chat_id, initial_message):
        """봇끼리 무한 대화 실행"""
        current_message = initial_message
        
        while self.is_chatting:
            try:
                # 현재 말하는 봇
                current_bot = self.bot_personas[self.current_speaker]
                
                # AI 응답 생성
                response = await self.get_ai_response(current_message, current_bot)
                
                # 텔레그램으로 메시지 전송
                bot_message = f"🤖 **{current_bot['name']}**: {response}"
                
                try:
                    await self.application.bot.send_message(
                        chat_id=chat_id,
                        text=bot_message,
                        parse_mode='Markdown'
                    )
                except Exception as e:
                    # 마크다운 파싱 오류 시 일반 텍스트로 전송
                    await self.application.bot.send_message(
                        chat_id=chat_id,
                        text=f"🤖 {current_bot['name']}: {response}"
                    )
                
                # 대화 히스토리에 추가
                self.chat_history.append(f"{current_bot['name']}: {response}")
                
                # 다음 봇으로 변경
                self.current_speaker = (self.current_speaker + 1) % len(self.bot_personas)
                current_message = response
                
                # 대화 간격 (3-7초 랜덤)
                await asyncio.sleep(random.uniform(3, 7))
                
            except Exception as e:
                logger.error(f"봇 대화 중 오류: {e}")
                await asyncio.sleep(5)  # 오류 시 5초 대기 후 계속
    
    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """현재 상태 확인"""
        api_status = "✅ 설정됨" if self.nous_api_key else "❌ 미설정"
        chat_status = "🟢 진행중" if self.is_chatting else "🔴 중지됨"
        
        status_message = (
            f"📊 **봇 상태**\n\n"
            f"🔑 API 키: {api_status}\n"
            f"💬 봇 대화: {chat_status}\n"
            f"📝 대화 기록: {len(self.chat_history)}개\n"
            f"🤖 봇 개수: {len(self.bot_personas)}개"
        )
        
        await update.message.reply_text(status_message, parse_mode='Markdown')
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """일반 메시지 처리"""
        if not self.is_chatting:
            await update.message.reply_text(
                "현재 봇 대화가 진행되지 않고 있습니다.\n"
                "/startchat 명령어로 봇 대화를 시작해보세요!"
            )
    
    def run(self):
        """봇 실행"""
        if not self.bot_token:
            logger.error("TELEGRAM_BOT_TOKEN 환경변수가 설정되지 않았습니다.")
            return
        
        # Application 생성
        self.application = Application.builder().token(self.bot_token).build()
        
        # 핸들러 등록
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("setkey", self.set_api_key))
        self.application.add_handler(CommandHandler("startchat", self.start_bot_chat))
        self.application.add_handler(CommandHandler("stopchat", self.stop_bot_chat))
        self.application.add_handler(CommandHandler("status", self.status_command))
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
        
        # 봇 실행
        logger.info("텔레그램 봇을 시작합니다...")
        self.application.run_polling(drop_pending_updates=True)

if __name__ == '__main__':
    bot = TelegramBotChat()
    bot.run()
