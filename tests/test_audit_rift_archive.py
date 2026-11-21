"""Hermetic checks for static RIFT archive triage; no game files or network."""
import contextlib
import io
from pathlib import Path
import sys
import tempfile
import unittest
import zipfile

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"tools"))
from audit_rift_addon_archive import AuditError, inspect_archive, main

TOC = '''Identifier = "Example"
Name = "Example Addon"
Version = "1.0.0"
Environment = "4.3"
RunOnStartup = { "Main.lua" }
'''

class ArchiveAuditTests(unittest.TestCase):
    def setUp(self):
        self.work=tempfile.TemporaryDirectory(prefix="rcm-addon-audit-")
        self.addCleanup(self.work.cleanup)
        self.zip=Path(self.work.name)/"candidate.zip"

    def put(self, files):
        with zipfile.ZipFile(self.zip,"w",compression=zipfile.ZIP_DEFLATED) as z:
            for key,body in files.items():
                z.writestr(key,body)
        return self.zip

    def test_rift_api_candidate_no_execution_and_path_preserved(self):
        archive=self.put({
            "Good/RiftAddon.toc":TOC,
            "Good/Main.lua":'local addon=...; Command.Event.Attach(Event.Chat.Npc,function() end,"npc")\n'
        })
        digest_before=archive.read_bytes()
        result=inspect_archive(archive)
        self.assertEqual(result["verdict"],"rift_api_candidate_needs_live_test")
        self.assertEqual(result["identifier"],"Example")
        self.assertGreater(result["riftApiFileHits"],0)
        self.assertEqual(result["wowApiFileAndXmlHits"],0)
        self.assertIs(result["lua51SyntaxOnly"][0]["lua51SyntaxOnly"],True)
        self.assertFalse(result["addonCodeExecuted"])
        self.assertFalse(result["nativePlayerChatReceptionVerified"])
        self.assertEqual(digest_before,archive.read_bytes())

    def test_actual_rcm_addon_is_positive_control_for_rift_api_not_live_capture(self):
        live_source=ROOT/"addon"/"RiftChatModern"
        with zipfile.ZipFile(self.zip,"w",compression=zipfile.ZIP_DEFLATED) as z:
            for member in live_source.rglob("*"):
                if member.is_file():
                    z.write(member,arcname="RiftChatModern/"+member.relative_to(live_source).as_posix())
        r=inspect_archive(self.zip)
        self.assertEqual(r["identifier"],"RiftChatModern")
        self.assertEqual(r["version"],"0.2.22")
        self.assertEqual(r["missingStartupFiles"],[])
        self.assertEqual(r["verdict"],"rift_api_candidate_needs_live_test")
        self.assertTrue(all(x["lua51SyntaxOnly"] for x in r["lua51SyntaxOnly"]))
        self.assertFalse(r["nativePlayerChatReceptionVerified"])

    def test_wow_code_is_not_mistaken_for_rift_native_chat(self):
        self.put({
            "Chat/RiftAddon.toc":TOC,
            "Chat/Main.lua":'''
local CreateFrame=CreateFrame
local f=CreateFrame("Frame","example")
f:RegisterEvent("CHAT_MSG_WHISPER")
DEFAULT_CHAT_FRAME:AddMessage("hello")
'''
        })
        r=inspect_archive(self.zip)
        self.assertEqual(r["verdict"],"wow_api_dominant_no_rift_runtime_evidence")
        self.assertEqual(r["riftApiFileHits"],0)
        self.assertGreater(r["wowApiFileAndXmlHits"],2)

    def test_loader_absent_file_fails_even_with_rift_toc(self):
        self.put({"Chat/RiftAddon.toc":TOC,"Chat/Other.lua":"return 1\n"})
        x=inspect_archive(self.zip)
        self.assertEqual(x["verdict"],"manifest_or_compile_blocker")
        self.assertEqual(x["missingStartupFiles"],["Main.lua"])

    def test_case_only_mismatch_is_visible_not_a_missing_file_on_windows(self):
        self.put({"Chat/RiftAddon.toc":TOC,
                  "Chat/main.lua":"Command.Slash.Register('test')\n"})
        x=inspect_archive(self.zip)
        self.assertEqual(x["missingStartupFiles"],[])
        self.assertEqual(x["caseMismatchWindowsMayResolve"],["Main.lua"])
        self.assertEqual(x["verdict"],"rift_api_candidate_needs_live_test")

    def test_invalid_lua_source_is_detected_without_executing_it(self):
        self.put({"Chat/RiftAddon.toc":TOC,"Chat/Main.lua":"function broken( end\n"})
        result=inspect_archive(self.zip)
        self.assertEqual(result["verdict"],"manifest_or_compile_blocker")
        self.assertIs(result["lua51SyntaxOnly"][0]["lua51SyntaxOnly"],False)

    def test_traversal_and_ambiguous_duplicates_are_rejected(self):
        self.put({"Chat/RiftAddon.toc":TOC,"../secret.lua":"oops"})
        with self.assertRaisesRegex(AuditError,"unsafe_path"):
            inspect_archive(self.zip)
        self.put({"Chat/RiftAddon.toc":TOC,"C:/absolute.lua":"oops"})
        with self.assertRaisesRegex(AuditError,"unsafe_path"):
            inspect_archive(self.zip)
        self.put({"Chat/RiftAddon.toc":TOC,"Chat/Main.lua":"x=1",
                  "Chat/main.lua":"x=2"})
        with self.assertRaisesRegex(AuditError,"ambiguous_case_insensitive_names"):
            inspect_archive(self.zip)

    def test_no_toc_and_invalid_zip_rejected(self):
        self.put({"Chat/Main.lua":"x=1"})
        with self.assertRaisesRegex(AuditError,"expected_one_riftaddon_toc"):
            inspect_archive(self.zip)
        self.zip.write_bytes(b"no zip bytes")
        with self.assertRaisesRegex(AuditError,"invalid_zip"):
            inspect_archive(self.zip)

    def test_cli_emits_structured_read_only_evidence(self):
        self.put({"Chat/RiftAddon.toc":TOC,
                  "Chat/Main.lua":"Command.Slash.Register('test')\n"})
        buffer=io.StringIO()
        with contextlib.redirect_stdout(buffer):
            code=main([str(self.zip)])
        self.assertEqual(code,0)
        self.assertIn('"gameFilesTouched": false',buffer.getvalue())
        self.assertIn('"nativePlayerChatReceptionVerified": false',buffer.getvalue())

if __name__=="__main__":
    unittest.main()
