"""Fixture-only tests for RCM disk receipt inspection.

No real SavedVariables are written, no Lua source from file is executed.
"""
from pathlib import Path
import contextlib
import io
import json
import os
import socket
import sys
import tempfile
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
from rcm_disk_receipt import DiskAuditError,inspect_saved_data,peer_file_metadata,run


SAVED = '''RiftChatModernSaved = {
  history = {
    { at = 1700, id = 1, kind = "system",
      source = "Game", text = "The tag saveCheckpoint = { sequence = 99 } is not code" },
    { at = 1701, id = 2, kind = "import",
      origin = "host_manual",channelKind = "guild",
      source = "RCMTest",text = "brace } and quote \\\\"escaped\\\\" data" }
  },
  nextId = 3,
  schemaVersion = 2,
  saveCheckpoint = {
    at = 1701.125,
    formatVersion = 1,
    historyCount = 2,
    lastHistoryId = 2,
    lastImportId = 2,
    nextId = 3,
    schemaVersion = 2,
    sequence = 1
  }
}
'''


class DiskCheckpointTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix="rcm-disk-audit-")
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.file=self.root/"RiftChatModern.lua"

    def write(self, contents=SAVED):
        self.file.write_text(contents,encoding="utf-8")
        return self.file

    def test_read_receipt_and_import_id_without_emitting_message_bodies(self):
        self.write()
        result=inspect_saved_data(self.file.read_text(encoding="utf-8"))
        self.assertEqual(result["schemaVersionOnDisk"],2)
        self.assertEqual(result["historyRowsOnDisk"],2)
        self.assertEqual(result["importRowsOnDisk"],1)
        self.assertEqual(result["lastImportedIdOnDisk"],2)
        self.assertTrue(result["checkpointOnDisk"])
        self.assertTrue(result["checkpointMetadataConsistent"])
        self.assertFalse(result["engineSaveEndProven"])
        self.assertFalse(result["messageBodiesEmitted"])
        self.assertEqual(result["checkpoint"]["at"],1701.125)
        self.assertNotIn("RCMTest",json.dumps(result))
        self.assertNotIn("saveCheckpoint = { sequence = 99 }",json.dumps(result))

    def test_old_schema_has_no_disk_receipt_and_no_fabricated_import(self):
        old='''RiftChatModernSaved = {
          history = {{ id = 1, kind = "system", text = "old" }},
          schemaVersion = 1, nextId=2
        }'''
        result=inspect_saved_data(old)
        self.assertEqual(result["schemaVersionOnDisk"],1)
        self.assertEqual(result["historyRowsOnDisk"],1)
        self.assertFalse(result["checkpointOnDisk"])
        self.assertFalse(result["checkpointMetadataConsistent"])
        self.assertIsNone(result["checkpoint"])
        self.write(old)
        out=io.StringIO()
        with contextlib.redirect_stdout(out):
            code=run(["--file",str(self.file),"--require-checkpoint"])
        self.assertEqual(code,2)
        self.assertFalse(json.loads(out.getvalue())["diskReceiptVerified"])

    def test_inconsistent_checkpoint_is_reported_not_accepted(self):
        result=inspect_saved_data(SAVED.replace("historyCount = 2,","historyCount = 3,"))
        self.assertTrue(result["checkpointOnDisk"])
        self.assertFalse(result["checkpointMetadataConsistent"])
        result=inspect_saved_data(SAVED.replace("lastImportId = 2,","lastImportId = 0,"))
        self.assertFalse(result["checkpointMetadataConsistent"])

    def test_duplicate_keys_in_checkpoint_are_rejected(self):
        bad=SAVED.replace("sequence = 1","sequence = 1, sequence = 2")
        with self.assertRaisesRegex(DiskAuditError,"duplicate_sequence"):
            inspect_saved_data(bad)

    def test_forged_checkpoint_inside_message_is_ignored(self):
        fake='''RiftChatModernSaved = {
            history = {{ id=1,kind="system",
              text="saveCheckpoint = {sequence=444,historyCount=1}" }},
            nextId=2, schemaVersion=2
        }'''
        result=inspect_saved_data(fake)
        self.assertFalse(result["checkpointOnDisk"])
        self.assertEqual(result["historyRowsOnDisk"],1)

    def test_wrong_host_and_filename_are_rejected_without_reading_private_text(self):
        self.write()
        output=io.StringIO()
        with contextlib.redirect_stdout(output):
            rc=run(["--file",str(self.file),"--expect-host","SOME-OTHER-PC"])
        self.assertEqual(rc,1)
        obj=json.loads(output.getvalue())
        self.assertEqual(obj["error"],"wrong_machine")
        self.assertFalse(obj["diskReceiptVerified"])
        invalid=self.root/"OtherAddon.lua"
        invalid.write_text(SAVED,encoding="utf-8")
        output=io.StringIO()
        with contextlib.redirect_stdout(output):
            self.assertEqual(run(["--file",str(invalid)]),1)
        self.assertEqual(json.loads(output.getvalue())["error"],
                         "incorrect_saved_filename")

    def test_peer_save_metadata_uses_file_times_not_chat_bodies(self):
        self.write()
        other=self.root/"UnrelatedAddon.lua"
        other.write_text("hidden chat text",encoding="utf-8")
        st=self.file.stat()
        os.utime(other,(st.st_mtime,st.st_mtime))
        m=peer_file_metadata(self.file)
        self.assertEqual(m["otherAddonSaveFiles"],1)
        self.assertEqual(m["othersWrittenWithinTwoSecondsOfRcm"],1)
        self.assertEqual(m["othersWrittenLaterByTenSecondsOrMore"],0)
        self.assertNotIn("hidden chat text",json.dumps(m))

    def test_cli_structured_verification_requires_real_disk_receipt(self):
        before=self.write().read_bytes()
        stream=io.StringIO()
        with contextlib.redirect_stdout(stream):
            rc=run(["--file",str(self.file),"--expect-host",socket.gethostname(),
                    "--require-checkpoint"])
        self.assertEqual(rc,0)
        result=json.loads(stream.getvalue())
        self.assertTrue(result["diskReceiptVerified"])
        self.assertEqual(result["checkpoint"]["lastImportId"],2)
        self.assertFalse(result["savedVariablesModified"])
        self.assertEqual(self.file.read_bytes(),before)

    def test_invalid_or_unbalanced_lua_does_not_execute(self):
        with self.assertRaisesRegex(DiskAuditError,"missing_or_multiple_rcm_root"):
            inspect_saved_data("while true do end")
        with self.assertRaisesRegex(DiskAuditError,"unbalanced_saved_table"):
            inspect_saved_data("RiftChatModernSaved = { history = {{ ")
        with self.assertRaisesRegex(DiskAuditError,"unterminated_lua_string"):
            inspect_saved_data('RiftChatModernSaved = {x="unclosed}')

    def test_invalid_utf8_is_refused_without_partial_metadata(self):
        self.file.write_bytes(b'RiftChatModernSaved = {schemaVersion=2, history={}, text="\xff"}')
        output=io.StringIO()
        with contextlib.redirect_stdout(output):
            rc=run(["--file",str(self.file)])
        self.assertEqual(rc,1)
        details=json.loads(output.getvalue())
        self.assertFalse(details["diskReceiptVerified"])
        self.assertFalse(details["savedVariablesModified"])
        self.assertNotIn("text=",json.dumps(details))

if __name__=="__main__":
    unittest.main()
