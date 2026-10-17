"""Offline self-check for check_versions.py: python3 -m unittest test_check_versions (run from scripts/)."""
import tempfile
import unittest
from pathlib import Path

from check_versions import gradle_configured, latest_release, maven_configured, newer


class CheckVersions(unittest.TestCase):
    def test_latest_release_prefers_release_tag(self):
        xml = "<metadata><versioning><latest>0.2.0-SNAPSHOT</latest><release>0.1.0</release></versioning></metadata>"
        self.assertEqual(latest_release(xml), "0.1.0")
        self.assertIsNone(latest_release(""))

    def test_newer(self):
        self.assertTrue(newer("0.2.0", "0.1.0"))
        self.assertTrue(newer("0.1.10", "0.1.9"))
        self.assertTrue(newer("0.0.1", "0.0.1-SNAPSHOT"))
        self.assertFalse(newer("0.1.0", "0.1.0"))
        self.assertFalse(newer(None, "0.1.0"))
        self.assertFalse(newer("0.1.0", None))

    def test_configured_versions(self):
        with tempfile.TemporaryDirectory() as d:
            repo = Path(d)
            (repo / "pom.xml").write_text(
                "<project><properties><to.v>0.0.9</to.v></properties><plugin><groupId>me.bechberger</groupId>"
                "<artifactId>test-order-maven-plugin</artifactId>\n  <version>${to.v}</version></plugin></project>")
            self.assertEqual(maven_configured(repo), "0.0.9")
            (repo / "build.gradle.kts").write_text('plugins { id("me.bechberger.test-order") version "0.0.1-SNAPSHOT" }')
            self.assertEqual(gradle_configured(repo), "0.0.1-SNAPSHOT")
            (repo / "build.gradle.kts").unlink()
            (repo / "build.gradle").write_text("plugins { id 'me.bechberger.test-order' version '0.3.0' }")
            self.assertEqual(gradle_configured(repo), "0.3.0")


if __name__ == "__main__":
    unittest.main()
