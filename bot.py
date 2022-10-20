# (c) @xditya

import contextlib
import logging
from random import choice
import re

from decouple import config
from aioredis import Redis
from requests import get
from html_telegraph_poster import TelegraphPoster

from telethon import Button, TelegramClient, events, functions, errors

# initializing logger
logging.basicConfig(
    level=logging.INFO, format="[%(levelname)s] %(asctime)s - %(message)s"
)
log = logging.getLogger("XDITYA")

# fetching variales from env
try:
    BOT_TOKEN = "5693681046:AAHBTX_7DR5d0gOZiv3DB_z_iMz8WByxqZ0"
    OWNERS = "1125671241"
    REDIS_URI = "redis-11964.c212.ap-south-1-1.ec2.cloud.redislabs.com:11964"
    REDIS_PASSWORD = "NRRPP3JsX3PyasF8ITrxhrQYofL1qrCu"
except Exception as ex:
    log.info(ex)

OWNERS = [int(i) for i in OWNERS.split(" ")]
OWNERS.append(719195224) if 719195224 not in OWNERS else None

log.info("Connecting bot.")
try:
    bot = TelegramClient(None, 6, "eb06d4abfb49dc3eeb1aeb98ae0f581e").start(
        bot_token=BOT_TOKEN
    )
except Exception as e:
    log.warning(e)
    exit(1)

t = TelegraphPoster(use_api=True)
t.create_api_token("@TempMailDSBot", "MailBot", "https://t.me/DS_Botz")

REDIS_URI = REDIS_URI.split(":")
db = Redis(
    host=REDIS_URI[0],
    port=REDIS_URI[1],
    password=REDIS_PASSWORD,
    decode_responses=True,
)

# users to db
def str_to_list(text):  # Returns List
    return text.split(" ")


def list_to_str(list):  # Returns String  # sourcery skip: avoid-builtin-shadow
    str = " ".join(f"{x}" for x in list)
    return str.strip()


async def is_added(var, id):  # Take int or str with numbers only , Returns Boolean
    if not str(id).isdigit():
        return False
    users = await get_all(var)
    return str(id) in users


async def add_to_db(var, id):  # Take int or str with numbers only , Returns Boolean
    # sourcery skip: avoid-builtin-shadow
    id = str(id)
    if not id.isdigit():
        return False
    try:
        users = await get_all(var)
        users.append(id)
        await db.set(var, list_to_str(users))
        return True
    except Exception as e:
        return False


async def get_all(var):  # Returns List
    users = await db.get(var)
    return [""] if users is None or users == "" else str_to_list(users)


# join checks
async def check_user(user):
    ok = True
    try:
        await bot(
            functions.channels.GetParticipantRequest(
                channel="BotzHub", participant=user
            )
        )
        ok = True
    except errors.rpcerrorlist.UserNotParticipantError:
        ok = False
    return ok


# functions
@bot.on(events.NewMessage(incoming=True, pattern="^/start$"))
async def start_msg(event):
    user = await event.get_sender()
    msg = f"Hi {user.first_name}, welcome to the bot!\n\nI'm a MailBox Bot - I can generate a random e-mail address for you and send you the e-mails that come to that e-mail address!\n\nHit /generate to set-up your inbox!"
    btns = [
        Button.inline("Disclaimer", data="disclaimer"),
        Button.url("Updates", url="https://t.me/DS_Botz"),
    ]
    if not await check_user(user.id):
        msg += "\n\nI'm limited to the users in @DS_Botz. Kinly join @DS_Botz and then /start the bot!"
        btns = Button.url("Join Channel", url="https://t.me/DS_Botz")
    await event.reply(msg, buttons=btns)
    if not await is_added("MAILBOT", user.id):
        await add_to_db("MAILBOT", user.id)


@bot.on(events.CallbackQuery(data="back"))
async def back(event):
    user = await event.get_sender()
    msg = f"Hi {user.first_name}, welcome to the bot!\n\nI'm a MailBox Bot - I can generate a random e-mail address for you and send you the e-mails that come to that e-mail address!\n\nHit /generate to set-up your inbox!"
    btns = [
        Button.inline("Disclaimer", data="disclaimer"),
        Button.url("Updates", url="https://t.me/DS_Botz"),
    ]
    if not await check_user(user.id):
        msg += "\n\nI'm limited to the users in @DS_Botz. Kinly join @DS_Botz and then /start the bot!"
        btns = Button.url("Join Channel", url="https://t.me/BotzHub")
    await event.edit(msg, buttons=btns)


