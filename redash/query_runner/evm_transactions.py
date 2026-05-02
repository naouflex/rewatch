"""EVM transactions query runner.

Lists every transaction in a block range whose ``from`` or ``to`` matches the
configured address. Queries are written as YAML, e.g.

    address: "0xdAC17F958D2ee523a2206206994597C13D831ec7"
    start_block: 19000000
    end_block: 19000050

Ported from inverse-watch with the ``SmartContract`` cache removed and the
boolean-precedence bug from the original ``and/or`` filter fixed.
"""
import logging

import yaml

from redash.query_runner import (
    TYPE_FLOAT,
    TYPE_INTEGER,
    TYPE_STRING,
    BaseHTTPQueryRunner,
    register,
)
from redash.utils import json_dumps

logger = logging.getLogger(__name__)

try:
    from web3 import HTTPProvider, Web3

    web3_installed = True
except ImportError:
    Web3 = None
    HTTPProvider = None
    web3_installed = False


class EVMTransactions(BaseHTTPQueryRunner):
    requires_url = False

    @classmethod
    def enabled(cls):
        return web3_installed

    @classmethod
    def type(cls):
        return "evmtransactions"

    @classmethod
    def name(cls):
        return "EVM Transactions"

    @classmethod
    def configuration_schema(cls):
        return {
            "type": "object",
            "properties": {
                "rpc_url": {"type": "string", "title": "Ethereum RPC URL"},
                "etherscan_api_key": {"type": "string", "title": "Etherscan API Key"},
            },
            "required": ["rpc_url", "etherscan_api_key"],
            "secret": ["etherscan_api_key"],
        }

    def __init__(self, configuration):
        super(EVMTransactions, self).__init__(configuration)
        self.syntax = "yaml"

    def test_connection(self):
        if not web3_installed:
            raise Exception("web3 is not installed.")
        w3 = Web3(HTTPProvider(self.configuration["rpc_url"]))
        if not w3.is_connected():
            raise Exception("Could not connect to RPC URL.")

    def get_schema(self, get_stats=False):
        return []

    def run_query(self, query, user):
        if not web3_installed:
            return None, "web3 is not installed."

        try:
            params = yaml.safe_load(query) or {}
        except yaml.YAMLError as e:
            return None, str(e)
        if not isinstance(params, dict):
            return None, "Query must be a YAML object."

        address = params.get("address")
        start_block = params.get("start_block")
        end_block = params.get("end_block")

        if not address or start_block is None or end_block is None:
            return None, "Missing required parameters: start_block, end_block, address"

        try:
            w3 = Web3(HTTPProvider(self.configuration["rpc_url"]))
            address = Web3.to_checksum_address(address)
        except Exception as e:
            return None, "Web3 initialisation error: {0}".format(e)

        if start_block == "latest":
            start_block = w3.eth.block_number
        if end_block == "latest":
            end_block = w3.eth.block_number

        try:
            transactions = self._fetch_transactions(w3, address, int(start_block), int(end_block))
        except Exception as e:
            logger.exception("EVM transactions fetch failed")
            return None, str(e)

        result = {"rows": transactions, "columns": self._columns()}
        return json_dumps(result), None

    @staticmethod
    def _fetch_transactions(w3, address, start_block, end_block):
        rows = []
        for block_num in range(start_block, end_block + 1):
            block = w3.eth.get_block(block_num, full_transactions=True)
            for tx in block.transactions:
                tx_to = tx.get("to")
                tx_from = tx.get("from")
                matches = (tx_to and Web3.to_checksum_address(tx_to) == address) or (
                    tx_from and Web3.to_checksum_address(tx_from) == address
                )
                if not matches:
                    continue
                rows.append(
                    {
                        "block": tx["blockNumber"],
                        "from": tx_from,
                        "to": tx_to,
                        "value": float(Web3.from_wei(tx["value"], "ether")),
                        "gas": tx.get("gas"),
                        "gas_price": tx.get("gasPrice"),
                        "data": tx["input"],
                        "tx_hash": tx["hash"].hex(),
                    }
                )
        return rows

    @staticmethod
    def _columns():
        return [
            {"name": "block", "type": TYPE_INTEGER},
            {"name": "from", "type": TYPE_STRING},
            {"name": "to", "type": TYPE_STRING},
            {"name": "value", "type": TYPE_FLOAT},
            {"name": "gas", "type": TYPE_INTEGER},
            {"name": "gas_price", "type": TYPE_INTEGER},
            {"name": "data", "type": TYPE_STRING},
            {"name": "tx_hash", "type": TYPE_STRING},
        ]


register(EVMTransactions)
