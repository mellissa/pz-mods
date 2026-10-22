import contextlib
import io
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))

import pzmods  # noqa: E402


def run(*argv: str) -> tuple[int, str]:
    out = io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(out):
        code = pzmods.main(list(argv))
    return code, out.getvalue()


class PzModsTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)
        self.original = (pzmods.REPO_ROOT, pzmods.MODS_DIR)
        pzmods.REPO_ROOT = self.tmp
        pzmods.MODS_DIR = self.tmp / "pz"
        self.addCleanup(self.restore)

    def restore(self) -> None:
        pzmods.REPO_ROOT, pzmods.MODS_DIR = self.original

    def mod_version_dir(self, mod_id: str) -> Path:
        return self.tmp / "pz" / mod_id / "Contents" / "mods" / mod_id / "42"

    def test_new_mod_is_valid(self) -> None:
        code, _ = run("new", "RainCatcher", "--name", 'Rain "Catcher"')
        self.assertEqual(code, 0)
        code, out = run("validate")
        self.assertEqual(code, 0, out)
        self.assertTrue((self.mod_version_dir("RainCatcher") / "media/lua/client/RainCatcher_Client.lua").is_file())
        self.assertEqual(pzmods.png_size(self.tmp / "pz/RainCatcher/preview.png"), (256, 256))

    def test_rejects_bad_and_duplicate_ids(self) -> None:
        self.assertEqual(run("new", "1bad")[0], 2)
        self.assertEqual(run("new", "GoodMod")[0], 0)
        self.assertEqual(run("new", "goodmod")[0], 2)

    def test_validate_catches_build41_layout(self) -> None:
        run("new", "OldStyle")
        mod_dir = self.mod_version_dir("OldStyle").parent
        shutil.move(str(mod_dir / "42" / "mod.info"), str(mod_dir / "mod.info"))
        code, out = run("validate")
        self.assertEqual(code, 1)
        self.assertIn("ignores a mod.info at the mod root", out)

    def test_validate_catches_txt_translations_and_bad_json(self) -> None:
        run("new", "Translated")
        en = self.mod_version_dir("Translated") / "media/lua/shared/Translate/EN"
        (en / "UI_EN.txt").write_text("UI_EN = {}", encoding="utf-8")
        (en / "UI.json").write_text("{ not json", encoding="utf-8")
        code, out = run("validate")
        self.assertEqual(code, 1)
        self.assertIn("only loads .json", out)
        self.assertIn("invalid JSON", out)

    def test_link_and_unlink(self) -> None:
        run("new", "Linked")
        zomboid = self.tmp / "Zomboid"
        zomboid.mkdir()
        code, out = run("link", "--zomboid-dir", str(zomboid))
        self.assertEqual(code, 0, out)
        link = zomboid / "Workshop" / "Linked"
        self.assertTrue((link / "Contents/mods/Linked/42/mod.info").is_file())
        self.assertEqual(run("link", "--zomboid-dir", str(zomboid))[0], 0)
        run("unlink", "--zomboid-dir", str(zomboid))
        self.assertFalse(link.exists())

    def test_link_refuses_to_replace_real_folder(self) -> None:
        run("new", "Clash")
        (self.tmp / "Zomboid" / "Workshop" / "Clash").mkdir(parents=True)
        code, out = run("link", "--zomboid-dir", str(self.tmp / "Zomboid"))
        self.assertEqual(code, 1)
        self.assertIn("real folder", out)


if __name__ == "__main__":
    unittest.main()
