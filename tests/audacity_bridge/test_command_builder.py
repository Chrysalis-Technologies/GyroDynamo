import unittest

from audacity_bridge.commands import build_command


class BuildCommandTests(unittest.TestCase):
    def test_build_command_quotes_strings_and_paths(self) -> None:
        cmd = build_command("Import2", Filename=r"C:\\Audio Files\\demo.wav")
        self.assertEqual(cmd, 'Import2: Filename="C:\\\\Audio Files\\\\demo.wav"')

    def test_build_command_formats_numbers_and_bool(self) -> None:
        cmd = build_command("Repeat", Count=3, Enabled=True, Ratio=1.25)
        self.assertEqual(cmd, "Repeat: Count=3 Enabled=1 Ratio=1.25")

    def test_build_command_strips_trailing_colon(self) -> None:
        cmd = build_command("Help:", Command="Echo")
        self.assertEqual(cmd, 'Help: Command="Echo"')

    def test_build_command_requires_name(self) -> None:
        with self.assertRaises(ValueError):
            build_command("  ")


if __name__ == "__main__":
    unittest.main()
