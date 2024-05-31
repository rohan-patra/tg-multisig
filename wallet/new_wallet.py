from substrateinterface import SubstrateInterface, Keypair
import json

# Connect to the Westend testnet
substrate = SubstrateInterface(
    url="wss://westend-rpc.polkadot.io", ss58_format=42, type_registry_preset="westend"
)

# Generate a new keypair
keypair = Keypair.create_from_mnemonic(Keypair.generate_mnemonic())

# Save the public and private keys to a file
keys = {"public_key": keypair.ss58_address, "private_key": keypair.private_key.hex()}

with open("westend_wallet_keys.json", "w") as key_file:
    json.dump(keys, key_file)

print(f"Public key: {keypair.ss58_address}")
print(f"Private key: {keypair.private_key.hex()}")
