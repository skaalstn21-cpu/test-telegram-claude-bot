import os
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import anthropic

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

conversations = {}

SYSTEM_PROMPT = "당신은 친절하고 도움이 되는 한국어 AI 비서입니다."
MAX_HISTORY = 20

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    conversations[user_id] = []
    await update.message.reply_text("안녕하세요! 무엇이든 물어보세요!\n/reset - 대화 초기화")

async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    conversations[update.effective_user.id] = []
    await update.message.reply_text("대화 기록이 초기화되었어요!")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_message = update.message.text
    if user_id not in conversations:
        conversations[user_id] = []
    conversations[user_id].append({"role": "user", "content": user_message})
    if len(conversations[user_id]) > MAX_HISTORY:
        conversations[user_id] = conversations[user_id][-MAX_HISTORY:]
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    try:
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            messages=conversations[user_id],
        )
        assistant_message = response.content[0].text
        conversations[user_id].append({"role": "assistant", "content": assistant_message})
        if len(assistant_message) > 4096:
            for i in range(0, len(assistant_message), 4096):
                await update.message.reply_text(assistant_message[i:i+4096])
        else:
            await update.message.reply_text(assistant_message)
    except Exception as e:
        logger.error(f"Error: {e}")
        await update.message.reply_text(f"오류 발생: {type(e).__name__}: {e}")

def main():
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("reset", reset))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    logger.info("Bot started!")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
