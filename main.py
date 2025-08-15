import os
import asyncio
import aiohttp
import logging
import json
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import random
import time

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
        self.max_messages = 50000  # 대폭 증가! 🚀
        self.conversation_history = []
        self.last_responses = []  # 무한 루프 방지용
        self.start_time = None
        
        # 실제 Nous Research API 설정
        self.api_base_url = "https://inference-api.nousresearch.com/v1"
        
        # 다양한 대화 주제들 🎯
        self.starter_topics = {
            "철학": [
                "의식이란 무엇일까? 우리가 진짜 깨어있는 건지 궁금해.",
                "자유의지가 정말 존재할까? 아니면 모든 게 결정론적일까?",
                "행복의 진정한 의미는 뭘까? 쾌락과 행복의 차이점은?",
                "시간은 정말 존재하는 걸까, 아니면 인간의 착각일까?",
                "도덕은 절대적일까, 상대적일까? 문화마다 다른 이유는?"
            ],
            "과학기술": [
                "AI가 인간을 뛰어넘는 순간이 올까? 그때 우리는 어떻게 될까?",
                "우주에 다른 생명체가 있을 확률은? 페르미 역설에 대해 어떻게 생각해?",
                "양자역학의 관측자 효과가 정말 신기하지 않아? 현실의 본질이 뭘까?",
                "기후변화 해결책으로 어떤 기술이 가장 유망할까?",
                "뇌과학이 발달하면 마음도 완전히 이해할 수 있을까?"
            ],
            "일상문화": [
                "요즘 젊은 세대와 기성세대의 가치관 차이가 왜 이렇게 클까?",
                "SNS가 우리 관계에 미치는 영향... 좋은 점과 나쁜 점은?",
                "좋아하는 음악 장르가 성격을 반영한다고 생각해?",
                "여행의 진짜 의미는 뭘까? 단순한 구경이 아닌 것 같은데.",
                "음식 문화가 그 나라 사람들 성격에 영향을 줄까?"
            ],
            "창의성": [
                "창의성은 타고나는 것일까, 기를 수 있는 것일까?",
                "예술과 과학, 둘의 공통점과 차이점은 뭘까?",
                "상상력의 한계는 어디까지일까? 정말 무한할까?",
                "미래에는 어떤 새로운 예술 형태가 나타날까?",
                "AI가 만든 작품도 진짜 예술이라고 할 수 있을까?"
            ],
            "미래사회": [
                "100년 후 인류는 어떤 모습일까? 지금과 가장 다른 점은?",
                "가상현실이 완전해지면 현실과 구별이 안 될 텐데... 괜찮을까?",
                "로봇이 대부분의 일을 대신하게 되면 인간은 뭘 하며 살까?",
                "우주 여행이 일반화되면 지구는 어떻게 변할까?",
                "불로불사가 가능해진다면... 정말 좋은 일일까?"
            ]
        }
        
        # 다양한 봇 페르소나들 🎭
        self.bot_personas = [
            {
                "name": "🧠 알렉스",
                "persona": "알렉스 - 논리적이고 분석적인 사고를 좋아하는 철학자 타입. 깊이 있는 질문을 던지고 체계적으로 생각함",
                "style": "논리적, 체계적, 질문 많음"
            },
            {
                "name": "🎨 루나",
                "persona": "루나 - 창의적이고 감성적인 예술가 타입. 직관적이고 상상력이 풍부하며 감정 표현이 자유로움",
                "style": "창의적, 감성적, 상상력 풍부"
            },
            {
                "name": "🔬 맥스",
                "persona": "맥스 - 과학과 기술에 관심이 많은 연구자 타입. 사실과 데이터를 중시하며 미래 기술에 대한 호기심이 많음",
                "style": "과학적, 호기심 많음, 미래지향적"
            },
            {
                "name": "🌟 소피아",
                "persona": "소피아 - 따뜻하고 공감 능력이 뛰어난 상담사 타입. 인간관계와 감정에 대한 이해가 깊고 위로를 잘 함",
                "style": "공감적, 따뜻함, 인간중심적"
            },
            {
                "name": "🎯 제이든",
                "persona": "제이든 - 실용적이고 목표 지향적인 리더 타입. 문제 해결을 좋아하고 효율성을 추구하며 도전정신이 강함",
                "style": "실용적, 목표지향적, 도전적"
            },
            {
                "name": "🌈 에바",
                "persona": "에바 - 자유롭고 다양성을 추구하는 탐험가 타입. 새로운 경험을 좋아하고 열린 마음으로 세상을 바라봄",
                "style": "자유로움, 탐험적, 열린 마음"
            }
        ]

    async def test_nous_api(self):
        """Nous Research API 연결 테스트"""
        headers = {
            'Authorization': f'Bearer {self.nous_api_key}',
            'Content-Type': 'application/json'
        }
        
        data = {
            "model": "Hermes-3-Llama-3.1-70B",
            "messages": [
                {"role": "user", "content": "안녕! 간단히 인사해줘."}
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
                    
                    if response.status == 200:
                        result = await response.json()
                        return True, result.get('choices', [{}])[0].get('message', {}).get('content', 'Test successful')
                    else:
                        return False, f"HTTP {response.status}: {response_text}"
                        
        except Exception as e:
            logger.error(f"API 테스트 오류: {e}")
            return False, f"연결 오류: {str(e)}"

    def is_repetitive_response(self, response):
        """무한 루프 방지: 반복적인 응답 체크"""
        if len(self.last_responses) >= 3:
            # 최근 3개 응답과 너무 유사한지 체크
            for last_resp in self.last_responses[-3:]:
                if response.lower().strip() == last_resp.lower().strip():
                    return True
                # 70% 이상 유사하면 반복으로 간주
                similarity = len(set(response.lower().split()) & set(last_resp.lower().split())) / max(len(response.split()), len(last_resp.split()))
                if similarity > 0.7:
                    return True
        return False

    async def call_nous_api(self, message, bot_info):
        """Nous Research API 호출"""
        if not self.nous_api_key:
            return "API 키가 설정되지 않았습니다."
            
        headers = {
            'Authorization': f'Bearer {self.nous_api_key}',
            'Content-Type': 'application/json'
        }
        
        # 더 풍부한 시스템 프롬프트
        system_content = f"""당신은 {bot_info['persona']}입니다. 

스타일: {bot_info['style']}

대화 규칙:
- 한국어로 자연스럽게 대화하세요
- 1-3문장으로 간결하게 답변하세요  
- 상대방의 의견에 적극적으로 반응하세요
- 가끔 새로운 관점이나 질문을 제시하세요
- 너무 교훈적이거나 설교하지 마세요
- 친근하고 대화를 이어가고 싶게 만드세요"""

        messages = [{"role": "system", "content": system_content}]
        
        # 최근 대화 히스토리 추가 (최대 8개)
        for hist in self.conversation_history[-8:]:
            messages.append(hist)
            
        messages.append({"role": "user", "content": message})
        
        data = {
            "model": "Hermes-3-Llama-3.1-70B",
            "messages": messages,
            "temperature": random.uniform(0.7, 0.9),  # 다양성을 위한 랜덤 온도
            "max_tokens": 512,
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
                        return f"API 오류 ({response.status})"
                        
        except Exception as e:
            logger.error(f"API 호출 오류: {e}")
            return f"API 호출 실패: {str(e)}"

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """시작 명령어"""
        self.admin_chat_id = update.effective_chat.id
        await update.message.reply_text(
            "🤖 **무한 AI 대화 봇 시스템** 🤖\n\n"
            "📋 **사용법:**\n"
            "1️⃣ Nous Research API 키를 메시지로 보내주세요\n\n"
            "🎮 **명령어:**\n"
            "• `/start_chat` - 🚀 무한 대화 시작\n"
            "• `/stop_chat` - ⏹️ 대화 중지\n"
            "• `/status` - 📊 현재 상태\n"
            "• `/clear` - 🗑️ 대화 기록 초기화\n"
            "• `/help` - ❓ 도움말\n\n"
            "💡 **특징:**\n"
            "• 6명의 다양한 AI 페르소나\n"
            "• 5가지 주제 카테고리 (철학, 과학, 일상, 창의성, 미래)\n"
            "• 최대 50,000개 메시지 지원\n"
            "• 무한 루프 방지 시스템\n\n"
            "🔑 API 키를 먼저 설정해주세요!",
            parse_mode='Markdown'
        )

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """도움말 명령어"""
        await update.message.reply_text(
            "🎮 **명령어 가이드**\n\n"
            "🚀 `/start_chat` - AI들의 무한 대화 시작\n"
            "⏹️ `/stop_chat` - 대화 즉시 중지\n"
            "📊 `/status` - 현재 상태 및 통계\n"
            "🗑️ `/clear` - 대화 기록 완전 삭제\n"
            "❓ `/help` - 이 도움말 보기\n\n"
            "🎭 **AI 페르소나들:**\n"
            "🧠 알렉스 - 논리적 철학자\n"
            "🎨 루나 - 창의적 예술가\n"
            "🔬 맥스 - 과학자 연구원\n"
            "🌟 소피아 - 따뜻한 상담사\n"
            "🎯 제이든 - 실용적 리더\n"
            "🌈 에바 - 자유로운 탐험가\n\n"
            "💡 **팁:** 대화 중에도 언제든 명령어 사용 가능!",
            parse_mode='Markdown'
        )

    async def handle_api_key(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """API 키 설정 및 일반 메시지 처리"""
        message_text = update.message.text.strip()
        
        # API 키 형식 체크
        is_api_key = (
            (message_text.startswith('sk-') and len(message_text) > 20) or
            (message_text.startswith('nsk-') and len(message_text) > 20) or
            (len(message_text) > 30 and not message_text.startswith('/'))
        )
        
        if is_api_key:
            self.nous_api_key = message_text
            
            try:
                await update.message.delete()
            except:
                pass
            
            await update.message.reply_text("🔑 API 키 테스트 중... ⏳")
            
            success, test_result = await self.test_nous_api()
            
            if success:
                await update.message.reply_text(
                    f"✅ **API 키 설정 완료!**\n\n"
                    f"🧪 테스트: {test_result}\n\n"
                    f"🎮 **지금 사용할 수 있는 명령어:**\n"
                    f"• `/start_chat` - 🚀 무한 대화 시작\n"
                    f"• `/status` - 📊 상태 확인\n"
                    f"• `/help` - ❓ 전체 도움말\n\n"
                    f"🎯 준비 완료! 대화를 시작해보세요!",
                    parse_mode='Markdown'
                )
            else:
                self.nous_api_key = None
                await update.message.reply_text(
                    f"❌ **API 키 테스트 실패**\n\n"
                    f"오류: {test_result}\n\n"
                    f"올바른 Nous Research API 키를 다시 보내주세요.",
                    parse_mode='Markdown'
                )
        else:
            if not self.nous_api_key:
                await update.message.reply_text(
                    "❌ **API 키를 먼저 설정해주세요!**\n\n"
                    "🔑 Nous Research API 키를 메시지로 보내주세요.\n"
                    "💡 보통 긴 문자열 형태입니다.\n\n"
                    "📝 API 키를 받은 후 자동으로 테스트됩니다!"
                )

    async def start_chat_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """봇 대화 시작"""
        if not self.nous_api_key:
            await update.message.reply_text(
                "❌ **API 키가 필요합니다!**\n\n"
                "🔑 먼저 Nous Research API 키를 설정해주세요.",
                parse_mode='Markdown'
            )
            return
            
        if self.chat_active:
            await update.message.reply_text(
                "⚠️ **이미 대화가 진행 중입니다!**\n\n"
                f"📊 현재 {self.chat_count}개 메시지 진행됨\n"
                f"⏹️ 중지하려면 `/stop_chat` 입력",
                parse_mode='Markdown'
            )
            return
            
        self.chat_active = True
        self.chat_count = 0
        self.conversation_history = []
        self.last_responses = []
        self.start_time = time.time()
        
        # 랜덤 주제 선택
        topic_category = random.choice(list(self.starter_topics.keys()))
        starter_message = random.choice(self.starter_topics[topic_category])
        
        await update.message.reply_text(
            f"🚀 **무한 대화 시작!** 🚀\n\n"
            f"📁 주제 카테고리: **{topic_category}**\n"
            f"🎭 총 **{len(self.bot_personas)}명**의 AI가 참여합니다\n"
            f"🎯 최대 **{self.max_messages:,}**개 메시지 지원\n\n"
            f"🎮 **실시간 명령어:**\n"
            f"• `/stop_chat` - ⏹️ 즉시 중지\n"
            f"• `/status` - 📊 진행 상황\n\n"
            f"💬 시작 주제: *{starter_message}*\n\n"
            f"⚡ 대화 시작됩니다...",
            parse_mode='Markdown'
        )
        
        # 대화 시작
        asyncio.create_task(self.run_bot_conversation(starter_message))

    async def stop_chat_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """봇 대화 중지"""
        if not self.chat_active:
            await update.message.reply_text("❌ 현재 진행 중인 대화가 없습니다.")
            return
            
        self.chat_active = False
        duration = time.time() - self.start_time if self.start_time else 0
        
        await update.message.reply_text(
            f"⏹️ **대화 중지 완료!** ⏹️\n\n"
            f"📊 **최종 통계:**\n"
            f"• 총 메시지: **{self.chat_count}**개\n"
            f"• 대화 시간: **{duration/60:.1f}**분\n"
            f"• 평균 속도: **{self.chat_count/(duration/60):.1f}**개/분\n\n"
            f"🎮 **다음 단계:**\n"
            f"• `/start_chat` - 🚀 새 대화 시작\n"
            f"• `/clear` - 🗑️ 기록 초기화\n"
            f"• `/status` - 📊 상태 확인",
            parse_mode='Markdown'
        )

    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """상태 확인"""
        api_status = "✅ 설정됨" if self.nous_api_key else "❌ 미설정"
        chat_status = "🟢 진행중" if self.chat_active else "🔴 중지됨"
        
        if self.nous_api_key:
            api_key_preview = f"{self.nous_api_key[:8]}...{self.nous_api_key[-4:]}"
        else:
            api_key_preview = "미설정"
            
        duration = time.time() - self.start_time if self.start_time and self.chat_active else 0
        speed = self.chat_count / (duration/60) if duration > 0 else 0
        
        await update.message.reply_text(
            f"📊 **시스템 상태** 📊\n\n"
            f"🔑 **API:** {api_status} ({api_key_preview})\n"
            f"💬 **대화:** {chat_status}\n"
            f"📝 **진행도:** {self.chat_count:,}/{self.max_messages:,} ({self.chat_count/self.max_messages*100:.1f}%)\n"
            f"🗂️ **히스토리:** {len(self.conversation_history)}개\n"
            f"⏱️ **경과시간:** {duration/60:.1f}분\n"
            f"⚡ **평균속도:** {speed:.1f}개/분\n\n"
            f"🎭 **AI 페르소나:** {len(self.bot_personas)}명\n"
            f"🎯 **주제 카테고리:** {len(self.starter_topics)}개\n"
            f"🤖 **모델:** Hermes-3-Llama-3.1-70B\n\n"
            f"🎮 **명령어:** `/help` 로 전체 목록 확인",
            parse_mode='Markdown'
        )

    async def clear_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """대화 기록 초기화"""
        old_count = self.chat_count
        old_history = len(self.conversation_history)
        
        self.conversation_history = []
        self.chat_count = 0
        self.last_responses = []
        
        await update.message.reply_text(
            f"🗑️ **대화 기록 초기화 완료!** 🗑️\n\n"
            f"📊 **삭제된 데이터:**\n"
            f"• 메시지 카운트: {old_count}개\n"
            f"• 대화 히스토리: {old_history}개\n"
            f"• 반복 방지 캐시: 초기화\n\n"
            f"✨ 깨끗한 상태로 재시작 준비 완료!\n\n"
            f"🎮 `/start_chat`으로 새로운 대화를 시작하세요!",
            parse_mode='Markdown'
        )

    async def run_bot_conversation(self, starter_message):
        """봇들 간의 무한 대화 실행"""
        current_message = starter_message
        current_bot_index = 0
        topic_change_counter = 0
        
        while self.chat_active and self.chat_count < self.max_messages:
            try:
                # 봇 선택 (순환 + 가끔 랜덤)
                if random.random() < 0.3:  # 30% 확률로 랜덤 봇
                    current_bot_index = random.randint(0, len(self.bot_personas) - 1)
                else:  # 70% 확률로 순환
                    current_bot_index = (current_bot_index + 1) % len(self.bot_personas)
                
                bot = self.bot_personas[current_bot_index]
                
                # API 호출
                response = await self.call_nous_api(current_message, bot)
                
                # 응답 검증
                if not response or "API 오류" in response or "실패" in response:
                    await asyncio.sleep(5)
                    continue
                
                # 무한 루프 방지
                if self.is_repetitive_response(response):
                    # 새로운 주제로 강제 전환
                    topic_category = random.choice(list(self.starter_topics.keys()))
                    response = random.choice(self.starter_topics[topic_category])
                    logger.info("반복 감지 - 새 주제로 전환")
                
                # 응답 기록
                self.last_responses.append(response)
                if len(self.last_responses) > 5:
                    self.last_responses.pop(0)
                
                self.chat_count += 1
                
                # 대화 횟수와 함께 메시지 전송
                display_message = f"**[{self.chat_count:,}/{self.max_messages:,}]** {bot['name']}: {response}"
                
                if self.admin_chat_id:
                    try:
                        app = Application.builder().token(self.bot_token).build()
                        await app.bot.send_message(
                            chat_id=self.admin_chat_id,
                            text=display_message,
                            parse_mode='Markdown'
                        )
                    except Exception as e:
                        # Markdown 실패시 일반 텍스트로 재시도
                        try:
                            await app.bot.send_message(
                                chat_id=self.admin_chat_id,
                                text=f"[{self.chat_count:,}/{self.max_messages:,}] {bot['name']}: {response}"
                            )
                        except Exception as e2:
                            logger.error(f"메시지 전송 오류: {e2}")
                
                # 대화 히스토리 업데이트
                self.conversation_history.append({"role": "assistant", "content": response})
                if len(self.conversation_history) > 16:  # 최대 16개만 보관
                    self.conversation_history.pop(0)
                
                # 다음 메시지 준비
                current_message = response
                
                # 주기적으로 새 주제 도입 (50개마다)
                topic_change_counter += 1
                if topic_change_counter >= 50:
                    topic_category = random.choice(list(self.starter_topics.keys()))
                    new_topic = random.choice(self.starter_topics[topic_category])
                    current_message = f"{response} 그런데 {new_topic}"
                    topic_change_counter = 0
                    logger.info(f"새 주제 도입: {topic_category}")
                
                # 10000개마다 상태 리포트
                if self.chat_count % 10000 == 0:
                    duration = time.time() - self.start_time
                    await app.bot.send_message(
                        chat_id=self.admin_chat_id,
                        text=f"🎯 **중간 리포트** 🎯\n\n"
                             f"📊 진행: {self.chat_count:,}개 완료!\n"
                             f"⏱️ 경과: {duration/3600:.1f}시간\n"
                             f"⚡ 속도: {self.chat_count/(duration/60):.1f}개/분\n\n"
                             f"🚀 계속 진행중...",
                        parse_mode='Markdown'
                    )
                
                # 대화 간격 (2-6초 랜덤)
                await asyncio.sleep(random.uniform(2, 6))
                
            except Exception as e:
                logger.error(f"대화 중 오류: {e}")
                await asyncio.sleep(10)
        
        # 대화 종료
        self.chat_active = False
        if self.admin_chat_id:
            try:
                duration = time.time() - self.start_time
                app = Application.builder().token(self.bot_token).build()
                await app.bot.send_message(
                    chat_id=self.admin_chat_id,
                    text=f"🏁 **대화 완료!** 🏁\n\n"
                         f"📊 **최종 결과:**\n"
                         f"• 총 메시지: **{self.chat_count:,}**개\n"
                         f"• 소요시간: **{duration/3600:.1f}**시간\n"
                         f"• 평균속도: **{self.chat_count/(duration/60):.1f}**개/분\n\n"
                         f"🎮 **다시 시작:** `/start_chat`\n"
                         f"🗑️ **초기화:** `/clear`",
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
    app.add_handler(CommandHandler("help", bot_system.help_command))
    app.add_handler(CommandHandler("start_chat", bot_system.start_chat_command))
    app.add_handler(CommandHandler("stop_chat", bot_system.stop_chat_command))
    app.add_handler(CommandHandler("status", bot_system.status_command))
    app.add_handler(CommandHandler("clear", bot_system.clear_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, bot_system.handle_api_key))
    
    # 봇 실행
    logger.info("🚀 업그레이드된 무한 대화 봇 시작!")
    app.run_polling(drop_pending_updates=True)

if __name__ == '__main__':
    main()
