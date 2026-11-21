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
from unittest import mock

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

    def test_ui_geometry_receipt_and_exact_cli_match(self):
        saved=SAVED.replace("  nextId = 3,",
            "  ui = { x = 1547, y = 364, w = 952, h = 775 },\n  nextId = 3,")
        parsed=inspect_saved_data(saved)
        self.assertTrue(parsed["uiGeometryComplete"])
        self.assertEqual(parsed["uiGeometryOnDisk"],
                         {"x":1547,"y":364,"w":952,"h":775})
        self.assertNotIn("RCMTest", json.dumps(parsed))
        self.write(saved)
        for expectation,exitcode,matched in [
            ("1547,364,952,775",0,True),
            ("1547,364,760,618",2,False),
        ]:
            with self.subTest(expectation=expectation):
                output=io.StringIO()
                with contextlib.redirect_stdout(output):
                    code=run(["--file",str(self.file),
                              "--require-ui-geometry",expectation])
                self.assertEqual(code,exitcode)
                result=json.loads(output.getvalue())
                self.assertEqual(result["requiredUiGeometryMatched"],matched)
                self.assertFalse(result["savedVariablesModified"])

    def test_ui_geometry_ignores_forged_text_and_requires_complete_table(self):
        text=SAVED.replace('text = "The tag saveCheckpoint = { sequence = 99 } is not code"',
            'text = "ui = { x=999, y=999, w=999, h=999 } not code"')
        result=inspect_saved_data(text)
        self.assertFalse(result["uiGeometryComplete"])
        self.assertIsNone(result["uiGeometryOnDisk"])
        self.assertNotIn("999", json.dumps(result))
        half=text.replace("  nextId = 3,", "  ui = { x=10, y=11 },\n  nextId = 3,")
        partial=inspect_saved_data(half)
        self.assertFalse(partial["uiGeometryComplete"])
        self.assertIsNone(partial["uiGeometryOnDisk"])
        duplicate=half.replace("  nextId = 3,",
                               "  ui = { x=20, y=21, w=680, h=480 },\n  nextId = 3,")
        with self.assertRaisesRegex(DiskAuditError,"ambiguous_ui_tables"):
            inspect_saved_data(duplicate)

    def test_geometry_requirement_rejects_bad_cli_input(self):
        self.write()
        for argument in ("1,2,3", "1,2,3,notanumber", "1,2,0,480",
                         "1,2,99999,700", "1,-1,760,618"):
            with self.subTest(argument=argument):
                output=io.StringIO()
                with contextlib.redirect_stdout(output):
                    code=run(["--file",str(self.file),
                              "--require-ui-geometry",argument])
                self.assertEqual(code,1)
                self.assertFalse(json.loads(output.getvalue())["savedVariablesModified"])

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

    def test_realistic_kind_histogram_does_not_expose_message_text(self):
        details=inspect_saved_data(SAVED)
        self.assertEqual(details["historyKindsOnDisk"],{"system":1,"import":1})
        self.assertNotIn("RCMTest",json.dumps(details))
        self.assertNotIn("brace }",json.dumps(details))

    def test_duplicate_history_ids_never_count_as_verified_disk_save(self):
        forged=SAVED.replace('at = 1701, id = 2, kind = "import"',
                             'at = 1701, id = 1, kind = "import"')
        forged=forged.replace("lastHistoryId = 2,","lastHistoryId = 1,")
        forged=forged.replace("lastImportId = 2,","lastImportId = 1,")
        with self.assertRaisesRegex(DiskAuditError,"duplicate_history_id"):
            inspect_saved_data(forged)

    def test_out_of_order_history_ids_are_refused_even_if_tail_receipt_matches(self):
        forged=SAVED.replace('at = 1700, id = 1, kind = "system"',
                             'at = 1700, id = 2, kind = "system"')
        forged=forged.replace('at = 1701, id = 2, kind = "import"',
                              'at = 1701, id = 1, kind = "import"')
        forged=forged.replace("lastHistoryId = 2,","lastHistoryId = 1,")
        forged=forged.replace("lastImportId = 2,","lastImportId = 1,")
        with self.assertRaisesRegex(DiskAuditError,"non_monotonic_history_id"):
            inspect_saved_data(forged)

    def test_checkpoint_next_id_cannot_disagree_with_root_saved_sequence(self):
        forged=SAVED.replace("  nextId = 3,\n  schemaVersion = 2,",
                             "  nextId = 4,\n  schemaVersion = 2,")
        details=inspect_saved_data(forged)
        self.assertTrue(details["checkpointOnDisk"])
        self.assertFalse(details["checkpointMetadataConsistent"])
        self.write(forged)
        out=io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(run(["--file",str(self.file),"--require-checkpoint"]),2)
        self.assertFalse(json.loads(out.getvalue())["diskReceiptVerified"])

    def test_required_import_id_reports_exact_saved_row_without_text(self):
        present=inspect_saved_data(SAVED,required_import_id=2)
        missing=inspect_saved_data(SAVED,required_import_id=99)
        self.assertEqual(present["requiredImportId"],2)
        self.assertTrue(present["requiredImportIdPresent"])
        self.assertFalse(missing["requiredImportIdPresent"])
        self.assertNotIn("RCMTest",json.dumps(present))
        self.write()
        stdout=io.StringIO()
        with contextlib.redirect_stdout(stdout):
            self.assertEqual(run(["--file",str(self.file),"--require-import-id","2"]),0)
        success=json.loads(stdout.getvalue())
        self.assertTrue(success["requiredImportIdPresent"])
        self.assertTrue(success["diskReceiptVerified"])
        stdout=io.StringIO()
        with contextlib.redirect_stdout(stdout):
            self.assertEqual(run(["--file",str(self.file),"--require-import-id","99"]),2)
        self.assertFalse(json.loads(stdout.getvalue())["requiredImportIdPresent"])
        self.assertNotIn("RCMTest",stdout.getvalue())

    def test_import_id_requires_valid_checkpoint_and_positive_id(self):
        self.write(SAVED.replace("historyCount = 2,","historyCount = 3,"))
        out=io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(run(["--file",str(self.file),"--require-import-id","2"]),2)
        self.assertTrue(json.loads(out.getvalue())["requiredImportIdPresent"])
        self.assertFalse(json.loads(out.getvalue())["diskReceiptVerified"])
        out=io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(run(["--file",str(self.file),"--require-import-id","0"]),1)
        self.assertFalse(json.loads(out.getvalue())["diskReceiptVerified"])

    def test_import_token_and_id_require_the_same_retained_row(self):
        tagged = SAVED.replace('channelKind = "guild",',
                               'channelKind = "guild",importToken = "B3A0705FD6AA",')
        good = inspect_saved_data(tagged, required_import_id=2,
                                  required_import_token="B3A0705FD6AA")
        self.assertEqual(good["tokenizedImportRowsOnDisk"], 1)
        self.assertTrue(good["requiredImportIdPresent"])
        self.assertTrue(good["requiredImportTokenPresent"])
        self.assertTrue(good["requiredImportIdentityMatched"])
        self.assertNotIn("RCMTest", json.dumps(good))
        self.write(tagged)
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = run(["--file", str(self.file), "--require-import-id", "2",
                        "--require-import-token", "B3A0705FD6AA"])
        self.assertEqual(code, 0)
        self.assertTrue(json.loads(out.getvalue())["requiredImportIdentityMatched"])
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = run(["--file", str(self.file), "--require-import-token", "ABABABABABAB"])
        self.assertEqual(code, 2)
        self.assertFalse(json.loads(out.getvalue())["requiredImportTokenPresent"])
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = run(["--file", str(self.file), "--require-import-token", "lowercase123"])
        self.assertEqual(code, 1)
        self.assertFalse(json.loads(out.getvalue())["diskReceiptVerified"])

    def test_token_and_id_cannot_be_satisfied_by_different_rows(self):
        source = '''RiftChatModernSaved = {
          schemaVersion=2,nextId=3,
          history={
            {id=1,kind="import",origin="host_manual",importToken="B3A0705FD6AA"},
            {id=2,kind="import",origin="host_manual",importToken="A1A1A1A1A1A1"}
          },
          saveCheckpoint={formatVersion=1,schemaVersion=2,sequence=1,
            historyCount=2,nextId=3,lastHistoryId=2,lastImportId=2,at=1700}
        }'''
        combined = inspect_saved_data(source, required_import_id=1,
                                      required_import_token="A1A1A1A1A1A1")
        self.assertTrue(combined["requiredImportIdPresent"])
        self.assertTrue(combined["requiredImportTokenPresent"])
        self.assertFalse(combined["requiredImportIdentityMatched"])
        self.write(source)
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            rc = run(["--file", str(self.file), "--require-import-id", "1",
                      "--require-import-token", "A1A1A1A1A1A1"])
        self.assertEqual(rc, 2)

    def test_duplicate_stored_import_token_is_rejected(self):
        source='''RiftChatModernSaved={schemaVersion=2,nextId=3,history={
          {id=1,kind="import",origin="host_manual",importToken="B3A0705FD6AA"},
          {id=2,kind="import",origin="host_manual",importToken="B3A0705FD6AA"}}}'''
        with self.assertRaisesRegex(DiskAuditError, "duplicate_import_token"):
            inspect_saved_data(source)

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

    def test_disk_file_mutation_during_read_invalidates_receipt(self):
        # Fixture-only interference: ensure a mid-audit save cannot inherit
        # old bytes and a newer timestamp as one 'verified' snapshot.
        self.write()
        original=Path.read_bytes
        def changed_during_read(path):
            data=original(path)
            if path==self.file:
                path.write_bytes(data+b"\n-- fixture changed during audit\n")
            return data
        out=io.StringIO()
        with mock.patch.object(Path,"read_bytes",autospec=True,side_effect=changed_during_read):
            with contextlib.redirect_stdout(out):
                rc=run(["--file",str(self.file),"--require-checkpoint"])
        self.assertEqual(rc,1)
        result=json.loads(out.getvalue())
        self.assertFalse(result["diskReceiptVerified"])
        self.assertIn("saved_file_changed_during_audit",result["error"])

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

    def test_lua_long_comment_cannot_forge_checkpoint(self):
        forged='''RiftChatModernSaved = {
          history = {{ id=1,kind="system",text="ordinary" }},
          --[=[
          saveCheckpoint = {
            formatVersion=1,schemaVersion=2,sequence=900,
            historyCount=1,lastHistoryId=1,lastImportId=0,nextId=2,at=1700
          }
          ]=]
          nextId=2, schemaVersion=2
        }'''
        result=inspect_saved_data(forged)
        self.assertEqual(result["historyRowsOnDisk"],1)
        self.assertFalse(result["checkpointOnDisk"])
        self.assertFalse(result["checkpointMetadataConsistent"])

    def test_lua_long_string_cannot_forge_checkpoint_or_history_rows(self):
        forged='''RiftChatModernSaved = {
          history = {{ id=1,kind="system",text=[==[
              } saveCheckpoint = {sequence=999,formatVersion=1}
              { id=99,kind="import" }
              -- pretend comment
          ]==] }},
          nextId=2, schemaVersion=2
        }'''
        result=inspect_saved_data(forged)
        self.assertEqual(result["historyRowsOnDisk"],1)
        self.assertEqual(result["importRowsOnDisk"],0)
        self.assertFalse(result["checkpointOnDisk"])

    def test_long_bracket_false_positive_before_genuine_checkpoint(self):
        # A forged receipt in a Lua multiline comment must not hide a real one.
        injected=SAVED.replace(
            "  saveCheckpoint = {",
            '''  --[==[
          saveCheckpoint={sequence=777,historyCount=999}
          ]==]
          saveCheckpoint = {''',
            1)
        result=inspect_saved_data(injected)
        self.assertTrue(result["checkpointOnDisk"])
        self.assertTrue(result["checkpointMetadataConsistent"])
        self.assertEqual(result["checkpoint"]["sequence"],1)

    def test_unterminated_multiline_lua_literals_rejected(self):
        broken_comment='''RiftChatModernSaved={
          history={}, --[=[ forged checkpoint = { '''
        with self.assertRaisesRegex(DiskAuditError,"unterminated_lua_long_comment"):
            inspect_saved_data(broken_comment)
        broken_string='''RiftChatModernSaved={
          history={{id=1,kind="system",text=[==[ forgot closing '''
        with self.assertRaisesRegex(DiskAuditError,"unterminated_lua_long_string"):
            inspect_saved_data(broken_string)

if __name__=="__main__":
    unittest.main()
