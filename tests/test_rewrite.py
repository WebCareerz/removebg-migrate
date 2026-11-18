import os
import shutil
import tempfile
import unittest

from removebg_migrate.rewrite import rewrite

HERE = os.path.join(os.path.dirname(__file__), "fixtures")


class RewriteTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        shutil.copytree(HERE, os.path.join(self.tmp, "src"))
        self.root = os.path.join(self.tmp, "src")

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def test_dry_run_does_not_touch_files(self):
        changes = rewrite(self.root, "https://api.clearbg.org/")
        self.assertEqual(len(changes), 3)
        with open(os.path.join(self.root, "legacy_node.js")) as f:
            self.assertIn("api.remove.bg", f.read())
        self.assertTrue(all("+" in d and "api.clearbg.org" in d for _, _, d in changes))

    def test_write(self):
        rewrite(self.root, "api.clearbg.org", write=True)
        with open(os.path.join(self.root, "legacy_curl.sh")) as f:
            text = f.read()
        self.assertNotIn("api.remove.bg", text)
        self.assertEqual(text.count("https://api.clearbg.org/v1.0/"), 2)


if __name__ == "__main__":
    unittest.main()
