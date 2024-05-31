# PolkaSafe - easy, intuitive multisigs within your Telegram group chats

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
python -m venv venv
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

## Repo Structure

```
.
├── README.md
├── all.py → the main Python script containing the Telegram bot code.
├── bot
│   └── main.py → bot-related helpers
├── requirments.txt
└── wallet → wallet-related scripts
    ├── main.py
    └── new_wallet.py
```
