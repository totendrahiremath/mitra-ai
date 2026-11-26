import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parents[1] / "mitra ai"
sys.path.insert(0, str(PROJECT_DIR))

import database


class SecretRedactionTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.old_db_name = database.DB_NAME
        self.old_legacy_db_name = database.OLD_DB_NAME
        database.DB_NAME = str(Path(self.temp_dir.name) / "memory.sqlite3")
        database.OLD_DB_NAME = str(Path(self.temp_dir.name) / "legacy.sqlite3")
        database.init_db()

    def tearDown(self):
        database.DB_NAME = self.old_db_name
        database.OLD_DB_NAME = self.old_legacy_db_name
        self.temp_dir.cleanup()

    def stored_rows(self):
        with sqlite3.connect(database.DB_NAME) as connection:
            return connection.execute(
                "SELECT user_input, response FROM interactions"
            ).fetchall()

    def test_redacts_google_api_key_pattern(self):
        secret = "AIzaSyA1b2C3d4E5f6G7h8I9j0K1l2M3n4O5p6Q7"
        cleaned = database._redact_secrets("key=" + secret)
        self.assertNotIn(secret, cleaned)
        self.assertIn("[REDACTED_API_KEY]", cleaned)

    def test_redacts_key_setting_command(self):
        cleaned = database._redact_secrets("set gemini api key to LOCAL-SECRET-123")
        self.assertNotIn("LOCAL-SECRET-123", cleaned)
        self.assertIn("[REDACTED]", cleaned)

    def test_redacts_environment_assignment(self):
        cleaned = database._redact_secrets("GEMINI_API_KEY=LOCAL-SECRET-123")
        self.assertNotIn("LOCAL-SECRET-123", cleaned)
        self.assertIn("[REDACTED]", cleaned)

    def test_normal_logging_redacts_secret(self):
        secret = "AIzaSyA1b2C3d4E5f6G7h8I9j0K1l2M3n4O5p6Q7"
        database.log_interaction("My key is " + secret, "received " + secret)
        rows = self.stored_rows()
        self.assertEqual(len(rows), 1)
        self.assertNotIn(secret, str(rows))

    def test_imported_conversations_redact_secrets(self):
        secret = "AIzaSyA1b2C3d4E5f6G7h8I9j0K1l2M3n4O5p6Q7"
        inserted = database.insert_interactions_batch([
            ("2026-01-01 10:00:00", "Imported key " + secret, "Response " + secret)
        ])
        self.assertEqual(inserted, 1)
        self.assertNotIn(secret, str(self.stored_rows()))


if __name__ == "__main__":
    unittest.main()
