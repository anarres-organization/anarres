import unittest

from anarres.core.adapter_protocol import consume_adapter_invocation


class AdapterProtocolTest(unittest.TestCase):
    def test_direct_invocation_is_unchanged(self) -> None:
        arguments = ["status", "--json"]
        self.assertIs(consume_adapter_invocation(arguments, expected_name="finance"), arguments)

    def test_valid_runtime_handshake_is_consumed(self) -> None:
        self.assertEqual(
            consume_adapter_invocation(
                [
                    "--anarres-adapter-protocol",
                    "2",
                    "--anarres-adapter-name",
                    "finance",
                    "status",
                    "--json",
                ],
                expected_name="finance",
            ),
            ["status", "--json"],
        )

    def test_invalid_runtime_handshakes_are_rejected(self) -> None:
        cases = [
            (["--anarres-adapter-protocol", "2"], "malformed"),
            (
                [
                    "--anarres-adapter-protocol",
                    "1",
                    "--anarres-adapter-name",
                    "finance",
                ],
                "unsupported",
            ),
            (
                [
                    "--anarres-adapter-protocol",
                    "2",
                    "--anarres-adapter-name",
                    "legal",
                ],
                "identity",
            ),
        ]
        for arguments, message in cases:
            with self.subTest(arguments=arguments), self.assertRaisesRegex(ValueError, message):
                consume_adapter_invocation(arguments, expected_name="finance")


if __name__ == "__main__":
    unittest.main()
