import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from aoe2hdcontrol.screenshot_v3_3_5 import screenshot_client

class TestScreenshotV335(unittest.TestCase):
    def test_reject_non_windows(self):
        if os.name == "nt":
            self.skipTest("Non-Windows guard")
        with self.assertRaises(OSError):
            screenshot_client(123, "unreachable.bmp")

    def test_no_image_created_on_unsupported_platform(self):
        if os.name == "nt":
            self.skipTest("Non-Windows guard")
        with tempfile.TemporaryDirectory() as td:
            dest=Path(td)/"frame.bmp"
            with self.assertRaises(OSError):
                screenshot_client(123, dest)
            self.assertFalse(dest.exists())

    def test_cli_requires_allow_candidates(self):
        from aoe2hdcontrol.__main__ import main
        with self.assertRaises(SystemExit) as e:
            main(["capture-anchor-v3-3-5","--pid","5","--id","2630","--delay","0",
                  "--output","test.json"])
        self.assertEqual(e.exception.code,2)

    def test_cli_reject_delay_over_limit(self):
        from aoe2hdcontrol.__main__ import main
        with self.assertRaises(SystemExit) as e:
            main(["capture-anchor-v3-3-5","--pid","5","--id","2630","--delay","121",
                  "--allow-candidates","--output","test.json"])
        self.assertEqual(e.exception.code,2)

    def test_cli_reject_same_json_and_bmp_path(self):
        from aoe2hdcontrol.__main__ import main
        with patch("aoe2hdcontrol.__main__.time",create=True):
            outcome=main(["capture-anchor-v3-3-5","--pid","5","--id","2630",
                          "--delay","0","--allow-candidates",
                          "--output","same.json","--image","same.json"])
        self.assertEqual(outcome,1)
if __name__=="__main__":
    unittest.main()