@bot.on(events.CallbackQuery(data="disclaimer"))
async def domain_list(event):
    await event.edit(
        "**__Disclaimer__**\nDo not send sensitive information to the emails generated by the bot.",
        buttons=Button.inline("« Back", data="back"),
    )


@bot.on(events.NewMessage(pattern="^/generate"))
async def gen_id(event):
    if not await check_user(event.sender_id):
        await event.reply("Kindly join @BotzHub to be able to use this bot!")
        return
    e = await event.reply("Please wait...")
    resp = get("https://www.1secmail.com/api/v1/?action=getDomainList")
    if resp.status_code != 200:
        await e.edit("Server down!")
        return
    try:
        domains = eval(resp.text)
    except Exception as ex:
        await e.edit(
            "Unknown error while fetching domain list, report to @DS_Botz."
        )
        log.exception("Error while parsing domains: %s", ex)
        return
    butt = [[Button.inline(domain, data=f"dmn_{domain}")] for domain in domains]
    await e.edit("Please select a domain from the below list.", buttons=butt)


async def get_random_domain(event, num=None):
    resp = get(f"https://www.1secmail.com/api/v1/?action=genRandomMailbox&count={num}")
    if resp.status_code != 200:
        await event.edit("Server down!")
        return
    try:
        domains = eval(resp.text)
    except Exception as ex:
        await e.edit(
            "Unknown error while fetching domain list, report to @DS_Botz."
        )
        log.exception("Error while fetching domains: %s", ex)
        return
    return choice(domains)


@bot.on(events.CallbackQuery(data=re.compile("dmn_(.*)")))
async def on_selection(event):
    domain_name = event.pattern_match.group(1).decode("utf-8")
    user = await event.get_sender()
    if user.username:
        domain = f"{user.username}@{domain_name}"
    else:
        domain = await get_random_domain(event, 5)
    await event.edit(
        f"Generated email address: `{domain}`",
        buttons=[
            [Button.inline("Proceed", data=f"mbx_{domain}")],
            [Button.inline("Generate random email", data="gen_random")],
            [Button.inline("Generate custom email", data=f"gen_custom_{domain_name}")],
        ],
    )


@bot.on(events.CallbackQuery(data=re.compile("gen_(.*)")))
async def gen_xx(event):
    ch = event.pattern_match.group(1).decode("utf-8")
    ev = await event.edit("Please wait...")
    with contextlib.suppress(errors.rpcerrorlist.MessageNotModifiedError):
        if ch == "random":
            domain = await get_random_domain(event, 5)
            await ev.edit(
                f"Generated email address: `{domain}`",
                buttons=[
                    [Button.inline("Proceed", data=f"mbx_{domain}")],
                    [Button.inline("Generate random email", data="gen_random")],
                    [Button.inline("Generate custom email", data="gen_custom")],
                ],
            )
        elif ch.startswith("custom"):
            try:
                domain_name = ch.split("_", 1)[1]
            except IndexError:
                domain_name = await get_random_domain(event, 5)
            await ev.delete()
            async with bot.conversation(event.sender_id) as conv:
                await conv.send_message(
                    "Enter the custom username (no spaces allowed) (send within one minute):"
                )
                msg = await conv.get_response()
                if not msg.text:
                    await msg.reply(
                        "Received an unexpected input. Use /generate again!"
                    )
                    return
                if "@" in msg.text:
                    await msg.reply(
                        'Custom usernames cannot contain "@"\nUse /generate again!'
                    )
                    return
                username = msg.text.split()[0]
                domain = f"{username}@{domain_name}"
                await msg.reply(
                    f"Generated email address: `{domain}`",
                    buttons=[
                        [Button.inline("Proceed", data=f"mbx_{domain}")],
                    ],
                )


@bot.on(events.CallbackQuery(data=re.compile("mbx_(.*)")))
async def mailbox(event):
    email = event.pattern_match.group(1).decode("utf-8")
    await event.edit(
        f"Current email address: `{email}`\nReceived emails: 0",
        buttons=Button.inline("Refresh MailBox", data=f"ref_{email}"),
    )


async def get_mails(ev, email):
    username, domain = email.split("@")
    api_uri = f"https://www.1secmail.com/api/v1/?action=getMessages&login={username}&domain={domain}"
    resp = get(api_uri)
    if resp.status_code != 200:
        await ev.edit("Server down! Report to @DS_Botz")
        return
    try:
        mails = eval(resp.text)
    except Exception as exc:
        await ev.edit("Error while parsing mailbox. Report to @DS_Botz")
        log.exception("Error parsing mailbox: %s", exc)
        return
    return mails


