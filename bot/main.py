import os
from dotenv import load_dotenv
import telebot

load_dotenv()
BOT_TOKEN = os.getenv("TELEGRAM_API_KEY")
bot = telebot.TeleBot(BOT_TOKEN)

process_states = {}


# connect to a gnosis multisig wallet
@bot.message_handler(commands=["start", "hello"])
def send_welcome(message):
    bot.reply_to(message, "Howdy, how are you doing?")


@bot.message_handler(commands=["sign"])
def start_process(message):
    chat_id = message.chat.id
    process_states[chat_id] = {"active": True, "members_responded": set()}
    bot.reply_to(message, "Process started. All members, please respond with /yes.")


@bot.message_handler(commands=["yes"])
def confirm_yes(message):
    chat_id = message.chat.id
    if chat_id in process_states and process_states[chat_id]["active"]:
        user_id = message.from_user.id
        process_states[chat_id]["members_responded"].add(user_id)
        chat_members = bot.get_chat_members_count(chat_id)
        if len(process_states[chat_id]["members_responded"]) >= chat_members - 1:
            process_states[chat_id]["active"] = False
            bot.send_message(
                chat_id,
                "All members have responded with /yes. Proceeding with the process.",
            )
            # execute signature
        else:
            remaining = (
                chat_members - 1 - len(process_states[chat_id]["members_responded"])
            )
            bot.send_message(
                chat_id, f"Waiting for {remaining} more members to respond."
            )
    else:
        bot.reply_to(message, "No active process. Please start with /startprocess.")


@bot.message_handler(commands=["no"])
def confirm_no(message):
    chat_id = message.chat.id
    if chat_id in process_states and process_states[chat_id]["active"]:
        process_states[chat_id]["active"] = False
        bot.send_message(chat_id, "Process terminated due to a /no response.")
    else:
        bot.reply_to(message, "No active process. Please start with /startprocess.")


@bot.message_handler(func=lambda msg: True)
def echo_all(message):
    bot.reply_to(message, message.text)


bot.infinity_polling()
