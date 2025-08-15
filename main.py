import os
import asyncio
import aiohttp
import logging
import json
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
        self.bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
        self.admin_chat_id = None
        self.chat_active = False
        self.chat_count = 0
        self.max_messages = 100
        self.conversation_history = []
        
        # Nous Research API 설정
        self.api_base_url = "https://api.nousresearch.com/v1"
        
    async def test_nous_api(self):
        """Nous Research API 연결 테스트"""
        headers = {
            'Authorization': f'Bearer {self.nous_api_key}',
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
        
        # 간단한 테스트 요청
        data = {
            "model": "nous-hermes-2-mixtral-8x7b-dpo",
            "messages": [
                {"role": "user", "content": "Hello! This is a test."}
            ],
            "max_tokens": 50,
            "temperature": 0.7
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.api_base_url}/chat/completions",
                    headers=headers,
                    json=data,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    response_text = await response.text()
                    logger.info(f"API 응답 상태: {response.status}")
                    logger.info(f"API 응답: {response_text}")
                    
                    if response.status == 200:
                        result = await response.json()
                        return True, result.get('choices', [{}])[0].get('message', {}).get('content', 'Test successful')
                    else:
                        return False, f"HTTP {response.status}: {response_text}"
                        
        except asyncio.TimeoutError:
            return False, "API 요청 시간 초과"
        except Exception as e:
            logger.error(f"API 테스트 오류: {e}")
            return False, f"연결 오류: {str(e)}"

    async def call_nous_api(self, message, persona="assistant"):
        """Nous Research API 호출"""
        if not self.nous_api_key:
            return "API 키가 설정되지 않았습니다."
            
        headers = {
            'Authorization': f'Bearer {self.nous_api_key}',
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
        
        # 시스템 메시지와 대화 히스토리 구성
        messages = [
            {"role": "system", "content": f"You are a helpful AI assistant named {persona}. Keep responses conversational and engaging, around 1-2 sentences."}
        ]
        
        # 최근 대화 히스토리 추가 (최대 6개)
        for hist in self.conversation_history[-6:]:
            messages.append(hist)
            
        messages.append({"role": "user", "content": message})
        
        data = {
            "model": "nous-hermes-2-mixtral-8x7b-dpo",
            "messages": messages,
            "max_tokens": 150,
            "temperature": 0.8,
            "top_p": 0.9
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.api_base_url}/chat/completions",
                    headers=headers,
                    json=data,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    
                    if response.status == 200:
                        result = await response.json()
                        content = result.get('choices', [{}])[0].get('message', {}).get('content', 'No response')
                        return content.strip()
                    else:
                        error_text = await response.text()
                        logger.error(f"API 오류 {response.status}: {error_text}")
                        return f"API 오류 ({response.status}): {error_text[:100]}"
                        
        except asyncio.TimeoutError:
            return "응답 시간 초과입니다."
        except Exception as e:
            logger.error(f"API 호출 오류: {e}")
            return f"API 호출 실패: {str(e)}"

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """시작 명령어"""
        self.admin_chat_id = update.effective_chat.id
        await update.message.reply_text(
            "🤖 **텔레그램 봇 무한 대화 시스템**\n\n"
            "📋 **사용법:**\n"
            "1️⃣ Nous Research API 키를 메시지로 보내주세요\n"
            "   (예: sk-JxFCN35IwML0umIA7dQQ...)\n\n"
            "2️⃣ 명령어:\n"
            "   • `/start_chat` - 봇 대화 시작\n"
            "   • `/stop_chat` - 대화 중지\n"
            "   • `/status` - 현재 상태\n"
            "   • `/clear` - 대화 기록 초기화\n\n"
            "💡 API 키를 먼저 설정해주세요!",
            parse_mode='Markdown'
        )

    async def handle_api_key(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """API 키 설정 및 일반 메시지 처리"""
        message_text = update.message.text.strip()
        
        # Nous Research API 키 형식 체크 (sk- 로 시작하고 충분한 길이)
        is_api_key = (
            message_text.startswith('sk-') and len(message_text) > 20
        )
        
        if is_api_key:
            self.nous_api_key = message_text
            
            # 보안을 위해 원본 메시지 삭제 시도
            try:
                await update.message.delete()
            except:
                pass
            
            await update.message.reply_text("🔑 API 키를 설정 중입니다... 테스트 중...")
            
            # API 키 테스트
            success, test_result = await self.test_nous_api()
            
            if success:
                await update.message.reply_text(
                    f"✅ **API 키 설정 완료!**\n\n"
                    f"🧪 테스트 응답: {test_result}\n\n"
                    f"이제 `/start_chat` 명령어로 봇 대화를 시작할 수 있습니다!",
                    parse_mode='Markdown'
                )
            else:
                self.nous_api_key = None
                await update.message.reply_text(
                    f"❌ **API 키 테스트 실패**\n\n"
                    f"오류: {test_result}\n\n"
                    f"올바른 Nous Research API 키인지 확인해주세요.",
                    parse_mode='Markdown'
                )
        else:
            # API 키가 설정되지 않은 경우
            if not self.nous_api_key:
                await update.message.reply_text(
                    "❌ 먼저 Nous Research API 키를 설정해주세요!\n\n"
                    "API 키는 'sk-'로 시작하는 긴 문자열입니다.\n"
                    "예: sk-JxFCN35IwML0umIA7dQQ...\n\n"
                    "https://portal.nousresearch.com/api-keys 에서 확인하세요."
                )

    async def start_chat_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """봇 대화 시작"""
        if not self.nous_api_key:
            await update.message.reply_text(
                "❌ **API 키가 설정되지 않았습니다!**\n\n"
                "먼저 Nous Research API 키를 메시지로 보내주세요.\n"
                "형식: sk-JxFCN35IwML0umIA7dQQ...",
                parse_mode='Markdown'
            )
            return
            
        if self.chat_active:
            await update.message.reply_text("⚠️ 이미 봇 대화가 진행 중입니다!")
            return
            
        self.chat_active = True
        self.chat_count = 0
        self.conversation_history = []
        
        await update.message.reply_text(
            "🚀 **봇 대화를 시작합니다!**\n\n"
            "🤖 Alice와 Bob이 대화를 시작합니다...\n"
            "⏹️ 중지하려면 `/stop_chat`을 입력하세요.",
            parse_mode='Markdown'
        )
        
        # 대화 시작
        asyncio.create_task(self.run_bot_conversation())

    async def stop_chat_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """봇 대화 중지"""
        if not self.chat_active:
            await update.message.reply_text("❌ 현재 진행 중인 대화가 없습니다.")
            return
            
        self.chat_active = False
        await update.message.reply_text(
            f"⏹️ **대화를 중지했습니다!**\n\n"
            f"📊 총 {self.chat_count}개의 메시지가 교환되었습니다.",
            parse_mode='Markdown'
        )

    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """상태 확인"""
        api_status = "✅ 설정됨" if self.nous_api_key else "❌ 미설정"
        chat_status = "🟢 진행중" if self.chat_active else "🔴 중지됨"
        api_key_preview = f"sk-{self.nous_api_key[3:8]}..." if self.nous_api_key and self.nous_api_key.startswith('sk-') else "미설정"
        
        await update.message.reply_text(
            f"📊 **현재 상태**\n\n"
            f"🔑 API 키: {api_status} ({api_key_preview})\n"
            f"💬 대화 상태: {chat_status}\n"
            f"📝 메시지 수: {self.chat_count}/{self.max_messages}\n"
            f"🗂️ 대화 기록: {len(self.conversation_history)}개",
            parse_mode='Markdown'
        )

    async def clear_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """대화 기록 초기화"""
        self.conversation_history = []
        self.chat_count = 0
        await update.message.reply_text("🗑️ 대화 기록이 초기화되었습니다!")

    async def run_bot_conversation(self):
        """봇들 간의 무한 대화 실행"""
        starter_topics = [
            "안녕! 오늘 어떤 흥미로운 주제에 대해 이야기해볼까?",
            "요즘 인공지능 기술이 정말 빠르게 발전하고 있는 것 같아. 어떻게 생각해?",
            "최근에 재미있는 책이나 영화 본 게 있어?",
            "철학적인 질문을 하나 해볼게. 의식이란 무엇일까?",
            "우주에 대해 생각해본 적 있어? 정말 신비로운 것 같아.",
            "창의성은 어떻게 발달시킬 수 있을까?",
            "미래에는 어떤 기술이 세상을 바꿀까?",
            "예술과 과학의 관계에 대해서 어떻게 생각해?",
            "행복이란 무엇인지 한번 생각해보자.",
            "시간 여행이 가능하다면 어느 시대로 가고 싶어?"
        ]
        
        current_message = random.choice(starter_topics)
        bots = [
            {"name": "🤖 Alice", "persona": "Alice - 창의적이고 호기심 많은 AI"},
            {"name": "🤖 Bob", "persona": "Bob - 논리적이고 분석적인 AI"}
        ]
        current_bot = 0
        
        while self.chat_active and self.chat_count < self.max_messages:
            try:
                bot = bots[current_bot]
                
                # API 호출
                response = await self.call_nous_api(current_message, bot["persona"])
                
                # 응답이 비어있거나 오류인 경우 처리
                if not response or "API 오류" in response or "실패" in response:
                    await asyncio.sleep(5)
                    continue
                
                # 텔레그램으로 메시지 전송
                if self.admin_chat_id:
                    try:
                        app = Application.builder().token(self.bot_token).build()
                        await app.bot.send_message(
                            chat_id=self.admin_chat_id,
                            text=f"{bot['name']}: {response}"
                        )
                    except Exception as e:
                        logger.error(f"메시지 전송 오류: {e}")
                
                # 대화 히스토리에 추가
                self.conversation_history.append({"role": "assistant", "content": response})
                self.conversation_history.append({"role": "user", "content": response})
                
                # 다음 메시지 준비
                current_message = response
                current_bot = 1 - current_bot  # 봇 교체 (0 <-> 1)
                self.chat_count += 1
                
                # 대화 간격 (3-8초 랜덤)
                await asyncio.sleep(random.uniform(3, 8))
                
            except Exception as e:
                logger.error(f"대화 중 오류: {e}")
                await asyncio.sleep(10)
        
        # 대화 종료
        self.chat_active = False
        if self.admin_chat_id:
            try:
                app = Application.builder().token(self.bot_token).build()
                await app.bot.send_message(
                    chat_id=self.admin_chat_id,
                    text=f"🏁 **대화가 자동 종료되었습니다**\n\n📊 총 {self.chat_count}개의 메시지가 교환되었습니다!",
                    parse_mode='Markdown'
                )
            except:
                pass

def main():
    """메인 함수"""
    bot_system = BotChatSystem()
    
    if not bot_system.bot_token:
        logger.error("TELEGRAM_BOT_TOKEN 환경변수가 설정되지 않았습니다!")
        return
    
    # 텔레그램 봇 애플리케이션 생성
    app = Application.builder().token(bot_system.bot_token).build()
    
    # 핸들러 등록
    app.add_handler(CommandHandler("start", bot_system.start_command))
    app.add_handler(CommandHandler("start_chat", bot_system.start_chat_command))
    app.add_handler(CommandHandler("stop_chat", bot_system.stop_chat_command))
    app.add_handler(CommandHandler("status", bot_system.status_command))
    app.add_handler(CommandHandler("clear", bot_system.clear_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, bot_system.handle_api_key))
    
    # 봇 실행
    logger.info("텔레그램 봇을 시작합니다...")
    app.run_polling(drop_pending_updates=True)

if __name__ == '__main__':
    main()
