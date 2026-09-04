import unittest
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]


class ComposeConfigTests(unittest.TestCase):
    def test_storm_uses_environment_controlled_pangolin_address(self):
        compose = (REPOSITORY_ROOT / "compose.yaml").read_text(encoding="utf-8")

        self.assertIn("pangolin:", compose)
        self.assertIn('ipv4_address: "${STORM_PANGOLIN_IP', compose)
        self.assertIn("external: true", compose)
        self.assertIn("name: pangolin", compose)

    def test_environment_contract_defines_pangolin_address(self):
        environment = (REPOSITORY_ROOT / ".env.example").read_text(encoding="utf-8")

        self.assertIn("STORM_PANGOLIN_IP=", environment)


if __name__ == "__main__":
    unittest.main()
