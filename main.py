# instead of adding date joined to database, add date subscription ends
# then compare the todays date to subscription end date
# this allows for possibility os subscription renewal
# look into datetime functionality


import datetime
import logging
from datetime import date
from dateutil.relativedelta import relativedelta
from typing import Optional, Tuple
import redis

from telegram import *
from telegram.constants import ParseMode
from telegram.ext import Application, ChatMemberHandler, CommandHandler, ContextTypes, CallbackContext

BOT_TOKEN = ***REMOVED***
CHAT_ID = ''

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
    result = getStatusChange(update.chat_member)
    if result is None:
        return
    was_member, is_member = result

    subscription_start = date.today().strftime('%d/%m/%Y')
    subscription_end = (date.today() + relativedelta(months=+1)).strftime('%d/%m/%Y')

    memberID = update.chat_member.new_chat_member.user.id
    chatID = update.effective_chat.id

    if not was_member and is_member:
        r.rpush(memberID, subscription_start, subscription_end, chatID)
    # add user id to database, and date

    elif was_member and not is_member:
        try:
            r.delete(memberID)
        except:
            pass
    # remove user from database


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


# creates the bot and handlers
def main() -> None:
    # creates bot
    application = Application.builder().token(BOT_TOKEN).build()
    # allows me to access job queue
    job_queue = application.job_queue

    # runs daily
    check_subscription = job_queue.run_daily(checkSubscriptions, time=datetime.time(hour=13, minute=5, second=15))

    # called when new user has been added
    # Handle members joining/leaving chats.
    application.add_handler(ChatMemberHandler(memberStatusChange, ChatMemberHandler.CHAT_MEMBER))

    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()
