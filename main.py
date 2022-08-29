import logging
from datetime import date

from telegram import *
from telegram.constants import ParseMode
from telegram.ext import Application, ChatMemberHandler, CommandHandler, ContextTypes

BOT_TOKEN = ''

# enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

logger = logging.getLogger(__name__)


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
async def memberStatusChange(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    result = getStatusChange(update.chat_member)
    if result is None:
        return
    was_member, is_member = result
    today = date.today().strftime("%d/%m/%Y")
    memberID = update.chat_member.new_chat_member.user.id

    if not was_member and is_member:
        pass
    # add user id to database, and date

    elif was_member and not is_member:
        pass
    # remove user from database


async def checkSubscriptions(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    today = datetime.today().strftime("%d/%m/%Y")


async def kickUser() -> None:
    pass


def main() -> None:
    # creates bot
    application = Application.builder().token(BOT_TOKEN).build()
    # allows me to access job queue
    job_queue = application.job_queue

    # runs daily
    check_subscription = job_queue.run_daily(checkSubscriptions)

    # called when new user has been added
    # Handle members joining/leaving chats.
    application.add_handler(ChatMemberHandler(memberStatusChange, ChatMemberHandler.CHAT_MEMBER))


if __name__ == '__main__':
    main()
