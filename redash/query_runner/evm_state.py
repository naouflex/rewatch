"""EVM contract-state query runner.

Reads the result of a view/pure function call across one or many blocks.
Queries are written as YAML, e.g.

    contract_address: "0xdAC17F958D2ee523a2206206994597C13D831ec7"
    function_name: balanceOf
    args:
      - "0x..."
    start_block: 18000000
    end_block: latest
    lag: 100

Ported from inverse-watch with the ``SmartContract`` cache removed in favour
of direct Etherscan ABI lookups.
"""
import logging

import yaml

from rewatch.query_runner import (
    TYPE_INTEGER,
    TYPE_STRING,
    BaseHTTPQueryRunner,
    register,
)
from rewatch.query_runner._evm_abi import fetch_abi_from_etherscan
from rewatch.utils import json_dumps

logger = logging.getLogger(__name__)

try:
    from web3 import Web3
    from web3.middleware import geth_poa_middleware

    web3_installed = True
except ImportError:
    Web3 = None
    geth_poa_middleware = None
    web3_installed = False


class EVMState(BaseHTTPQueryRunner):
    requires_url = False

    @classmethod
    def enabled(cls):
        return web3_installed

    @classmethod
    def type(cls):
        return "evmstate"

    @classmethod
    def name(cls):
        return "EVM State"

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
            },
            "required": ["rpc_url", "etherscan_api_key"],
            "secret": ["etherscan_api_key"],
        }

    def __init__(self, configuration):
        super(EVMState, self).__init__(configuration)
        self.syntax = "yaml"

    def test_connection(self):
        if not web3_installed:
            raise Exception("web3 is not installed.")
        w3 = Web3(Web3.HTTPProvider(self.configuration["rpc_url"]))
        if not w3.is_connected():
            raise Exception("Could not connect to RPC URL.")

    def get_schema(self, get_stats=False):
        return []

    def _abi(self, address, implementation_address=None):
        target = implementation_address or address
        return fetch_abi_from_etherscan(
            target,
            self.configuration["etherscan_api_key"],
            self.configuration.get("etherscan_api_base", "https://api.etherscan.io/api"),
        )

    @staticmethod
    def _coerce_arg(arg):
        if isinstance(arg, str):
            if arg.startswith("0x") and len(arg) == 42:
                return Web3.to_checksum_address(arg)
            if arg.lower() in ("true", "false"):
                return arg.lower() == "true"
            if arg.isnumeric():
                return int(arg)
        return arg

    def _resolve_blocks(self, w3, start_block, end_block, lag):
        if start_block == "latest":
            start_block = w3.eth.block_number
        if end_block == "latest":
            end_block = w3.eth.block_number
        if isinstance(start_block, int) and start_block < 0 and isinstance(end_block, int):
            start_block = end_block + start_block

        if start_block is None and end_block is None:
            return [w3.eth.block_number]
        if start_block == end_block:
            return [start_block]
        if start_block is not None and end_block is not None:
            return list(range(start_block, end_block + 1, lag or 1))
        return [start_block if start_block is not None else end_block]

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

        function_names = params.get("function_name") or []
        if not isinstance(function_names, list):
            function_names = [function_names]
        if not function_names:
            return None, "Missing required field 'function_name'."

        args = params.get("args") or [[]]
        args_list = args if (isinstance(args, list) and (not args or isinstance(args[0], list))) else [args]
        args_list = [[self._coerce_arg(a) for a in arglist] for arglist in args_list]

        start_block = params.get("start_block")
        end_block = params.get("end_block")
        lag = params.get("lag")
        index = params.get("index")
        sub_index = params.get("sub_index")

        try:
            w3 = Web3(Web3.HTTPProvider(self.configuration["rpc_url"]))
            w3.middleware_onion.inject(geth_poa_middleware, layer=0)
        except Exception as e:
            return None, "Error initialising web3: {0}".format(e)

        blocks = self._resolve_blocks(w3, start_block, end_block, lag)

        rows = []
        try:
            for address in addresses:
                abi = self._abi(address, implementation_address)
                contract = w3.eth.contract(address=address, abi=abi)
                for function_name in function_names:
                    for arglist in args_list:
                        rows.extend(
                            self._call_function(
                                w3, contract, function_name, arglist, blocks, index, sub_index
                            )
                        )
        except Exception as e:
            logger.exception("EVM state call failed")
            return None, str(e)

        result = {"rows": rows, "columns": self._columns(rows)}
        return json_dumps(result), None

    def _call_function(self, w3, contract, function_name, args, blocks, index=None, sub_index=None):
        try:
            function = contract.functions[function_name]
        except KeyError:
            raise Exception("Function '{0}' not found on contract.".format(function_name))

        out = []
        for block in blocks:
            try:
                if not args or args == [None]:
                    value = function().call(block_identifier=block)
                else:
                    value = function(*args).call(block_identifier=block)
                if index is not None:
                    value = value[int(index)]
                    if sub_index is not None:
                        value = value[int(sub_index)]
            except Exception as e:
                logger.warning(
                    "Call %s(%s)@%s failed: %s", function_name, args, block, e
                )
                value = None

            try:
                block_time = w3.eth.get_block(block)["timestamp"]
            except Exception:
                block_time = None

            out.append(
                {
                    "block": block,
                    "block_time": block_time,
                    "contract_address": contract.address,
                    "function_name": function_name,
                    "args": json_dumps(args),
                    "value": str(value) if value is not None else None,
                }
            )
        return out

    @staticmethod
    def _columns(rows):
        return [
            {"name": "block", "friendly_name": "Block", "type": TYPE_INTEGER},
            {"name": "block_time", "friendly_name": "Block Time", "type": TYPE_INTEGER},
            {"name": "function_name", "friendly_name": "Function", "type": TYPE_STRING},
            {"name": "args", "friendly_name": "Arguments", "type": TYPE_STRING},
            {"name": "contract_address", "friendly_name": "Contract", "type": TYPE_STRING},
            {"name": "value", "friendly_name": "Value", "type": TYPE_STRING},
        ]


register(EVMState)
