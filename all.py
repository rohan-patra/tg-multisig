import os
from dotenv import load_dotenv
import telebot
from substrateinterface import SubstrateInterface, Keypair
from hashlib import blake2b

# Load environment variables
load_dotenv()
BOT_TOKEN = os.getenv("TELEGRAM_API_KEY")
bot = telebot.TeleBot(BOT_TOKEN)

# Connect to the default parachain
DEFAULT_RPC_URL = "wss://westend-rpc.polkadot.io"
substrate = SubstrateInterface(
    url=DEFAULT_RPC_URL, ss58_format=42, type_registry_preset="westend"
)


# In-memory storage for group and wallet info
groups = {}


def init_group(group_id: str, usernames: list[str], threshold: int):
    if group_id in groups:
        return {"error": "Group already exists"}

    wallets = {
        username: Keypair.create_from_mnemonic(Keypair.generate_mnemonic())
        for username in usernames
    }

    sorted_addresses = sorted([wallet.ss58_address for wallet in wallets.values()])
    multisig_account_id = substrate.generate_multisig_account(
        signatories=sorted_addresses, threshold=threshold
    )
    multisig_address = multisig_account_id.ss58_address

    groups[group_id] = {
        "usernames": usernames,
        "wallets": wallets,
        "multisig_address": multisig_address,
        "threshold": threshold,
        "pending_tx": None,
    }

    return {
        "message": f"Initialized group {group_id}",
        "wallets": {
            username: wallet.ss58_address for username, wallet in wallets.items()
        },
        "multisig_address": multisig_address,
    }


def create_tx(group_id: str, proposer: str, destination: str, amount: int):
    group = groups.get(group_id)
    if not group:
        return {"error": "Group not found"}

    if proposer not in group["usernames"]:
        return {"error": "Proposer not in group"}

    call = substrate.compose_call(
        call_module="Balances",
        call_function="transfer_allow_death",
        call_params={"dest": destination, "value": amount},
    )

    group["pending_tx"] = {"call": call, "signers": [proposer]}

    return {"message": "Created transaction"}


def sign_tx(group_id: str, username: str):
    group = groups.get(group_id)
    if not group:
        return {"error": "Group not found"}

    if not group["pending_tx"]:
        return {"error": "No pending transaction"}

    if username not in group["usernames"]:
        return {"error": "User not in group"}

    if username in group["pending_tx"]["signers"]:
        return {"error": "User already signed"}

    wallet = group["wallets"].get(username)
    if not wallet:
        return {"error": "Wallet not found for user"}

    group["pending_tx"]["signers"].append(username)

    return {"message": "Signed transaction"}


def confirm_tx(group_id: str):
    group = groups.get(group_id)
    if not group:
        return {"error": "Group not found"}

    if not group["pending_tx"]:
        return {"error": "No pending transaction"}

    signers = len(group["pending_tx"]["signers"])
    if signers < group["threshold"]:
        return {"error": "Not enough signatures"}

    other_signatories = [
        wallet.ss58_address
        for user, wallet in group["wallets"].items()
        if user in group["pending_tx"]["signers"][1:]
    ]

    call = group["pending_tx"]["call"]

    call_data = substrate.compose_call(
        call_module=call.call_module,
        call_function=call.call_function,
        call_params=call.call_args,
    ).data

    call_hash = blake2b(call_data, digest_size=32).digest()

    multi_sig_call = substrate.compose_call(
        call_module="Multisig",
        call_function="approve_as_multi",
        call_params={
            "threshold": group["threshold"],
            "other_signatories": other_signatories,
            "maybe_timepoint": None,
            "call_hash": call_hash,
            "store_call": True,
            "max_weight": {
                "proof_size": 0,
                "ref_time": 1000000000,
            },
        },
    )

    wallet = group["wallets"][group["pending_tx"]["signers"][0]]
    extrinsic = substrate.create_signed_extrinsic(call=multi_sig_call, keypair=wallet)
    receipt = substrate.submit_extrinsic(extrinsic, wait_for_inclusion=True)

    group["pending_tx"] = None

    return {"message": "Confirmed transaction", "receipt": receipt}


def get_multisig_balance(group_id: str):
    group = groups.get(group_id)
    if not group:
        return {"error": "Group not found"}

    multisig_address = group["multisig_address"]
    balance_info = substrate.query("System", "Account", [multisig_address])

    data = balance_info["data"]

    balance_data = {
        "free": int(data["free"].value),
        "reserved": int(data["reserved"].value),
        "frozen": int(data["frozen"].value),
        "flags": int(data["flags"].value),
    }

    return {"balance": balance_data, "address": multisig_address}


# Telegram bot handlers
process_state = {"active": False, "members": set()}
user_ids = []
bot_state = {"group_initialized": False}


@bot.message_handler(commands=["start", "hello"])
def send_welcome(message):
    if message.chat.type == "group":
        bot.send_message(
            message.chat.id,
            "Welcome to the MultiSig Wallet Bot! Here's how to use me:\n\n"
            "/hi - Register yourself with the bot\n"
            "/create <destination> <amount> - Create a new transaction\n"
            "/yes - Approve a pending transaction\n"
            "/no - Reject a pending transaction\n"
            "/balance - Check the multisig wallet balance and address\n"
            "/privatekey - Retrieve your private key (sent via DM)\n"
            "/switch_chain <rpc_url> <preset> - Switch to a different parachain",
        )


