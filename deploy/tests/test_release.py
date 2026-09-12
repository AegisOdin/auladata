import importlib.util
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "release.py"
SPEC = importlib.util.spec_from_file_location("release", SCRIPT)
release = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(release)


class ReleaseValidationTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.path = Path(self.temporary.name) / "release.env"
        self.valid = (
            "BACKEND_IMAGE=ghcr.io/example/auladata-backend@sha256:" + "a" * 64 + "\n"
            "FRONTEND_IMAGE=ghcr.io/example/auladata-frontend@sha256:" + "b" * 64 + "\n"
            "GIT_COMMIT=" + "c" * 40 + "\nAPP_VERSION=v1.0.0\n"
        )

    def read(self, text):
        self.path.write_text(text, encoding="utf-8")
        return release.read_release(self.path)

    def test_valid_digest_manifest_preserves_same_images(self):
        result = self.read(self.valid)
        self.assertEqual(result["GIT_COMMIT"], "c" * 40)
        self.assertTrue(result["BACKEND_IMAGE"].endswith("a" * 64))

    def test_mutable_image_tag_is_rejected(self):
        with self.assertRaises(ValueError):
            self.read(self.valid.replace("@sha256:" + "a" * 64, ":latest"))

    def test_shell_execution_payload_is_rejected(self):
        with self.assertRaises(ValueError):
            self.read(self.valid.replace("APP_VERSION=v1.0.0", "APP_VERSION=$(touch compromised)"))

    def test_unknown_or_secret_keys_are_rejected(self):
        with self.assertRaises(ValueError):
            self.read(self.valid + "JWT_SECRET=not-allowed\n")

    def test_duplicate_keys_are_rejected(self):
        with self.assertRaises(ValueError):
            self.read(self.valid + "APP_VERSION=v9.9.9\n")

    def test_short_git_sha_is_rejected(self):
        with self.assertRaises(ValueError):
            self.read(self.valid.replace("c" * 40, "ccccccc"))

    def test_missing_frontend_is_rejected(self):
        with self.assertRaises(ValueError):
            self.read(
                "\n".join(
                    line
                    for line in self.valid.splitlines()
                    if not line.startswith("FRONTEND_IMAGE=")
                )
            )


if __name__ == "__main__":
    unittest.main()
