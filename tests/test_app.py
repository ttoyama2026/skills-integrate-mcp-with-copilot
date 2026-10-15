import unittest
from concurrent.futures import ThreadPoolExecutor

from fastapi import HTTPException

from src import app as app_module


class SignupCapacityTests(unittest.TestCase):
    def setUp(self):
        self.original_activity = app_module.activities["Chess Club"]
        app_module.activities["Chess Club"] = {
            "max_participants": 2,
            "participants": ["existing@mergington.edu"],
        }

    def tearDown(self):
        app_module.activities["Chess Club"] = self.original_activity

    def test_signup_succeeds_below_capacity(self):
        result = app_module.signup_for_activity(
            "Chess Club", "new@mergington.edu"
        )

        self.assertEqual(
            result,
            {"message": "Signed up new@mergington.edu for Chess Club"},
        )
        self.assertEqual(
            app_module.activities["Chess Club"]["participants"],
            ["existing@mergington.edu", "new@mergington.edu"],
        )

    def test_signup_at_capacity_is_rejected(self):
        app_module.activities["Chess Club"]["participants"].append(
            "another@mergington.edu"
        )

        with self.assertRaises(HTTPException) as raised:
            app_module.signup_for_activity("Chess Club", "new@mergington.edu")

        self.assertEqual(raised.exception.status_code, 400)
        self.assertEqual(
            raised.exception.detail,
            "Activity has reached its maximum capacity",
        )
        self.assertEqual(
            len(app_module.activities["Chess Club"]["participants"]), 2
        )

    def test_duplicate_signup_behavior_is_preserved_at_capacity(self):
        app_module.activities["Chess Club"]["participants"].append(
            "another@mergington.edu"
        )

        with self.assertRaises(HTTPException) as raised:
            app_module.signup_for_activity(
                "Chess Club", "existing@mergington.edu"
            )

        self.assertEqual(raised.exception.status_code, 400)
        self.assertEqual(raised.exception.detail, "Student is already signed up")

    def test_unknown_activity_behavior_is_preserved(self):
        with self.assertRaises(HTTPException) as raised:
            app_module.signup_for_activity(
                "Unknown Club", "new@mergington.edu"
            )

        self.assertEqual(raised.exception.status_code, 404)
        self.assertEqual(raised.exception.detail, "Activity not found")

    def test_concurrent_signups_do_not_exceed_capacity(self):
        emails = [
            f"student{index}@mergington.edu" for index in range(10)
        ]

        def signup(email):
            try:
                app_module.signup_for_activity("Chess Club", email)
                return True
            except HTTPException as error:
                if error.detail != "Activity has reached its maximum capacity":
                    raise
                return False

        with ThreadPoolExecutor(max_workers=len(emails)) as executor:
            results = list(executor.map(signup, emails))

        participants = app_module.activities["Chess Club"]["participants"]
        self.assertEqual(sum(results), 1)
        self.assertEqual(len(participants), 2)


if __name__ == "__main__":
    unittest.main()
