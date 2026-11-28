"""Test packaging actual addon source; no installed game or character data."""
import hashlib
import io
from pathlib import Path
import shutil
import stat
import sys
import tempfile
import unittest
from unittest import mock
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import package_rcm as p


class AddonPackageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.package = p.build_package()

    def setUp(self):
        self.temp = self.enterContext(tempfile.TemporaryDirectory(prefix="rcm-package-test-"))
        self.root = Path(self.temp)

    def source_copy(self):
        source = self.root / p.ADDON
        return Path(shutil.copytree(p.SOURCE, source))

    def test_exact_runtime_inventory_and_source_bytes(self):
        package = self.package
        with zipfile.ZipFile(io.BytesIO(package.data)) as archive:
            expected = sorted(f"{p.ADDON}/{folder + '/' if folder else ''}{name}"
                              for folder, names in p.LAYOUT.items() for name in names)
            self.assertEqual(archive.namelist(), expected)
            self.assertEqual(len(expected), package.files)
            self.assertEqual(package.files, 23)
            for info in archive.infolist():
                relative = info.filename.removeprefix(p.ADDON + "/")
                self.assertEqual(archive.read(info), (p.SOURCE / relative).read_bytes())
                self.assertEqual(info.date_time, p.ZIP_TIME)
                self.assertEqual(info.compress_type, zipfile.ZIP_STORED)
                self.assertEqual(stat.S_IFMT(info.external_attr >> 16), stat.S_IFREG)
        self.assertEqual(package.sha256, hashlib.sha256(package.data).hexdigest())

    def test_reproducible_despite_different_source_timestamps(self):
        source = self.source_copy()
        import os
        for file in source.rglob("*"):
            if file.is_file():
                os.utime(file, (1000000000, 1000000000))
        self.assertEqual(p.build_package(source), self.package)

    def test_missing_required_asset_refuses(self):
        source = self.source_copy()
        (source / "textures" / p.TEXTURES[0]).unlink()
        with self.assertRaisesRegex(ValueError, "package_layout_mismatch"):
            p.build_package(source)

    def test_extra_private_file_refuses_instead_of_bundling(self):
        source = self.source_copy()
        (source / "fonts" / "private.json").write_bytes(b"private fixture")
        with self.assertRaisesRegex(ValueError, "package_layout_mismatch"):
            p.build_package(source)

    def test_invalid_manifest_version_refuses(self):
        source = self.source_copy()
        toc = source / "RiftAddon.toc"
        data = toc.read_text(encoding="utf-8")
        toc.write_text(data.replace(f'Version = "{self.package.version}"',
                                    'Version = "999.0.0"'), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "Core version differs"):
            p.build_package(source)

    def test_invalid_or_unavailable_lua_compile_refuses(self):
        source = self.source_copy()
        (source / "NativeChatProbe.lua").write_bytes(b"function ???")
        with self.assertRaisesRegex(ValueError, "lua51_compile_unavailable_or_invalid"):
            p.build_package(source)
        with mock.patch.object(p, "compile_lua", return_value=(None, "unavailable")):
            with self.assertRaisesRegex(ValueError, "lua51_compile_unavailable_or_invalid"):
                p.build_package()

    def test_nonregular_or_reparse_source_refused(self):
        source = self.source_copy()
        file = source / "fonts" / p.FONTS[0]
        real_lstat = Path.lstat
        def lstat(path, *args, **kwargs):
            if path == file:
                return mock.Mock(st_mode=stat.S_IFREG, st_file_attributes=p.REPARSE_POINT)
            return real_lstat(path, *args, **kwargs)
        with mock.patch.object(Path, "lstat", lstat):
            with self.assertRaisesRegex(ValueError, "non_plain_package_path"):
                p.build_package(source)
        file.unlink()
        file.mkdir()
        with self.assertRaisesRegex(ValueError, "non_plain_package_path"):
            p.build_package(source)

    def test_publish_is_idempotent_and_check_is_read_only(self):
        dist = self.root / "dist"
        report = p.publish_package(self.package, dist)
        archive = dist / self.package.filename
        checksum = dist / (self.package.filename + ".sha256")
        times = (archive.stat().st_mtime_ns, checksum.stat().st_mtime_ns)
        self.assertEqual(archive.read_bytes(), self.package.data)
        self.assertEqual(checksum.read_bytes(), self.package.checksum)
        self.assertEqual(p.publish_package(self.package, dist), report)
        self.assertEqual(p.publish_package(self.package, dist, check=True), report)
        self.assertEqual(times, (archive.stat().st_mtime_ns, checksum.stat().st_mtime_ns))
        self.assertFalse(report["physicalRiftAcceptanceVerified"])
        self.assertFalse(report["gameFilesTouched"])
        self.assertEqual(set(x.name for x in dist.iterdir()),
                         {archive.name, checksum.name})

    def test_conflicting_output_never_overwritten_or_partially_published(self):
        dist = self.root / "dist"
        dist.mkdir()
        checksum = dist / (self.package.filename + ".sha256")
        checksum.write_bytes(b"bad")
        with self.assertRaises(ValueError):
            p.publish_package(self.package, dist)
        self.assertEqual(checksum.read_bytes(), b"bad")
        self.assertFalse((dist / self.package.filename).exists())
        checksum.unlink()
        archive = dist / self.package.filename
        archive.write_bytes(b"old")
        with self.assertRaises(ValueError):
            p.publish_package(self.package, dist)
        self.assertEqual(archive.read_bytes(), b"old")
        self.assertFalse(checksum.exists())

    def test_missing_checksum_check_refuses_and_build_repairs_it(self):
        dist = self.root / "dist"
        dist.mkdir()
        archive = dist / self.package.filename
        archive.write_bytes(self.package.data)
        with self.assertRaisesRegex(ValueError, "package_output_missing"):
            p.publish_package(self.package, dist, check=True)
        checksum = dist / (self.package.filename + ".sha256")
        self.assertFalse(checksum.exists())
        p.publish_package(self.package, dist)
        self.assertEqual(checksum.read_bytes(), self.package.checksum)


if __name__ == "__main__":
    unittest.main()
