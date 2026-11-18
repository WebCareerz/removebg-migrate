import os
import unittest

from removebg_migrate.scan import scan, scan_text

HERE = os.path.join(os.path.dirname(__file__), "fixtures")


def rules_at(findings, name):
    return {f.rule for f in findings if f.path.endswith(name)}


class ScanTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.findings = scan(HERE)

    def test_python_fixture(self):
        r = rules_at(self.findings, "legacy_python.py")
        self.assertTrue({"host", "format_zip", "bg_color_alpha", "crop_margin", "add_shadow",
                         "x_type", "size_large", "ignored_fields"} <= r, r)

    def test_dynamic_shadow_is_reported(self):
        msgs = [f.message for f in self.findings if f.rule == "add_shadow"]
        self.assertTrue(any("variable" in m for m in msgs), msgs)

    def test_node_fixture(self):
        r = rules_at(self.findings, "legacy_node.js")
        self.assertIn("bg_image", r)
        self.assertIn("position", r)
        self.assertNotIn("scale", r)        # 'original' is fine
        self.assertNotIn("size_large", r)   # preview is fine
        self.assertIn("credits_header", r)

    def test_curl_fixture(self):
        r = rules_at(self.findings, "legacy_curl.sh")
        self.assertTrue({"host", "size_large", "shadow_type", "oauth", "improve"} <= r, r)

    def test_unrelated_file_is_ignored(self):
        self.assertEqual(rules_at(self.findings, "unrelated.css.txt"), set())

    def test_errors_sort_after_changes(self):
        order = [f.severity for f in self.findings]
        self.assertEqual(order, sorted(order, key=["change", "error", "check", "info"].index))

    def test_curl_literal_is_not_a_variable(self):
        msgs = [f.message for f in self.findings if f.rule == "shadow_type"]
        self.assertEqual(len(msgs), 1)
        self.assertNotIn("variable", msgs[0])

    def test_query_string_literal(self):
        text = 'u = "https://api.remove.bg/v1.0/removebg?size=preview&scale=50%"\n'
        self.assertIn("scale", {f.rule for f in scan_text("x.py", text)})

    def test_valid_values_pass(self):
        text = 'URL = "https://api.remove.bg/v1.0/removebg"\ndata = {"crop_margin": "0px", "bg_color": "#fff", "format": "png"}\n'
        self.assertEqual({f.rule for f in scan_text("x.py", text)}, {"host"})


if __name__ == "__main__":
    unittest.main()
