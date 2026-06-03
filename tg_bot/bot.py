import logging
import os
import threading

import telebot

from utils.kafka_consumer import KafkaConsumerClient
from utils import subscribers

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
bot = telebot.TeleBot(TELEGRAM_TOKEN)


# ── Команды бота ──────────────────────────────────────────────────────────────

@bot.message_handler(commands=["start", "subscribe"])
def cmd_subscribe(message):
    added = subscribers.add(message.chat.id)
    if added:
        bot.reply_to(
            message, "Подписка оформлена. Будешь получать алерты об изменении цен.")
    else:
        bot.reply_to(message, "Ты уже подписан.")


@bot.message_handler(commands=["unsubscribe"])
def cmd_unsubscribe(message):
    removed = subscribers.remove(message.chat.id)
    if removed:
        bot.reply_to(message, "Подписка отменена.")
    else:
        bot.reply_to(message, "Ты не был подписан.")


@bot.message_handler(commands=["status"])
def cmd_status(message):
    ids = subscribers.all_ids()
    bot.reply_to(message, f"Активных подписчиков: {len(ids)}")


# ── Kafka → рассылка ──────────────────────────────────────────────────────────

def format_alert(alert: dict) -> str:
    direction = alert.get("direction", "")
    symbol = alert.get("symbol", "")
    delta = alert.get("delta_pct", 0)
    prev = alert.get("prev_price", 0)
    curr = alert.get("curr_price", 0)
    updated = alert.get("last_updated", "")[:19].replace("T", " ")

    return (
        f"<b>{direction} {symbol} Price Alert</b>\n"
        f"Delta:  <b>{delta:+.2f}%</b>\n"
        f"Before: <code>${prev:,.4f}</code>\n"
        f"After:  <code>${curr:,.4f}</code>\n"
        f"<i>{updated}</i>"
    )


def kafka_worker():
    with KafkaConsumerClient(topic="crypto.alerts", group_id="tg_bot_alerts") as consumer:
        for alert in consumer:
            try:
                text = format_alert(alert)
                for chat_id in subscribers.all_ids():
                    bot.send_message(chat_id, text, parse_mode="HTML")
                    log.info(
                        f"Sent alert to {chat_id}: {alert.get('symbol')} {alert.get('delta_pct')}%")
            except Exception as e:
                log.error(f"Failed to send alert: {e}")


# ── Запуск ────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    log.info("Starting bot...")
    threading.Thread(target=kafka_worker, daemon=True).start()
    bot.infinity_polling()