@bot.message_handler(commands=["hi"])
def register_user(message):
    chat_id = message.chat.id
    user_id = str(message.from_user.id)
    username = message.from_user.username

    if bot_state["group_initialized"]:
        bot.send_message(
            chat_id, "The group is already initialized. No new registrations allowed."
        )
        return

    if username in user_ids:
        bot.send_message(chat_id, f"@{username} is already registered.")
        return

    user_ids.append(user_id)
    bot.send_message(chat_id, f"Hello, @{username}! You are now registered.")

    # Get chat members count
    chat_member_count = bot.get_chat_member_count(chat_id) - 1
    if len(user_ids) == chat_member_count:
        response = init_group(chat_id, user_ids, chat_member_count)
        print(user_ids)
        bot_state["group_initialized"] = True
        bot.send_message(
            chat_id, "Group initialized! You may begin creating transactions."
        )
    else:
        bot.send_message(
            chat_id,
            f"Waiting for {chat_member_count - len(user_ids)} more members to register.",
        )


@bot.message_handler(commands=["create"])
def create_tx_handler(message):
    chat_id = message.chat.id
    user_id = str(message.from_user.id)
    text = message.text.split()
    if len(text) < 2:
        bot.reply_to(message, "Usage: /create_tx <destination> <amount>")
        return

    if not bot_state["group_initialized"]:
        bot.reply_to(
            message, "Group not initialized. Please register all members first."
        )
        return

    if process_state["active"]:
        bot.reply_to(
            message, "There is an active process. Please wait for it to finish."
        )
        return

    destination = text[1]
    amount = int(text[2])

    print(user_id)

    process_state["active"] = True
    process_state["members"] = set([user_id])
    response = create_tx(chat_id, user_id, destination, amount)
    print(response)
    bot.reply_to(
        message,
        "Transaction created. Waiting for all members to sign with /yes or /no.",
    )


@bot.message_handler(commands=["yes"])
def confirm_yes(message):
    chat_id = message.chat.id
    user_id = str(message.from_user.id)

    if not bot_state["group_initialized"]:
        bot.reply_to(
            message, "Group not initialized. Please register all members first."
        )
        return

    if process_state["active"]:
        if user_id in process_state["members"]:
            bot.reply_to(message, "You have already responded.")
            return

        process_state["members"].add(user_id)
        chat_members = bot.get_chat_members_count(chat_id)
        signed_data = sign_tx(chat_id, user_id)

        print(signed_data)

        if len(process_state["members"]) >= chat_members - 1:
            process_state["active"] = False
            process_state["members"] = set()
            bot.send_message(
                chat_id,
                f"Threshold has been reached and the transaction has been confirmed. 🎉🎉🎉\nTransaction Data: {groups[chat_id]['pending_tx']}",
            )
            try:
                confirm_data = confirm_tx(chat_id)
            except:
                pass
        else:
            remaining = chat_members - 1 - len(process_state["members"])
            bot.send_message(
                chat_id, f"Waiting for {remaining} more members to respond."
            )
    else:
        bot.reply_to(message, "No active process. Please start with /create.")


@bot.message_handler(commands=["no"])
def confirm_no(message):
    chat_id = message.chat.id
    user_id = str(message.from_user.id)

    if not bot_state["group_initialized"]:
        bot.reply_to(
            message, "Group not initialized. Please register all members first."
        )
        return

    if process_state["active"]:
        if user_id in process_state["members"]:
            bot.reply_to(message, "You have already responded.")
            return
        process_state["active"] = False
        process_state["members"] = set()
        bot.send_message(chat_id, "Process terminated due to a /no response.")
    else:
        bot.reply_to(message, "No active process. Please start with /startprocess.")


@bot.message_handler(commands=["balance"])
def get_balance_handler(message):
    chat_id = message.chat.id

    if not bot_state["group_initialized"]:
        bot.reply_to(
            message, "Group not initialized. Please register all members first."
        )
        return

    response = get_multisig_balance(chat_id)
    bot.reply_to(message, response)


@bot.message_handler(commands=["switch_chain"])
def switch_chain(message):
    if len(message.text.split()) < 3:
        bot.reply_to(
            message,
            "Please provide the RPC URL and preset of the parachain you want to switch to.",
        )
        return

    rpc_url = message.text.split()[1]
    preset = message.text.split()[2]
    try:
        global substrate
        print(rpc_url, preset)
        substrate = SubstrateInterface(
            url=rpc_url, ss58_format=42, type_registry_preset=preset
        )
        bot.reply_to(
            message,
            f"Switched to the parachain with RPC: {rpc_url} and preset: {preset}",
        )
    except Exception as e:
        bot.reply_to(message, f"Error switching to the parachain: {str(e)}")


@bot.message_handler(commands=["privatekey"])
def get_private_key(message):
    if not bot_state["group_initialized"]:
        bot.reply_to(
            message, "Group not initialized. Please register all members first."
        )
        return

    chat_id = message.chat.id
    user_id = str(message.from_user.id)

    wallet = groups[chat_id]["wallets"].get(user_id)
    if not wallet:
        bot.reply_to(message, "You are not registered in this group.")
        return

    private_key = wallet.mnemonic
    bot.reply_to(
        message,
        f"Your private key is: ||{private_key}||\n\nPlease keep it safe and do not share it with anyone\!",
        parse_mode="MarkdownV2",
    )


@bot.message_handler(func=lambda msg: True)
def echo_all(message):
    bot.reply_to(message, message.text)


if __name__ == "__main__":
    bot.infinity_polling()
    print("Bot is running...\nYou can now interact with it on Telegram")
