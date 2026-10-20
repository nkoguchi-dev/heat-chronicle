import unittest

from probe import NoRedirect, validate_target


class TargetBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.target = {
            "environment": "capacity-test",
            "region": "ap-northeast-1",
            "api_id": "abc123",
            "function_name": "heat-capacity-issue5-local",
            "endpoint": "https://abc123.execute-api.ap-northeast-1.amazonaws.com",
        }

    def test_isolated_target(self):
        validate_target(self.target)

    def test_rejects_prod_and_external_targets(self):
        for key, value in [
            ("environment", "prod"),
            ("function_name", "heat-prod-backend"),
            ("endpoint", "https://heat-chronicle.koppepan.org"),
            ("endpoint", self.target["endpoint"] + "/redirect"),
            ("api_id", "abc/123"),
            ("region", "--profile"),
        ]:
            with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                validate_target({**self.target, key: value})

    def test_redirect_is_not_followed(self):
        self.assertIsNone(
            NoRedirect().redirect_request(
                None, None, 302, "", {}, "https://production.invalid"
            )
        )


if __name__ == "__main__":
    unittest.main()
