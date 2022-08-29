import datetime
import logging
from datetime import date
from typing import Optional, Tuple
import redis

from telegram import *
from telegram.constants import ParseMode
from telegram.ext import Application, ChatMemberHandler, CommandHandler, ContextTypes, CallbackContext

BOT_TOKEN = ***REMOVED***

# enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

logger = logging.getLogger(__name__)

r = redis.Redis()


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

    today = date.today().strftime("%d/%m/%Y")
    memberID = update.chat_member.new_chat_member.user.id

    if not was_member and is_member:
        r.rpush(memberID, today)
    # add user id to database, and date

    elif was_member and not is_member:
        print('deleting user')
        try:
            r.delete(memberID)
        except:
            pass
    # remove user from database


async def checkSubscriptions(context: CallbackContext) -> None:
    today = date.today().strftime("%d/%m/%Y")

    for key in r.scan_iter():
        dateAdded = r.lindex(key, 0).decode()
        if dateAdded[0:2] == today[0:2] and (int(dateAdded[3:5]) + 1 == (int(today[3:5]) or (dateAdded[3:5] == '12' and today[3:5] == '1'):
            await kickUser(update, context, key)

async def kickUser(update: Update, context: ContextTypes.DEFAULT_TYPE, userid) -> None:
    # called from check subscriptions
    pass


def main() -> None:
    # creates bot
    application = Application.builder().token(BOT_TOKEN).build()
    # allows me to access job queue
    job_queue = application.job_queue

    # runs daily
    check_subscription = job_queue.run_daily(checkSubscriptions, time=datetime.time(hour=11, minute=0, second=0))

    # called when new user has been added
    # Handle members joining/leaving chats.
    application.add_handler(ChatMemberHandler(memberStatusChange, ChatMemberHandler.CHAT_MEMBER))

    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()
