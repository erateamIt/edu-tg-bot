import unittest
from unittest.mock import patch

from app import database as db
from app.auto_tag import apply_auto_tags_for_customer, classify_message, normalize_text


class AutoTagTests(unittest.TestCase):
    def test_normalize_text_handles_apostrophes(self):
        self.assertEqual(normalize_text("o‘zingizni qayerda joylashgansiz?"), "o'zingizni qayerda joylashgansiz?")

    def test_python_keyword_detection(self):
        self.assertIn("python", [tag["slug"] for tag in classify_message("Python kursi bormi?")])

    def test_price_keyword_detection(self):
        self.assertIn("price", [tag["slug"] for tag in classify_message("Narxi qancha?")])

    def test_location_keyword_detection(self):
        self.assertIn("location", [tag["slug"] for tag in classify_message("Qayerda joylashgansiz?")])

    def test_ielts_keyword_detection(self):
        self.assertIn("ielts", [tag["slug"] for tag in classify_message("IELTS kursi kerak")])

    def test_interest_keyword_detection(self):
        self.assertIn("interested", [tag["slug"] for tag in classify_message("Yozilmoqchiman")])

    def test_multiple_tags_are_detected(self):
        tags = [tag["slug"] for tag in classify_message("Python kursi narxi qancha?")]
        self.assertIn("python", tags)
        self.assertIn("price", tags)

    def test_auto_tag_disabled_is_ignored(self):
        with patch.object(db, "get_setting", return_value="false"):
            self.assertEqual(apply_auto_tags_for_customer(1, "Python kursi bormi?"), [])

    def test_auto_tags_are_added_once_per_customer(self):
        with patch.object(db, "get_setting", side_effect=lambda key, default=None: {
            "auto_tag_enabled": "true",
            "auto_tag_min_confidence": "0.70",
        }.get(key, default)), patch.object(db, "add_customer_tag") as add_tag, patch.object(db, "get_customer_by_id", return_value={"status_source": "automatic"}):
            result = apply_auto_tags_for_customer(1, "Python kursi narxi qancha?")
        self.assertTrue(result)
        self.assertGreaterEqual(add_tag.call_count, 1)


if __name__ == "__main__":
    unittest.main()
