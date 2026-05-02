"""EVM event-logs query runner.

Queries are written as YAML, e.g.

    contract_address: "0xdAC17F958D2ee523a2206206994597C13D831ec7"
    event_name: Transfer
    start_block: -10000
    end_block: latest
    args:
      to: "0x..."

The runner fetches event logs for the requested block range, decodes them
with the contract ABI (pulled from Etherscan) and returns one row per event.
Ported from inverse-watch with ``SmartContract`` removed in favour of direct
Etherscan ABI fetches.
"""
import datetime
import logging
import time
from concurrent.futures import ThreadPoolExecutor

import yaml

from redash.query_runner import (
    TYPE_BOOLEAN,
    TYPE_DATETIME,
    TYPE_FLOAT,
    TYPE_INTEGER,
    TYPE_STRING,
    BaseHTTPQueryRunner,
    register,
)
from redash.query_runner._evm_abi import (
    fetch_abi_from_etherscan,
    fetch_contract_creation_block,
)
from redash.utils import json_dumps

logger = logging.getLogger(__name__)

try:
    from web3 import Web3
    from web3.middleware import geth_poa_middleware

    web3_installed = True
except ImportError:
    Web3 = None
    geth_poa_middleware = None
    web3_installed = False


def _value_type(value):
    if isinstance(value, bool):
        return TYPE_BOOLEAN
    if isinstance(value, int):
        return TYPE_STRING if value > 2**32 else TYPE_INTEGER
    if isinstance(value, float):
        return TYPE_FLOAT
    if isinstance(value, datetime.datetime):
        return TYPE_DATETIME
    return TYPE_STRING


