import unittest

from audacity_bridge.response_parser import parse_response


class ParseResponseTests(unittest.TestCase):
    def test_parse_json_payload_with_ok_status(self) -> None:
        raw = '{"k": 1}\nBatchCommand finished: OK\n\n'
        parsed = parse_response("GetInfo:", raw)
        self.assertTrue(parsed.ok)
        self.assertEqual(parsed.status, "OK")
        self.assertEqual(parsed.json_payload, {"k": 1})

    def test_parse_failed_status(self) -> None:
        raw = "Something bad\nBatchCommand finished: Failed!\n\n"
        parsed = parse_response("Echo:", raw)
        self.assertFalse(parsed.ok)
        self.assertEqual(parsed.status, "Failed!")

    def test_parse_plain_text_without_status(self) -> None:
        raw = "Plain output\n\n"
        parsed = parse_response("Help:", raw)
        self.assertTrue(parsed.ok)
        self.assertEqual(parsed.payload, "Plain output")
        self.assertIsNone(parsed.json_payload)


if __name__ == "__main__":
    unittest.main()
