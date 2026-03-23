import unittest
from pathlib import Path

from audacity_bridge.commands import AudacityBridge, build_command
from audacity_bridge.config import AudacityBridgeConfig


class _FakeTransport:
    def __init__(self) -> None:
        self.commands: list[str] = []
        self.connected = False

    def connect(self) -> None:
        self.connected = True

    def disconnect(self) -> None:
        self.connected = False

    def send_command(self, command: str, *, timeout_s=None) -> str:
        self.commands.append(command)
        return "BatchCommand finished: OK\n\n"


_FIXTURE_PROJECT = (Path(__file__).resolve().parent / "fixtures" / "test_project.aup3").resolve()


class CommandWrapperTests(unittest.TestCase):
    def setUp(self) -> None:
        self.transport = _FakeTransport()
        self.bridge = AudacityBridge(config=AudacityBridgeConfig(), transport=self.transport)

    def test_open_project_builds_openproject2_command(self) -> None:
        self.bridge.open_project(str(_FIXTURE_PROJECT))

        expected = build_command(
            "OpenProject2",
            Filename=str(_FIXTURE_PROJECT),
            AddToHistory=False,
        )
        self.assertEqual(self.transport.commands[-1], expected)

    def test_open_project_appends_aup3_extension(self) -> None:
        self.bridge.open_project(str(_FIXTURE_PROJECT.with_suffix("")))

        expected = build_command(
            "OpenProject2",
            Filename=str(_FIXTURE_PROJECT),
            AddToHistory=False,
        )
        self.assertEqual(self.transport.commands[-1], expected)

    def test_open_project_raises_when_missing(self) -> None:
        with self.assertRaises(FileNotFoundError):
            self.bridge.open_project(str(_FIXTURE_PROJECT.parent / "missing_project.aup3"))

    def test_select_all_uses_selectall_command(self) -> None:
        self.bridge.select_all()
        self.assertEqual(self.transport.commands[-1], "SelectAll:")


if __name__ == "__main__":
    unittest.main()
