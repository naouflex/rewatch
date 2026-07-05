"""Shared helpers for EVM query runners.

In inverse-watch the EVM runners cache contract ABIs in a dedicated
``smart_contracts`` table. We don't ship that model here, so we always go
straight to Etherscan. The helper intentionally keeps the surface tiny and
swallows transient errors so the runner can degrade gracefully.
"""
import json
import logging

import requests

logger = logging.getLogger(__name__)


def fetch_abi_from_etherscan(address, etherscan_api_key, base_url="https://api.etherscan.io/api"):
    """Fetch and parse a contract ABI from Etherscan.

    Returns the parsed ABI list, or raises ``Exception`` with a human readable
    message if Etherscan refuses to serve it (private contract, missing key,
    ratelimit, ...).
    """
    if not etherscan_api_key:
        raise Exception("Etherscan API key is required to fetch ABIs.")

    params = {
        "module": "contract",
        "action": "getabi",
        "address": address,
        "apikey": etherscan_api_key,
    }
    response = requests.get(base_url, params=params, timeout=30)
    response.raise_for_status()
    payload = response.json()
    if str(payload.get("status")) != "1":
        raise Exception("Etherscan refused the ABI request: {0}".format(payload.get("result") or payload))

    return json.loads(payload["result"])


def fetch_contract_creation_block(address, etherscan_api_key, base_url="https://api.etherscan.io/api"):
    params = {
        "module": "account",
        "action": "txlist",
        "address": address,
        "startblock": 0,
        "endblock": 99999999,
        "sort": "asc",
        "apikey": etherscan_api_key,
    }
    response = requests.get(base_url, params=params, timeout=30)
    response.raise_for_status()
    payload = response.json()
    if str(payload.get("status")) != "1" or not payload.get("result"):
        raise Exception("Could not determine contract creation block: {0}".format(payload.get("message") or payload))
    return int(payload["result"][0]["blockNumber"])
