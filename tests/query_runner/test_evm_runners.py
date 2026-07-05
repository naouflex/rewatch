"""Unit tests for the EVM logs / state / transactions query runners.

Web3 calls are mocked end-to-end. If web3 isn't installed in the test
environment we just skip the runtime tests but still verify metadata.
"""
import json
from unittest import TestCase
from unittest import mock

from rewatch.query_runner import evm_logs as evm_logs_module
from rewatch.query_runner import evm_state as evm_state_module
from rewatch.query_runner import evm_transactions as evm_tx_module
from rewatch.query_runner.evm_logs import EVMLogs
from rewatch.query_runner.evm_state import EVMState
from rewatch.query_runner.evm_transactions import EVMTransactions


CONFIG = {
    "rpc_url": "https://example/rpc",
    "etherscan_api_key": "key",
}


class TestEVMRunnerMetadata(TestCase):
    def test_logs_metadata(self):
        self.assertEqual(EVMLogs.type(), "evmlogs")
        self.assertFalse(EVMLogs.requires_url)

    def test_state_metadata(self):
        self.assertEqual(EVMState.type(), "evmstate")
        self.assertFalse(EVMState.requires_url)

    def test_transactions_metadata(self):
        self.assertEqual(EVMTransactions.type(), "evmtransactions")
        self.assertFalse(EVMTransactions.requires_url)

    def test_logs_required_fields(self):
        schema = EVMLogs.configuration_schema()
        for field in ("rpc_url", "etherscan_api_key"):
            self.assertIn(field, schema["required"])
        self.assertIn("etherscan_api_key", schema["secret"])


class TestEVMRunnerYAML(TestCase):
    """The early YAML-validation paths don't actually need web3, so we test
    them unconditionally and only short-circuit when web3 is missing."""

    def test_logs_missing_address(self):
        runner = EVMLogs(CONFIG)
        if not evm_logs_module.web3_installed:
            self.skipTest("web3 not installed")
        data, error = runner.run_query("event_name: Transfer", None)
        self.assertIsNone(data)
        self.assertIn("contract_address", error)

    def test_logs_missing_event(self):
        runner = EVMLogs(CONFIG)
        if not evm_logs_module.web3_installed:
            self.skipTest("web3 not installed")
        data, error = runner.run_query(
            'contract_address: "0x0000000000000000000000000000000000000001"', None
        )
        self.assertIsNone(data)
        self.assertIn("event_name", error)

    def test_state_missing_function(self):
        runner = EVMState(CONFIG)
        if not evm_state_module.web3_installed:
            self.skipTest("web3 not installed")
        data, error = runner.run_query(
            'contract_address: "0x0000000000000000000000000000000000000001"', None
        )
        self.assertIsNone(data)
        self.assertIn("function_name", error)

    def test_transactions_missing_address(self):
        runner = EVMTransactions(CONFIG)
        if not evm_tx_module.web3_installed:
            self.skipTest("web3 not installed")
        data, error = runner.run_query("start_block: 1\nend_block: 2", None)
        self.assertIsNone(data)
        self.assertIn("Missing required parameters", error)


class TestEVMTransactionsFiltering(TestCase):
    """Verify the OR condition (the operator-precedence bug from the
    inverse-watch source is fixed) by stubbing web3."""

    def test_filters_by_either_from_or_to(self):
        if not evm_tx_module.web3_installed:
            self.skipTest("web3 not installed")
        from rewatch.query_runner.evm_transactions import EVMTransactions, Web3

        target = "0x0000000000000000000000000000000000000001"
        other = "0x0000000000000000000000000000000000000002"

        # Two transactions: one matches via `to`, one via `from`, one doesn't match.
        block = mock.Mock()
        block.transactions = [
            {
                "blockNumber": 1,
                "from": other,
                "to": target,
                "value": 10**18,
                "gas": 21000,
                "gasPrice": 1,
                "input": "0x",
                "hash": mock.Mock(hex=mock.Mock(return_value="0xa")),
            },
            {
                "blockNumber": 1,
                "from": target,
                "to": other,
                "value": 0,
                "gas": 21000,
                "gasPrice": 1,
                "input": "0x",
                "hash": mock.Mock(hex=mock.Mock(return_value="0xb")),
            },
            {
                "blockNumber": 1,
                "from": other,
                "to": other,
                "value": 0,
                "gas": 21000,
                "gasPrice": 1,
                "input": "0x",
                "hash": mock.Mock(hex=mock.Mock(return_value="0xc")),
            },
        ]
        w3 = mock.Mock()
        w3.eth.get_block.return_value = block

        rows = EVMTransactions._fetch_transactions(
            w3, Web3.to_checksum_address(target), 1, 1
        )
        self.assertEqual(len(rows), 2)
        hashes = {r["tx_hash"] for r in rows}
        self.assertEqual(hashes, {"0xa", "0xb"})