class EVMLogs(BaseHTTPQueryRunner):
    requires_url = False

    @classmethod
    def enabled(cls):
        return web3_installed

    @classmethod
    def type(cls):
        return "evmlogs"

    @classmethod
    def name(cls):
        return "EVM Logs"

    @classmethod
    def configuration_schema(cls):
        return {
            "type": "object",
            "properties": {
                "rpc_url": {"type": "string", "title": "Ethereum RPC URL"},
                "etherscan_api_key": {"type": "string", "title": "Etherscan API Key"},
                "etherscan_api_base": {
                    "type": "string",
                    "title": "Etherscan API base URL",
                    "default": "https://api.etherscan.io/api",
                },
                "log_chunk_size": {
                    "type": "integer",
                    "title": "Block range chunk size",
                    "default": 10000,
                },
                "max_workers": {
                    "type": "integer",
                    "title": "Parallel chunk fetchers",
                    "default": 4,
                },
            },
            "required": ["rpc_url", "etherscan_api_key"],
            "secret": ["etherscan_api_key"],
            "order": ["rpc_url", "etherscan_api_key", "etherscan_api_base"],
        }

    def __init__(self, configuration):
        super(EVMLogs, self).__init__(configuration)
        self.syntax = "yaml"

    def test_connection(self):
        if not web3_installed:
            raise Exception("web3 is not installed; install the all_ds dependency group.")
        w3 = Web3(Web3.HTTPProvider(self.configuration["rpc_url"]))
        if not w3.is_connected():
            raise Exception("Could not connect to RPC URL.")

    def get_schema(self, get_stats=False):
        return []

    # ------------------------------------------------------------ ABI helpers

    def _abi(self, address, implementation_address=None):
        target = implementation_address or address
        return fetch_abi_from_etherscan(
            target,
            self.configuration["etherscan_api_key"],
            self.configuration.get("etherscan_api_base", "https://api.etherscan.io/api"),
        )

    @staticmethod
    def _event_abi(contract, event_name):
        for entry in contract.abi:
            if entry.get("type") == "event" and entry.get("name") == event_name:
                return entry
        raise ValueError("Event '{0}' not found in contract ABI".format(event_name))

    # ------------------------------------------------------------- run_query

    def run_query(self, query, user):
        if not web3_installed:
            return None, "web3 is not installed."

        try:
            params = yaml.safe_load(query) or {}
        except yaml.YAMLError as e:
            return None, str(e)
        if not isinstance(params, dict):
            return None, "Query must be a YAML object."

        addresses = params.get("contract_address") or []
        if not isinstance(addresses, list):
            addresses = [addresses]
        try:
            addresses = [Web3.to_checksum_address(a) for a in addresses]
        except Exception as e:
            return None, "Invalid contract address: {0}".format(e)
        if not addresses:
            return None, "Missing required field 'contract_address'."

        implementation_address = params.get("implementation_address")
        if implementation_address:
            try:
                implementation_address = Web3.to_checksum_address(implementation_address)
            except Exception as e:
                return None, "Invalid implementation address: {0}".format(e)

        event_name = params.get("event_name")
        event_names = event_name if isinstance(event_name, list) else [event_name] if event_name else []
        if not event_names:
            return None, "Missing required field 'event_name'."

        start_block = params.get("start_block")
        end_block = params.get("end_block")
        arg_filters = params.get("args") or {}

        try:
            w3 = Web3(Web3.HTTPProvider(self.configuration["rpc_url"]))
            w3.middleware_onion.inject(geth_poa_middleware, layer=0)
        except Exception as e:
            return None, "Error initialising web3: {0}".format(e)

        rows = []
        try:
            for address in addresses:
                abi = self._abi(address, implementation_address)
                contract = w3.eth.contract(address=address, abi=abi)
                for evt in event_names:
                    rows.extend(
                        self._fetch_event_logs(
                            w3, contract, evt, start_block, end_block, arg_filters
                        )
                    )
        except Exception as e:
            logger.exception("EVM logs fetch failed")
            return None, str(e)

        result = {"rows": rows, "columns": self._columns_from_rows(rows)}
        return json_dumps(result), None

    # ----------------------------------------------------------- log fetchers

    def _fetch_event_logs(self, w3, contract, event_name, start_block, end_block, arg_filters):
        event_abi = self._event_abi(contract, event_name)
        signature = "{0}({1})".format(
            event_name, ",".join(i["type"] for i in event_abi["inputs"])
        )
        topic = Web3.keccak(text=signature).hex()

        if start_block in (None, "earliest"):
            start_block = fetch_contract_creation_block(
                contract.address,
                self.configuration["etherscan_api_key"],
                self.configuration.get("etherscan_api_base", "https://api.etherscan.io/api"),
            )
        if start_block == "latest":
            start_block = w3.eth.block_number
        if end_block in (None, "latest"):
            end_block = w3.eth.block_number
        if isinstance(start_block, int) and start_block < 0:
            start_block = end_block + start_block

        chunk = int(self.configuration.get("log_chunk_size") or 10000)
        max_workers = int(self.configuration.get("max_workers") or 4)
        results = []

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = []
            for block in range(start_block, end_block, chunk):
                end = min(block + chunk, end_block)
                futures.append(
                    executor.submit(
                        self._fetch_chunk, w3, contract, topic, event_name, block, end, arg_filters
                    )
                )
            for future in futures:
                results.extend(future.result())
        return results

    def _fetch_chunk(self, w3, contract, topic, event_name, from_block, to_block, arg_filters):
        backoff = 0.1
        for attempt in range(5):
            try:
                if attempt:
                    time.sleep(backoff)
                logs = w3.eth.get_logs(
                    {
                        "fromBlock": from_block,
                        "toBlock": to_block,
                        "address": contract.address,
                        "topics": [topic],
                    }
                )
                break
            except Exception as e:
                backoff *= 2
                logger.warning("get_logs failed (%s/5): %s", attempt + 1, e)
        else:
            return []

        out = []
        for log in logs:
            try:
                event_data = contract.events[event_name]().process_log(log)
                try:
                    block_time = w3.eth.get_block(log["blockNumber"])["timestamp"]
                except Exception:
                    block_time = None

                row = {
                    "block": log["blockNumber"],
                    "block_time": block_time,
                    "address": log["address"],
                    "transaction_hash": log["transactionHash"].hex(),
                    "log_index": log["logIndex"],
                    "event_name": event_name,
                }

                if arg_filters and not self._matches_filters(event_data["args"], arg_filters):
                    continue
                row.update(dict(event_data["args"]))
                out.append(row)
            except Exception as e:
                logger.warning("Skipping unparseable log: %s", e)
        return out

    @staticmethod
    def _matches_filters(args, filters):
        for key, value in filters.items():
            if key not in args:
                return False
            arg_value = args[key]
            if isinstance(arg_value, str) and isinstance(value, str):
                if arg_value.lower() != value.lower():
                    return False
            elif arg_value != value:
                return False
        return True

    @staticmethod
    def _columns_from_rows(rows):
        if not rows:
            return [
                {"name": "block", "type": TYPE_INTEGER},
                {"name": "block_time", "type": TYPE_INTEGER},
                {"name": "address", "type": TYPE_STRING},
                {"name": "transaction_hash", "type": TYPE_STRING},
                {"name": "log_index", "type": TYPE_INTEGER},
                {"name": "event_name", "type": TYPE_STRING},
            ]
        seen = set()
        columns = []
        for key, value in rows[0].items():
            if key in seen:
                continue
            seen.add(key)
            ctype = TYPE_INTEGER if key == "block_time" else _value_type(value)
            columns.append({"name": key, "type": ctype})
        return columns


register(EVMLogs)
