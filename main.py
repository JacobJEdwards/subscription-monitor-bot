
import datetime
import logging
from datetime import date
from typing import Optional, Tuple

import redis
from dateutil.relativedelta import relativedelta
from telegram import *
from telegram.ext import Application, ChatMemberHandler, ContextTypes, CallbackContext, CommandHandler
import os

BOT_TOKEN = ***REMOVED***

# enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

logger = logging.getLogger(__name__)

r = redis.Redis()


# allows the bot to know if a member update is a join or leave
def getStatusChange(chat_member_update: ChatMemberUpdated) -> Optional[Tuple[bool, bool]]:
    status_change = chat_member_update.difference().get("status")
    old_is_member, new_is_member = chat_member_update.difference().get("is_member", (None, None))

    if status_change is None:
        return None

    old_status, new_status = status_change
    was_member = old_status in [
        ChatMember.MEMBER,
        ChatMember.OWNER,
        ChatMember.ADMINISTRATOR
    ] or (old_status == ChatMember.RESTRICTED and old_is_member is True)
    is_member = new_status in [
        ChatMember.MEMBER,
        ChatMember.OWNER,
        ChatMember.ADMINISTRATOR
    ] or (new_status == ChatMember.RESTRICTED and new_is_member is True)

    return was_member, is_member


# called when a new member joins, or leaves
async def memberStatusChange(update: Update, context: CallbackContext) -> None:
    # checks whether member joined or leaves
    result = getStatusChange(update.chat_member)
    if result is None:
        return
    was_member, is_member = result

    subscription_start = date.today().strftime('%d/%m/%Y')
    subscription_end = (date.today() + relativedelta(months=+1)).strftime('%d/%m/%Y')

    memberID = update.chat_member.new_chat_member.user.id
    chatID = update.effective_chat.id
    username = update.chat_member.new_chat_member.user.first_name+' '+update.chat_member.new_chat_member.user.last_name

    if not was_member and is_member:
        r.rpush(memberID, subscription_start, subscription_end, chatID, username)
    # add user id to database, and date

    elif was_member and not is_member:
        try:
            r.delete(memberID)
        except:
            pass
    # remove user from database if they leave - prevents errors


# called daily to check if anyone's subscription has ended
async def checkSubscriptions(context: CallbackContext) -> None:
    today = date.today().strftime("%d/%m/%Y")

    # iterates through each user and checks their subscription is valid
    for key in r.scan_iter():
        subscription_end = r.lindex(key, 1).decode()
        # if subscription invalid, calls kick function
        if today == subscription_end:
            chat_id = r.lindex(key, 2).decode()
            await kickUser(context, key.decode(), chat_id)


# bans an invalid user
async def kickUser(context: ContextTypes.DEFAULT_TYPE, userid, chat_id) -> None:
    # called from check subscriptions
    await context.bot.banChatMember(chat_id=chat_id, user_id=userid)
    r.delete(userid)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text('Use /check followed by a user id to view the users subscription')


async def manualCheck(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        userID = context.args[0]
    except IndexError:
        await update.message.reply_text('Please use this command followed by a user id!\nFor example:\n*/check'
                                        ' 6043385959*', parse_mode='Markdown')
        return

    if not userID.isnumeric():
        await update.message.reply_text('Invalid User ID')
        return

    if not r.exists(userID):
        await update.message.reply_text('User is not a member!')
        return

    subscription_end = r.lindex(userID, 1).decode()
    subscription_start = r.lindex(userID, 0).decode()
    chatID = r.lindex(userID, 2).decode()
    username = r.lindex(userID, 3).decode()

    await update.message.reply_text(f'*User ID{userID}*\n*Username: *{username}\n*Chat: *{chatID}\n*Subscription start:'
                                    f' *{subscription_start}'f'\n*Subscription end: *{subscription_end}'
                                    , parse_mode='Markdown')


async def dailyCheck(context: CallbackContext) -> None:
    today = date.today().strftime("%d-%m-%Y")

    filename = f'{today}.txt'

    with open(filename, 'w') as file:
        for key in r.scan_iter():
            user_id = key.decode()
            subscription_start = r.lindex(key, 0).decode()
            subscription_end = r.lindex(key, 1).decode()
            chat_id = r.lindex(key, 2).decode()
            username = r.lindex(key, 3).decode()

            file.write(f'{username}: {user_id}\nChat ID: {chat_id}\nSubscription start: {subscription_start}\n'
                       f'Subscription end: {subscription_end}\n\n')

    await context.bot.send_document(document=open(filename, 'rb'), chat_id='***REMOVED***')

    if os.path.exists(filename):
        os.remove(filename)


# creates the bot and handlers
def main() -> None:
    # creates bot
    application = Application.builder().token(BOT_TOKEN).build()
    # allows me to access job queue
    job_queue = application.job_queue

    # runs daily
    check_subscription = job_queue.run_daily(checkSubscriptions, time=datetime.time(hour=8))
    daily_message = job_queue.run_daily(dailyCheck, time=datetime.time(hour=7))

    # called when new user has been added
    # Handle members joining/leaving chats.
    application.add_handler(ChatMemberHandler(memberStatusChange, ChatMemberHandler.CHAT_MEMBER))

    # command handlers
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('check', manualCheck))

    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()
