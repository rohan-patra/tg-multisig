from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from substrateinterface import SubstrateInterface, Keypair
from hashlib import blake2b

app = FastAPI()

# Connect to Westend testnet
substrate = SubstrateInterface(
    url="wss://westend-rpc.polkadot.io", ss58_format=42, type_registry_preset="westend"
)

# In-memory storage for group and wallet info
groups = {}


class InitGroupRequest(BaseModel):
    group_id: str
    usernames: list[str]
    threshold: int


@app.post("/init_group")
async def init_group(req: InitGroupRequest):
    if req.group_id in groups:
        raise HTTPException(status_code=400, detail="Group already exists")

    # Initialize wallets for each user
    wallets = {
        username: Keypair.create_from_mnemonic(Keypair.generate_mnemonic())
        for username in req.usernames
    }

    # Generate multisig address
    sorted_addresses = sorted([wallet.ss58_address for wallet in wallets.values()])
    multisig_account_id = substrate.generate_multisig_account(
        signatories=sorted_addresses, threshold=req.threshold
    )
    multisig_address = multisig_account_id.ss58_address

    # Initialize group with usernames, threshold, wallets, and multisig address
    groups[req.group_id] = {
        "usernames": req.usernames,
        "wallets": wallets,
        "multisig_address": multisig_address,
        "threshold": req.threshold,
        "pending_tx": None,
    }

    return {
        "message": f"Initialized group {req.group_id}",
        "wallets": {
            username: wallet.ss58_address for username, wallet in wallets.items()
        },
        "multisig_address": multisig_address,
    }


class CreateTxRequest(BaseModel):
    group_id: str
    proposer: str
    destination: str
    amount: int


@app.post("/create_tx")
async def create_tx(req: CreateTxRequest):
    group = groups.get(req.group_id)
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")

    if req.proposer not in group["usernames"]:
        raise HTTPException(status_code=403, detail="Proposer not in group")

    # Create unsigned transaction
    call = substrate.compose_call(
        call_module="Balances",
        call_function="transfer_allow_death",
        call_params={"dest": req.destination, "value": req.amount},
    )

    group["pending_tx"] = {"call": call, "signers": [req.proposer]}

    return {"message": "Created transaction"}


class SignTxRequest(BaseModel):
    group_id: str
    username: str


@app.post("/sign_tx")
async def sign_tx(req: SignTxRequest):
    group = groups.get(req.group_id)
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")

    if not group["pending_tx"]:
        raise HTTPException(status_code=400, detail="No pending transaction")

    if req.username not in group["usernames"]:
        raise HTTPException(status_code=403, detail="User not in group")

    if req.username in group["pending_tx"]["signers"]:
        raise HTTPException(status_code=400, detail="User already signed")

    # Sign the pending transaction with user's wallet
    wallet = group["wallets"].get(req.username)
    if not wallet:
        raise HTTPException(status_code=404, detail="Wallet not found for user")

    group["pending_tx"]["signers"].append(req.username)

    return {"message": "Signed transaction"}


@app.post("/confirm_tx")
async def confirm_tx(group_id: str):
    group = groups.get(group_id)
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")

    if not group["pending_tx"]:
        raise HTTPException(status_code=400, detail="No pending transaction")

    signers = len(group["pending_tx"]["signers"])
    if signers < group["threshold"]:
        raise HTTPException(status_code=400, detail="Not enough signatures")

    other_signatories = [
        wallet.ss58_address
        for user, wallet in group["wallets"].items()
        if user in group["pending_tx"]["signers"][1:]
    ]

    call = group["pending_tx"]["call"]

    # Compose the call hash
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


@app.get("/balance/{group_id}")
async def get_multisig_balance(group_id: str):
    group = groups.get(group_id)
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")

    multisig_address = group["multisig_address"]
    balance_info = substrate.query("System", "Account", [multisig_address])

    data = balance_info["data"]

    balance_data = {
        "free": int(data["free"].value),
        "reserved": int(data["reserved"].value),
        "frozen": int(data["frozen"].value),
        "flags": int(data["flags"].value),
    }

    return {"balance": balance_data}
