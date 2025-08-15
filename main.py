import os
import asyncio
import aiohttp
import logging
import json
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import random
import time
from typing import Dict, Any

# 로깅 설정
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class UserSession:
    """사용자별 세션 클래스"""
    def __init__(self, chat_id: int):
        self.chat_id = chat_id
        self.nous_api_key = None
        self.chat_active = False
        self.chat_count = 0
        self.max_messages = 50000
        self.conversation_history = []
        self.last_responses = []
        self.start_time = None
        self.current_task = None

class BotChatSystem:
    def __init__(self):
        self.bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
        self.user_sessions: Dict[int, UserSession] = {}  # 사용자별 세션 저장
        
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

    def get_user_session(self, chat_id: int) -> UserSession:
        """사용자별 세션 가져오기 (없으면 생성)"""
        if chat_id not in self.user_sessions:
            self.user_sessions[chat_id] = UserSession(chat_id)
            logger.info(f"새 사용자 세션 생성: {chat_id}")
        return self.user_sessions[chat_id]

    async def test_nous_api(self, api_key: str):
        """Nous Research API 연결 테스트"""
        headers = {
            'Authorization': f'Bearer {api_key}',
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
                    
                    if response.status == 200:
                        result = await response.json()
                        return True, result.get('choices', [{}])[0].get('message', {}).get('content', 'Test successful')
                    else:
                        response_text = await response.text()
                        return False, f"HTTP {response.status}: {response_text}"
                        
        except Exception as e:
            logger.error(f"API 테스트 오류: {e}")
            return False, f"연결 오류: {str(e)}"

    def is_repetitive_response(self, user_session: UserSession, response: str):
        """무한 루프 방지: 반복적인 응답 체크"""
        if len(user_session.last_responses) >= 3:
            for last_resp in user_session.last_responses[-3:]:
                if response.lower().strip() == last_resp.lower().strip():
                    return True
                similarity = len(set(response.lower().split()) & set(last_resp.lower().split())) / max(len(response.split()), len(last_resp.split()))
                if similarity > 0.7:
                    return True
        return False

    async def call_nous_api(self, user_session: UserSession, message: str, bot_info: dict):
        """Nous Research API 호출"""
        if not user_session.nous_api_key:
            return "API 키가 설정되지 않았습니다."
            
        headers = {
            'Authorization': f'Bearer {user_session.nous_api_key}',
            'Content-Type': 'application/json'
        }
        
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
        
        for hist in user_session.conversation_history[-8:]:
            messages.append(hist)
            
        messages.append({"role": "user", "content": message})
        
        data = {
            "model": "Hermes-3-Llama-3.1-70B",
            "messages": messages,
            "temperature": random.uniform(0.7, 0.9),
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
        chat_id = update.effective_chat.id
        user_session = self.get_user_session(chat_id)
        
        await update.message.reply_text(
            f"🤖 **다중 사용자 무한 AI 대화 봇** 🤖\n\n"
            f"👥 **다중 사용자 지원!** 여러 명이 동시에 사용 가능\n"
            f"🆔 당신의 세션 ID: `{chat_id}`\n\n"
            f"📋 **사용법:**\n"
            f"1️⃣ Nous Research API 키를 메시지로 보내주세요\n\n"
            f"🎮 **명령어:**\n"
            f"• `/start_chat` - 🚀 무한 대화 시작\n"
            f"• `/stop_chat` - ⏹️ 대화 중지\n"
            f"• `/status` - 📊 현재 상태\n"
            f"• `/clear` - 🗑️ 대화 기록 초기화\n"
            f"• `/help` - ❓ 도움말\n"
            f"• `/global_status` - 🌍 전체 사용자 현황\n\n"
            f"💡 **특징:**\n"
            f"• 6명의 다양한 AI 페르소나\n"
            f"• 5가지 주제 카테고리\n"
            f"• 최대 50,000개 메시지 지원\n"
            f"• 사용자별 독립적인 세션\n\n"
            f"🔑 API 키를 먼저 설정해주세요!",
            parse_mode='Markdown'
        )

    async def global_status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """전체 사용자 현황 명령어"""
        total_users = len(self.user_sessions)
        active_users = sum(1 for session in self.user_sessions.values() if session.chat_active)
        total_messages = sum(session.chat_count for session in self.user_sessions.values())
        
        status_text = f"🌍 **전체 시스템 현황** 🌍\n\n"
        status_text += f"👥 **총 사용자:** {total_users}명\n"
        status_text += f"🟢 **활성 대화:** {active_users}명\n"
        status_text += f"📝 **총 메시지:** {total_messages:,}개\n\n"
        
        if active_users > 0:
            status_text += f"🔥 **진행 중인 대화들:**\n"
            for chat_id, session in self.user_sessions.items():
                if session.chat_active:
                    duration = time.time() - session.start_time if session.start_time else 0
                    speed = session.chat_count / (duration/60) if duration > 0 else 0
                    status_text += f"• 사용자 `{chat_id}`: {session.chat_count:,}개 ({speed:.1f}/분)\n"
        
        await update.message.reply_text(status_text, parse_mode='Markdown')

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """도움말 명령어"""
        await update.message.reply_text(
            "🎮 **명령어 가이드**\n\n"
            "🚀 `/start_chat` - AI들의 무한 대화 시작\n"
            "⏹️ `/stop_chat` - 대화 즉시 중지\n"
            "📊 `/status` - 나의 현재 상태\n"
            "🌍 `/global_status` - 전체 사용자 현황\n"
            "🗑️ `/clear` - 대화 기록 완전 삭제\n"
            "❓ `/help` - 이 도움말 보기\n\n"
            "🎭 **AI 페르소나들:**\n"
            "🧠 알렉스 - 논리적 철학자\n"
            "🎨 루나 - 창의적 예술가\n"
            "🔬 맥스 - 과학자 연구원\n"
            "🌟 소피아 - 따뜻한 상담사\n"
            "🎯 제이든 - 실용적 리더\n"
            "🌈 에바 - 자유로운 탐험가\n\n"
            "💡 **다중 사용자:** 각자 독립적인 대화 진행!",
            parse_mode='Markdown'
        )

    async def handle_api_key(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """API 키 설정 및 일반 메시지 처리"""
        chat_id = update.effective_chat.id
        user_session = self.get_user_session(chat_id)
        message_text = update.message.text.strip()
        
        # API 키 형식 체크
        is_api_key = (
            (message_text.startswith('sk-') and len(message_text) > 20) or
            (message_text.startswith('nsk-') and len(message_text) > 20) or
            (len(message_text) > 30 and not message_text.startswith('/'))
        )
        
        if is_api_key:
            user_session.nous_api_key = message_text
            
            try:
                await update.message.delete()
            except:
                pass
            
            await update.message.reply_text("🔑 API 키 테스트 중... ⏳")
            
            success, test_result = await self.test_nous_api(message_text)
            
            if success:
                await update.message.reply_text(
                    f"✅ **API 키 설정 완료!**\n\n"
                    f"🆔 세션 ID: `{chat_id}`\n"
                    f"🧪 테스트: {test_result}\n\n"
                    f"🎮 **사용 가능한 명령어:**\n"
                    f"• `/start_chat` - 🚀 무한 대화 시작\n"
                    f"• `/status` - 📊 내 상태 확인\n"
                    f"• `/global_status` - 🌍 전체 현황\n"
                    f"• `/help` - ❓ 전체 도움말\n\n"
                    f"🎯 준비 완료! 대화를 시작해보세요!",
                    parse_mode='Markdown'
                )
            else:
                user_session.nous_api_key = None
                await update.message.reply_text(
                    f"❌ **API 키 테스트 실패**\n\n"
                    f"오류: {test_result}\n\n"
                    f"올바른 Nous Research API 키를 다시 보내주세요.",
                    parse_mode='Markdown'
                )
        else:
            if not user_session.nous_api_key:
                await update.message.reply_text(
                    f"❌ **API 키를 먼저 설정해주세요!**\n\n"
                    f"🆔 당신의 세션: `{chat_id}`\n"
                    f"🔑 Nous Research API 키를 메시지로 보내주세요.\n\n"
                    f"💡 각 사용자마다 별도의 API 키가 필요합니다!",
                    parse_mode='Markdown'
                )

    async def start_chat_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """봇 대화 시작"""
        chat_id = update.effective_chat.id
        user_session = self.get_user_session(chat_id)
        
        if not user_session.nous_api_key:
            await update.message.reply_text(
                f"❌ **API 키가 필요합니다!**\n\n"
                f"🆔 세션 ID: `{chat_id}`\n"
                f"🔑 먼저 Nous Research API 키를 설정해주세요.",
                parse_mode='Markdown'
            )
            return
            
        if user_session.chat_active:
            await update.message.reply_text(
                f"⚠️ **이미 대화가 진행 중입니다!**\n\n"
                f"📊 현재 {user_session.chat_count}개 메시지 진행됨\n"
                f"⏹️ 중지하려면 `/stop_chat` 입력",
                parse_mode='Markdown'
            )
            return
            
        user_session.chat_active = True
        user_session.chat_count = 0
        user_session.conversation_history = []
        user_session.last_responses = []
        user_session.start_time = time.time()
        
        # 랜덤 주제 선택
        topic_category = random.choice(list(self.starter_topics.keys()))
        starter_message = random.choice(self.starter_topics[topic_category])
        
        await update.message.reply_text(
            f"🚀 **무한 대화 시작!** 🚀\n\n"
            f"🆔 세션 ID: `{chat_id}`\n"
            f"📁 주제: **{topic_category}**\n"
            f"🎭 총 **{len(self.bot_personas)}명**의 AI 참여\n"
            f"🎯 최대 **{user_session.max_messages:,}**개 메시지\n\n"
            f"🎮 **실시간 명령어:**\n"
            f"• `/stop_chat` - ⏹️ 즉시 중지\n"
            f"• `/status` - 📊 진행 상황\n\n"
            f"💬 시작 주제: *{starter_message}*\n\n"
            f"⚡ 대화 시작됩니다...",
            parse_mode='Markdown'
        )
        
        # 대화 시작 (비동기 태스크로 실행)
        user_session.current_task = asyncio.create_task(
            self.run_bot_conversation(user_session, starter_message)
        )

    async def stop_chat_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """봇 대화 중지"""
        chat_id = update.effective_chat.id
        user_session = self.get_user_session(chat_id)
        
        if not user_session.chat_active:
            await update.message.reply_text("❌ 현재 진행 중인 대화가 없습니다.")
            return
            
        user_session.chat_active = False
        
        # 실행 중인 태스크 취소
        if user_session.current_task:
            user_session.current_task.cancel()
            
        duration = time.time() - user_session.start_time if user_session.start_time else 0
        
        await update.message.reply_text(
            f"⏹️ **대화 중지 완료!** ⏹️\n\n"
            f"🆔 세션 ID: `{chat_id}`\n"
            f"📊 **최종 통계:**\n"
            f"• 총 메시지: **{user_session.chat_count}**개\n"
            f"• 대화 시간: **{duration/60:.1f}**분\n"
            f"• 평균 속도: **{user_session.chat_count/(duration/60):.1f}**개/분\n\n"
            f"🎮 **다음 단계:**\n"
            f"• `/start_chat` - 🚀 새 대화 시작\n"
            f"• `/clear` - 🗑️ 기록 초기화\n"
            f"• `/global_status` - 🌍 전체 현황",
            parse_mode='Markdown'
        )

    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """상태 확인"""
        chat_id = update.effective_chat.id
        user_session = self.get_user_session(chat_id)
        
        api_status = "✅ 설정됨" if user_session.nous_api_key else "❌ 미설정"
        chat_status = "🟢 진행중" if user_session.chat_active else "🔴 중지됨"
        
        if user_session.nous_api_key:
            api_key_preview = f"{user_session.nous_api_key[:8]}...{user_session.nous_api_key[-4:]}"
        else:
            api_key_preview = "미설정"
            
        duration = time.time() - user_session.start_time if user_session.start_time and user_session.chat_active else 0
        speed = user_session.chat_count / (duration/60) if duration > 0 else 0
        
        await update.message.reply_text(
            f"📊 **내 세션 상태** 📊\n\n"
            f"🆔 **세션 ID:** `{chat_id}`\n"
            f"🔑 **API:** {api_status} ({api_key_preview})\n"
            f"💬 **대화:** {chat_status}\n"
            f"📝 **진행도:** {user_session.chat_count:,}/{user_session.max_messages:,} ({user_session.chat_count/user_session.max_messages*100:.1f}%)\n"
            f"🗂️ **히스토리:** {len(user_session.conversation_history)}개\n"
            f"⏱️ **경과시간:** {duration/60:.1f}분\n"
            f"⚡ **평균속도:** {speed:.1f}개/분\n\n"
            f"🌍 전체 현황을 보려면 `/global_status` 입력",
            parse_mode='Markdown'
        )

    async def clear_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """대화 기록 초기화"""
        chat_id = update.effective_chat.id
        user_session = self.get_user_session(chat_id)
        
        old_count = user_session.chat_count
        old_history = len(user_session.conversation_history)
        
        user_session.conversation_history = []
        user_session.chat_count = 0
        user_session.last_responses = []
        
        await update.message.reply_text(
            f"🗑️ **내 대화 기록 초기화 완료!** 🗑️\n\n"
            f"🆔 세션 ID: `{chat_id}`\n"
            f"📊 **삭제된 데이터:**\n"
            f"• 메시지 카운트: {old_count}개\n"
            f"• 대화 히스토리: {old_history}개\n"
            f"• 반복 방지 캐시: 초기화\n\n"
            f"✨ 깨끗한 상태로 재시작 준비 완료!\n\n"
            f"🎮 `/start_chat`으로 새로운 대화를 시작하세요!",
            parse_mode='Markdown'
        )

    async def run_bot_conversation(self, user_session: UserSession, starter_message: str):
        """봇들 간의 무한 대화 실행 (사용자별)"""
        try:
            current_message = starter_message
            current_bot_index = 0
            topic_change_counter = 0
            
            while user_session.chat_active and user_session.chat_count < user_session.max_messages:
                try:
                    # 봇 선택
                    if random.random() < 0.3:
                        current_bot_index = random.randint(0, len(self.bot_personas) - 1)
                    else:
                        current_bot_index = (current_bot_index + 1) % len(self.bot_personas)
                    
                    bot = self.bot_personas[current_bot_index]
                    
                    # API 호출
                    response = await self.call_nous_api(user_session, current_message, bot)
                    
                    if not response or "API 오류" in response or "실패" in response:
                        await asyncio.sleep(5)
                        continue
                    
                    # 무한 루프 방지
                    if self.is_repetitive_response(user_session, response):
                        topic_category = random.choice(list(self.starter_topics.keys()))
                        response = random.choice(self.starter_topics[topic_category])
                        logger.info(f"사용자 {user_session.chat_id}: 반복 감지 - 새 주제로 전환")
                    
                    # 응답 기록
                    user_session.last_responses.append(response)
                    if len(user_session.last_responses) > 5:
                        user_session.last_responses.pop(0)
                    
                    user_session.chat_count += 1
                    
                    # 메시지 전송
                    display_message = f"**[{user_session.chat_count:,}/{user_session.max_messages:,}]** {bot['name']}: {response}"
                    
                    try:
                        app = Application.builder().token(self.bot_token).build()
                        await app.bot.send_message(
                            chat_id=user_session.chat_id,
                            text=display_message,
                            parse_mode='Markdown'
                        )
                    except Exception as e:
                        try:
                            await app.bot.send_message(
                                chat_id=user_session.chat_id,
                                text=f"[{user_session.chat_count:,}/{user_session.max_messages:,}] {bot['name']}: {response}"
                            )
                        except Exception as e2:
                            logger.error(f"메시지 전송 오류: {e2}")
                    
                    # 대화 히스토리 업데이트
                    user_session.conversation_history.append({"role": "assistant", "content": response})
                    if len(user_session.conversation_history) > 16:
                        user_session.conversation_history.pop(0)
                    
                    current_message = response
                    
                    # 주기적 새 주제 도입
                    topic_change_counter += 1
                    if topic_change_counter >= 50:
                        topic_category = random.choice(list(self.starter_topics.keys()))
                        new_topic = random.choice(self.starter_topics[topic_category])
                        current_message = f"{response} 그런데 {new_topic}"
                        topic_change_counter = 0
                    
                    # 10000개마다 상태 리포트
                    if user_session.chat_count % 10000 == 0:
                        duration = time.time() - user_session.start_time
                        await app.bot.send_message(
                            chat_id=user_session.chat_id,
                            text=f"🎯 **중간 리포트** 🎯\n\n"
                                 f"📊 진행: {user_session.chat_count:,}개 완료!\n"
                                 f"⏱️ 경과: {duration/3600:.1f}시간\n"
                                 f"⚡ 속도: {user_session.chat_count/(duration/60):.1f}개/분\n\n"
                                 f"🚀 계속 진행중...",
                            parse_mode='Markdown'
                        )
                    
                    await asyncio.sleep(random.uniform(2, 6))
                    
                except asyncio.CancelledError:
                    logger.info(f"사용자 {user_session.chat_id}: 대화 태스크 취소됨")
                    break
                except Exception as e:
                    logger.error(f"사용자 {user_session.chat_id} 대화 중 오류: {e}")
                    await asyncio.sleep(10)
            
            # 대화 종료
            user_session.chat_active = False
            duration = time.time() - user_session.start_time
            
            try:
                app = Application.builder().token(self.bot_token).build()
                await app.bot.send_message(
                    chat_id=user_session.chat_id,
                    text=f"🏁 **대화 완료!** 🏁\n\n"
                         f"📊 **최종 결과:**\n"
                         f"• 총 메시지: **{user_session.chat_count:,}**개\n"
                         f"• 소요시간: **{duration/3600:.1f}**시간\n"
                         f"• 평균속도: **{user_session.chat_count/(duration/60):.1f}**개/분\n\n"
                         f"🎮 **다시 시작:** `/start_chat`\n"
                         f"🗑️ **초기화:** `/clear`",
                    parse_mode='Markdown'
                )
            except:
                pass
                
        except asyncio.CancelledError:
            logger.info(f"사용자 {user_session.chat_id}: 대화 완전 취소됨")
        except Exception as e:
            logger.error(f"사용자 {user_session.chat_id} 대화 실행 오류: {e}")

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
    app.add_handler(CommandHandler("global_status", bot_system.global_status_command))
    app.add_handler(CommandHandler("start_chat", bot_system.start_chat_command))
    app.add_handler(CommandHandler("stop_chat", bot_system.stop_chat_command))
    app.add_handler(CommandHandler("status", bot_system.status_command))
    app.add_handler(CommandHandler("clear", bot_system.clear_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, bot_system.handle_api_key))
    
    # 봇 실행
    logger.info("🚀 다중 사용자 무한 대화 봇 시작!")
    app.run_polling(drop_pending_updates=True)

if __name__ == '__main__':
    main()
