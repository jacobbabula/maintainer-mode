from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "plugins" / "maintainer-mode"


class DistributionTests(unittest.TestCase):
    def test_repository_marketplace_resolves_to_installable_bundle(self) -> None:
        marketplace = json.loads(
            (ROOT / ".agents" / "plugins" / "marketplace.json").read_text(encoding="utf-8")
        )
        self.assertEqual(marketplace["name"], "maintainer-mode")
        self.assertEqual(len(marketplace["plugins"]), 1)
        entry = marketplace["plugins"][0]
        self.assertEqual(entry["name"], "maintainer-mode")
        self.assertEqual(entry["source"], {"source": "local", "path": "./plugins/maintainer-mode"})
        self.assertEqual(entry["policy"]["installation"], "AVAILABLE")
        self.assertEqual(entry["policy"]["authentication"], "ON_INSTALL")

    def test_bundle_manifest_points_to_real_components(self) -> None:
        manifest = json.loads((PLUGIN / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["name"], PLUGIN.name)
        self.assertEqual(manifest["version"], "0.1.0")
        self.assertTrue((PLUGIN / manifest["skills"]).is_dir())
        interface = manifest["interface"]
        self.assertTrue((PLUGIN / interface["composerIcon"]).is_file())
        self.assertTrue((PLUGIN / interface["logo"]).is_file())

    def test_every_skill_can_resolve_the_bundled_runner(self) -> None:
        runner = PLUGIN / "scripts" / "maintainer_mode.py"
        self.assertTrue(runner.is_file())
        skill_files = sorted((PLUGIN / "skills").glob("*/SKILL.md"))
        self.assertEqual(len(skill_files), 4)
        for skill in skill_files:
            self.assertEqual((skill.parent / "../../scripts/maintainer_mode.py").resolve(), runner.resolve())

    def test_registry_and_marketplace_skills_stay_identical(self) -> None:
        for bundled in sorted((PLUGIN / "skills").glob("**/*")):
            if bundled.is_file():
                registry = ROOT / "skills" / bundled.relative_to(PLUGIN / "skills")
                self.assertTrue(registry.is_file())
                self.assertEqual(registry.read_bytes(), bundled.read_bytes())

    def test_root_manifest_remains_registry_discoverable(self) -> None:
        manifest = json.loads((ROOT / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["repository"], "https://github.com/jacobbabula/maintainer-mode")
        self.assertEqual(manifest["license"], "MIT")
        self.assertTrue((ROOT / manifest["skills"]).is_dir())
        self.assertTrue((ROOT / manifest["interface"]["composerIcon"]).is_file())


if __name__ == "__main__":
    unittest.main()
