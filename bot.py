import os
import logging
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)
from anthropic import Anthropic

# ─── 설정 ───
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "여기에_토큰_입력")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "여기에_API키_입력")

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Anthropic 클라이언트 초기화
client = Anthropic(api_key=ANTHROPIC_API_KEY)

# 사용자별 대화 기록 저장 (메모리)
conversations: dict[int, list[dict]] = {}

# 시스템 프롬프트 (원하는 대로 수정하세요)
SYSTEM_PROMPT = """당신은 친절하고 도움이 되는 한국어 AI 비서입니다.
사용자의 질문에 명확하고 자연스러운 한국어로 답변하세요."""

# 대화 기록 최대 길이 (토큰 절약을 위해 제한)
MAX_HISTORY = 20


# ─── 핸들러 ───


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """봇 시작 시 인사 메시지"""
    user_id = update.effective_user.id
    conversations[user_id] = []
    await update.message.reply_text(
        "안녕하세요! 👋\n"
        "저는 Claude AI와 연결된 Telegram 봇이에요.\n"
        "무엇이든 물어보세요!\n\n"
        "/reset - 대화 기록 초기화"
    )


async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """대화 기록 초기화"""
    user_id = update.effective_user.id
    conversations[user_id] = []
    await update.message.reply_text("대화 기록이 초기화되었어요! 새로 시작할게요. 🔄")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """사용자 메시지를 받아서 Claude에게 전달하고 응답 반환"""
    user_id = update.effective_user.id
    user_message = update.message.text

    # 대화 기록 초기화 (처음 사용하는 유저)
    if user_id not in conversations:
        conversations[user_id] = []

    # 사용자 메시지를 기록에 추가
    conversations[user_id].append({"role": "user", "content": user_message})

    # 대화 기록이 너무 길면 오래된 것 제거
    if len(conversations[user_id]) > MAX_HISTORY:
        conversations[user_id] = conversations[user_id][-MAX_HISTORY:]

    # "입력 중..." 표시
    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id, action="typing"
    )

    try:
        # Claude API 호출
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            messages=conversations[user_id],
        )

        # 응답 텍스트 추출
        assistant_message = response.content[0].text

        # 응답을 대화 기록에 추가
        conversations[user_id].append(
            {"role": "assistant", "content": assistant_message}
        )

        # Telegram 메시지 길이 제한 (4096자)
        if len(assistant_message) > 4096:
            for i in range(0, len(assistant_message), 4096):
                await update.message.reply_text(assistant_message[i : i + 4096])
        else:
            await update.message.reply_text(assistant_message)

    except Exception as e:
        logger.error(f"Claude API 오류: {e}")
        await update.message.reply_text(
            "죄송해요, 오류가 발생했어요. 잠시 후 다시 시도해 주세요. 😥"
        )


# ─── 메인 ───


def main():
    """봇 실행"""
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # 명령어 핸들러
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("reset", reset))

    # 일반 메시지 핸들러
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # 봇 시작
    logger.info("봇이 시작되었습니다! 🚀")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