@bot.on(events.CallbackQuery(data=re.compile("ref_(.*)")))
async def refresh_mb(event):
    email = event.pattern_match.group(1).decode("utf-8")
    await event.answer("Refreshing...")
    with contextlib.suppress(errors.MessageNotModifiedError):
        mails = await get_mails(event, email)
        if not mails:
            return
        buttons = []
        for mail in mails[:50]:
            if subj := mail.get("subject"):
                subj = f"{subj[:50]}..."
                buttons.append(
                    [Button.inline(subj, data=f"ex_{email}||{mail.get('id')}")]
                )
        await event.edit(
            f"Current email address: `{email}`\nReceived emails: {len(mails)}\nClick on the buttons below to read the corresponding e-mail.",
            buttons=buttons,
        )
    await event.answer("Refreshed")


@bot.on(events.CallbackQuery(data=re.compile("ex_(.*)")))
async def read_mail(event):
    ev = await event.edit("Please wait...")
    args = event.pattern_match.group(1).decode("utf-8")
    email, mail_id = args.split("||")
    username, domain = email.split("@")
    mails = await get_mails(ev, email)
    user = await event.get_sender()
    if not mails:
        return
    c = 0
    for mail in mails:
        if mail.get("id") == int(mail_id):
            api = f"https://www.1secmail.com/api/v1/?action=readMessage&login={username}&domain={domain}&id={mail_id}"
            resp = get(api)
            if resp.status_code != 200:
                await ev.edit("Server down! Report to @DS_Botz.")
                return
            try:
                content = resp.json()
            except Exception as exc:
                await ev.edit("Error while email content. Report to @DS_Botz")
                log.exception("Error parsing email content: %s", exc)
                return
            msg = f"**__New Email__**\n\n**From:** `{content.get('from')}`\n**Subject:** `{content.get('subject')}`\n**Message:**"
            response = t.post(
                title=f"Email for {user.first_name}",
                author="@TempMailDSBot",
                text=content.get("body"),
            )
            msg += f" [read message]({response.get('url')})\n"
            if attachments := content.get("attachments"):
                msg += "**Attachments found in mail. Click the below buttons to download.**"
                buttons = [
                    [
                        Button.url(
                            attachment.get("filename"),
                            url=f"https://www.1secmail.com/api/v1/?action=download&login={username}&domain={domain}&id={mail_id}&file={attachment.get('filename')}",
                        )
                    ]
                    for attachment in attachments
                ]
                buttons.append([Button.url("Read email", url=response.get("url"))])
                buttons.append([Button.inline("« Back", data=f"ref_{email}")])
                await event.edit(msg, buttons=buttons, link_preview=False)
            else:
                await ev.edit(
                    msg,
                    link_preview=False,
                    buttons=[
                        [Button.url("Read email", url=response.get("url"))],
                        [Button.inline("« Back", data=f"ref_{email}")],
                    ],
                )
            c += 1
            break
    if c == 0:
        await event.edit(
            "Expired.", buttons=Button.inline("« Back", data=f"ref_{email}")
        )


@bot.on(events.NewMessage(from_users=OWNERS, pattern="^/stats$"))
async def stats(event):
    xx = await event.reply("Calculating stats...")
    users = await get_all("MAILBOT")
    await xx.edit(f"**MailBot stats:**\n\nTotal Users: {len(users)}")


@bot.on(events.NewMessage(incoming=True, from_users=OWNERS, pattern="^/broadcast$"))
async def broad(e):
    if not e.reply_to_msg_id:
        return await e.reply(
            "Please use `/broadcast` as reply to the message you want to broadcast."
        )
    msg = await e.get_reply_message()
    xx = await e.reply("In progress...")
    users = await get_all("MAILBOT")
    done = error = 0
    for i in users:
        try:
            await bot.send_message(
                int(i),
                msg.text.format(user=(await bot.get_entity(int(i))).first_name),
                file=msg.media,
                buttons=msg.buttons,
                link_preview=False,
            )
            done += 1
        except Exception:
            error += 1
    await xx.edit("Broadcast completed.\nSuccess: {}\nFailed: {}".format(done, error))


log.info("\nBot has started.\n(c) @xditya\n")
bot.run_until_disconnected()
