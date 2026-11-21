"""Guarded RCM installer regression tests using hermetic temporary addon folders.

Never writes the physical installed RIFT addon or character SavedVariables.
"""
import contextlib
import io
import json
from pathlib import Path
import shutil
import socket
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import deploy_rcm


class DeploymentTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="rcm-deploy-test-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / "project" / "addon" / "RiftChatModern"
        self.target = self.root / "installed" / "RiftChatModern"
        self.source.parent.mkdir(parents=True)
        self.target.parent.mkdir(parents=True)
        shutil.copytree(ROOT / "addon" / "RiftChatModern", self.source)
        shutil.copytree(self.source, self.target)

    def test_valid_manifest_and_hash_matched_dry_run(self):
        data = deploy_rcm.manifest(self.source)
        self.assertEqual(data["identifier"], "RiftChatModern")
        self.assertIn("HostIngress.lua", data["modules"])
        self.assertLess(data["modules"].index("HostIngress.lua"),
                        data["modules"].index("Main.lua"))
        plan = deploy_rcm.preflight(self.source, self.target)
        self.assertEqual(plan["changed"], [])
        self.assertEqual(len(plan["files"]), 10)

    def test_copy_creates_verified_backups_and_is_idempotent(self):
        target_main = self.target / "Main.lua"
        old = target_main.read_bytes() + b"\n-- old installed fixture\n"
        target_main.write_bytes(old)
        extra = self.target / "KeepExtraSourceFile.txt"
        extra.write_text("must remain", encoding="utf-8")
        plan = deploy_rcm.preflight(self.source, self.target)
        self.assertEqual(plan["changed"], [Path("Main.lua")])
        saved = deploy_rcm.apply_copy(self.source, self.target, plan,
                                     self.root / "project")
        self.assertEqual(saved["changed"], ["Main.lua"])
        self.assertEqual(target_main.read_bytes(), (self.source / "Main.lua").read_bytes())
        backup = Path(saved["backups"]) / "Main.lua"
        self.assertEqual(backup.read_bytes(), old)
        self.assertEqual(extra.read_text(encoding="utf-8"), "must remain")
        self.assertEqual(deploy_rcm.preflight(self.source,self.target)["changed"], [])
        again=deploy_rcm.apply_copy(self.source,self.target,
            deploy_rcm.preflight(self.source,self.target),self.root/"project")
        self.assertEqual(again["changed"], [])
        self.assertIsNone(again["backups"])

    def test_missing_new_module_is_added_without_removing_other_files(self):
        (self.target / "HostIngress.lua").unlink()
        extra = self.target / "unrelated-in-folder.txt"
        extra.write_text("keep", encoding="utf-8")
        plan = deploy_rcm.preflight(self.source, self.target)
        self.assertEqual(plan["changed"], [Path("HostIngress.lua")])
        result=deploy_rcm.apply_copy(self.source,self.target,plan,self.root/"project")
        self.assertIn("HostIngress.lua", result["changed"])
        self.assertEqual(self.target.joinpath("HostIngress.lua").read_bytes(),
                         self.source.joinpath("HostIngress.lua").read_bytes())
        self.assertEqual(extra.read_text(encoding="utf-8"),"keep")

    def test_refuse_invalid_target_identity_or_missing_target(self):
        toc=self.target/"RiftAddon.toc"
        toc.write_text(toc.read_text(encoding="utf-8").replace(
            'Identifier = "RiftChatModern"', 'Identifier = "DifferentAddon"'),
            encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "not an established RCM"):
            deploy_rcm.preflight(self.source,self.target)
        with self.assertRaises(ValueError):
            deploy_rcm.preflight(self.source,self.root/"nonexistent")

    def test_source_manifest_must_have_email_and_complete_startup_order(self):
        toc=self.source/"RiftAddon.toc"
        original=toc.read_text(encoding="utf-8")
        toc.write_text(original.replace('Email = "placeholder@example.com"',
                                        "Email = nil"),encoding="utf-8")
        with self.assertRaisesRegex(ValueError,"missing Email"):
            deploy_rcm.manifest(self.source)
        toc.write_text(original.replace('"HostIngress.lua", "Main.lua"',
                                        '"Main.lua", "HostIngress.lua"'),
                       encoding="utf-8")
        with self.assertRaisesRegex(ValueError,"list/order"):
            deploy_rcm.manifest(self.source)

    def test_machine_verification_required_for_apply(self):
        stream=io.StringIO()
        with contextlib.redirect_stdout(stream):
            result=deploy_rcm.main(["--apply","--expect-host","NONMATCHING-HOST",
                                    "--target",str(self.target)])
        self.assertEqual(result,1)
        response=json.loads(stream.getvalue())
        self.assertFalse(response["success"])
        self.assertEqual(deploy_rcm.preflight(self.source,self.target)["changed"],[])

    def test_explicit_target_dry_run_does_not_write(self):
        old=(self.target/"Main.lua").read_bytes() + b"\n-- changed here\n"
        (self.target/"Main.lua").write_bytes(old)
        stream=io.StringIO()
        with contextlib.redirect_stdout(stream):
            rc=deploy_rcm.main(["--target",str(self.target)])
        self.assertEqual(rc,0)
        response=json.loads(stream.getvalue())
        self.assertEqual(response["mode"],"dry_run")
        self.assertEqual(response["machine"],socket.gethostname())
        self.assertIn("Main.lua",response["changedFiles"])
        self.assertFalse(response["savedVariablesTouched"])
        self.assertEqual((self.target/"Main.lua").read_bytes(),old)

    def test_apply_rollback_if_second_file_replace_fails(self):
        for name in ("Main.lua","Core.lua"):
            p=self.target/name
            p.write_bytes(p.read_bytes()+b"\n-- old installed fixture\n")
        before={n:(self.target/n).read_bytes() for n in ("Main.lua","Core.lua")}
        plan=deploy_rcm.preflight(self.source,self.target)
        self.assertEqual(len(plan["changed"]),2)
        real_replace=deploy_rcm.os.replace
        calls=[]
        def fails_second(src,dst):
            calls.append(dst)
            if len(calls)==2:raise OSError("test injection: second replace failed")
            return real_replace(src,dst)
        with mock.patch.object(deploy_rcm.os,"replace",side_effect=fails_second):
            with self.assertRaisesRegex(OSError,"second replace"):
                deploy_rcm.apply_copy(self.source,self.target,plan,self.root/"project")
        for n,data in before.items():
            self.assertEqual((self.target/n).read_bytes(),data)

    def test_discover_existing_one_drive_only(self):
        home=self.root/"home"
        root=home/"OneDrive"/"Documents"/"RIFT"/"Interface"/"AddOns"/"RiftChatModern"
        root.mkdir(parents=True)
        (root/"RiftAddon.toc").write_text("example",encoding="utf-8")
        paths=deploy_rcm.discover_targets(home,{})
        self.assertEqual(paths,[root])


    def test_apply_hot_deploys_live_game_and_requires_reloadui(self):
        target_main=self.target/"Main.lua"
        before=target_main.read_bytes()+b"\n-- installed older version\n"
        target_main.write_bytes(before)
        stream=io.StringIO()
        with mock.patch.object(deploy_rcm,"running_game_pids",create=True,return_value=[23164]):
            with contextlib.redirect_stdout(stream):
                rc=deploy_rcm.main(["--apply","--expect-host",socket.gethostname(),
                                    "--target",str(self.target)])
        self.assertEqual(rc,0)
        self.assertEqual(target_main.read_bytes(),(self.source/"Main.lua").read_bytes())
        response=json.loads(stream.getvalue())
        self.assertEqual(response["gameProcessCheck"],"running")
        self.assertEqual(response["runningGamePids"],[23164])
        self.assertTrue(response["reloadUiRequired"])
        self.assertEqual(response["reloadUiCommand"],"/reloadui")
        self.assertTrue(response["hashVerified"])
        self.assertFalse(response["savedVariablesTouched"])
        self.assertFalse(response["gameInputSent"])
        self.assertFalse(response["physicalGameLoaded"])

    def test_running_game_with_identical_files_needs_no_reload(self):
        stream=io.StringIO()
        with mock.patch.object(deploy_rcm,"running_game_pids",return_value=[34596]):
            with contextlib.redirect_stdout(stream):
                rc=deploy_rcm.main(["--apply","--expect-host",socket.gethostname(),
                                    "--target",str(self.target)])
        self.assertEqual(rc,0)
        result=json.loads(stream.getvalue())
        self.assertEqual(result["gameProcessCheck"],"running")
        self.assertEqual(result["runningGamePids"],[34596])
        self.assertEqual(result["changed"],[])
        self.assertFalse(result["reloadUiRequired"])
        self.assertIsNone(result["reloadUiCommand"])
        self.assertTrue(result["hashVerified"])
        self.assertFalse(result["savedVariablesTouched"])
        self.assertFalse(result["runtimeReloadVerified"])

    def test_apply_fails_closed_when_process_query_unavailable(self):
        target_main=self.target/"Main.lua"
        before=target_main.read_bytes()+b"\n-- installed older version\n"
        target_main.write_bytes(before)
        stream=io.StringIO()
        with mock.patch.object(deploy_rcm,"running_game_pids",create=True,
                               side_effect=RuntimeError("game_process_query_failed")):
            with contextlib.redirect_stdout(stream):
                rc=deploy_rcm.main(["--apply","--expect-host",socket.gethostname(),
                                    "--target",str(self.target)])
        self.assertEqual(rc,1)
        self.assertEqual(target_main.read_bytes(),before)
        response=json.loads(stream.getvalue())
        self.assertFalse(response["success"])
        self.assertIn("game_process_query_failed",response["error"])

    def test_apply_after_verified_no_game_preserves_hash_receipts(self):
        target_main=self.target/"Main.lua"
        target_main.write_bytes(target_main.read_bytes()+b"\n-- older install\n")
        stream=io.StringIO()
        with mock.patch.object(deploy_rcm,"running_game_pids",create=True,return_value=[]):
            with contextlib.redirect_stdout(stream):
                rc=deploy_rcm.main(["--apply","--expect-host",socket.gethostname(),
                                    "--target",str(self.target)])
        self.assertEqual(rc,0)
        response=json.loads(stream.getvalue())
        self.assertEqual(response["gameProcessCheck"],"closed")
        self.assertFalse(response["reloadUiRequired"])
        self.assertIsNone(response["reloadUiCommand"])
        self.assertTrue(response["hashVerified"])
        self.assertEqual(response["changed"],["Main.lua"])
        self.assertEqual(target_main.read_bytes(),(self.source/"Main.lua").read_bytes())

    def test_unparseable_game_row_blocks_apply_but_error_handler_alone_does_not(self):
        fake=mock.Mock(returncode=0,stdout='"rift_x64.exe","INVALID_PID","Console"\n')
        with mock.patch.object(deploy_rcm.os,"name","nt"):
            with mock.patch.object(deploy_rcm.subprocess,"run",return_value=fake):
                with self.assertRaisesRegex(RuntimeError,"game_process_query_unparseable"):
                    deploy_rcm.running_game_pids()
        fake.stdout='"rifterrorhandler_x64.exe","222","Console"\n'
        with mock.patch.object(deploy_rcm.os,"name","nt"):
            with mock.patch.object(deploy_rcm.subprocess,"run",return_value=fake):
                self.assertEqual(deploy_rcm.running_game_pids(),[])

if __name__=="__main__":
    unittest.main()
