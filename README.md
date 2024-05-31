# PolkaSafe - Easy, Intuitive Multisigs within Your Telegram Group Chats

This repository contains a Telegram bot that allows users to create and manage multisignature wallets on a Polkadot parachain. The bot is built using Python and leverages the `substrateinterface` library to interact with the parachain.

## Prerequisites

- Python 3.12
- Telegram Bot API key

## Installation

1. Clone the repository:

```bash
git clone https://github.com/rohan-patra/tg-multisig
cd tg-multisig
```

2. Create a virtual environment and activate it:

```bash
python3.12 -m venv venv
source venv/bin/activate
```

3. Install the required dependencies:

```bash
pip install -r requirements.txt
```

4. Create a `.env` file in the root directory and add your Telegram Bot API key:

```
TELEGRAM_API_KEY=your_api_key_here
```

Example `.env` file:

```
TELEGRAM_API_KEY=1234567890:ABCdefGHIjklMNOpqrSTUvwxYZ
```

## Getting a Telegram Bot API Key

To obtain a Telegram Bot API key, follow these steps:

1. Open the Telegram app and search for the "BotFather" bot.
2. Start a conversation with BotFather and send the `/newbot` command.
3. Follow the prompts to choose a name and username for your bot.
4. BotFather will provide you with an API token. Copy this token and use it in your `.env` file.

## Usage

To start the bot, run the following command:

```bash
python all.py
```

The bot will now be active and ready to receive commands from users in Telegram.

## Bot Commands

- `/start` or `/hello`: Displays a welcome message with a list of available commands.
- `/hi`: Registers the user with the bot. All group members must register before creating transactions.
- `/create <destination> <amount>`: Creates a new transaction proposal.
- `/yes`: Approves a pending transaction.
- `/no`: Rejects a pending transaction.
- `/balance`: Checks the balance of the multisig wallet.
- `/privatekey`: Retrieves the user's private key (sent via direct message).
- `/switch_chain <rpc_url> <preset>`: Switches to a different parachain.

## Testing

To test the bot locally, you can use the following steps:

1. Create a new Telegram group and add your bot to the group.
2. Start the bot by running `python all.py`.
3. In the Telegram group, use the `/hi` command to register each group member.
4. Once all members are registered, you can start creating transactions using the `/create` command.
5. Each member can approve or reject the transaction using the `/yes` or `/no` commands.
6. You can check the balance of the multisig wallet using the `/balance` command.

## Repo Structure

```
.
├── README.md
├── all.py → the main Python script containing the Telegram bot code.
├── bot
│   └── main.py → bot-related helpers
├── requirments.txt
└── wallet → wallet-related scripts
    ├── main.py
    └── new_wallet.py
```
