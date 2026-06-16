import sys
import unittest
from unittest.mock import MagicMock, patch

sys.modules.setdefault("shazamio", MagicMock())

from fastapi import HTTPException

from app.main import _verify_api_key


class TestVerifyApiKey(unittest.TestCase):
    @patch("app.main.settings")
    def test_non_ascii_client_key_returns_401_not_500(self, settings):
        settings.api_key = "b027cc1cea67fb74c18f69fd4fb54862ba2e2d17e3f6cc588e1479e98074ffe3"
        with self.assertRaises(HTTPException) as ctx:
            _verify_api_key("••••••••ffe3")
        self.assertEqual(ctx.exception.status_code, 401)


if __name__ == "__main__":
    unittest.main()
