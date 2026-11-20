"""RCM read-only Windows session/log preflight; all tests use local fixtures."""
import contextlib, csv, io, json, os
from pathlib import Path
import sys, tempfile, unittest
from unittest import mock

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"tools"))
import rcm_session_preflight as p

class SessionPreflightTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix="rcm-prefight-")
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.docs=self.root/"OneDrive"/"Documents"
        (self.docs/"RIFT").mkdir(parents=True)
        self.home=self.root

    def test_tasklist_filters_only_exact_rift_processes_and_csv(self):
        stdout='"rift_x64.exe","22532","Console","1","22,240 K"\n'+(
          '"rifterrorhandler_x64.exe","21120","Console","1","11,000 K"\n')+(
          '"GlyphClientApp.exe","9999","Console","1","30,000 K"\n')
        rows=p.parse_tasklist(stdout)
        self.assertEqual([(x["name"],x["pid"]) for x in rows],[
          ("rift_x64.exe",22532),("rifterrorhandler_x64.exe",21120)])
        self.assertEqual(p.parse_tasklist(
          "INFO: No tasks are running which match the specified criteria.\n"),[])
        with self.assertRaises(ValueError):
            p.parse_tasklist("x"*2_000_001)

    def test_fails_closed_on_crash_handler_or_ambiguous_game(self):
        cases=[
          ([], "game_process_absent"),
          ([{"name":"rifterrorhandler_x64.exe","pid":21120}],"error_handler_only"),
          ([{"name":"rift_x64.exe","pid":22532}],"game_process_present"),
          ([{"name":"rift_x64.exe","pid":22532},
            {"name":"rifterrorhandler_x64.exe","pid":21120}],"game_plus_error_handler")
        ]
        for value,expected in cases:
            with self.subTest(state=expected):
                self.assertEqual(p.classify_processes(value),expected)

    def test_candidates_respect_redirected_documents_and_only_bounded_roots(self):
        game_exe=str(self.root/"Glyph"/"Games"/"RIFT"/"Live"/"rift_x64.exe")
        paths=p.candidate_log_paths(
          self.home,self.docs,{"OneDrive":str(self.root/"OneDrive")},[game_exe])
        self.assertEqual(len(paths),6)
        self.assertEqual(paths[0],self.docs/"RIFT"/"Log.txt")
        self.assertIn(self.root/"Glyph"/"Games"/"RIFT"/"Live"/"Log.txt",paths)
        self.assertEqual(len({str(x).casefold() for x in paths}),len(paths))
        self.assertTrue(all(x.name in ("Log.txt","CombatLog.txt") for x in paths))

    def test_current_document_path_only_not_combatlog_for_noncombat_proof(self):
        combat=self.docs/"RIFT"/"CombatLog.txt"
        combat.write_text("[combat fixture]\n",encoding="utf-8")
        files=p.candidate_log_paths(self.home,self.docs,{},[])
        row=p.make_report([{"name":"rift_x64.exe","pid":30000}],"AMD-DESKTOP",
          self.docs,"fixture",files,None,None,"AMD-DESKTOP")
        self.assertFalse(row["canAttemptSupervisedLogTest"])
        self.assertIn("no_log_file_found_in_known_paths",row["blockers"])
        log=self.docs/"RIFT"/"Log.txt"
        log.write_text("[Say][Mock]: test\n",encoding="utf-8")
        row=p.make_report([{"name":"rift_x64.exe","pid":30000}],"AMD-DESKTOP",
          self.docs,"fixture",files,None,None,"AMD-DESKTOP")
        self.assertTrue(row["canAttemptSupervisedLogTest"])
        self.assertFalse(row["canClaimLiveChatReception"])
        self.assertFalse(row["readyForLiveChatAcceptance"])
        self.assertIn("modifiedLocal",next(x for x in row["logCandidates"] if x["path"]==str(log)))

    def test_stale_hwnd_and_stale_pid_are_explicit(self):
        rows=[{"name":"rifterrorhandler_x64.exe","pid":21120}]
        report=p.make_report(rows,"AMD-DESKTOP",self.docs,"fixture",
          [],{"hwnd":9965380,"present":False,"pid":None},22532,"AMD-DESKTOP")
        self.assertEqual(report["processState"],"error_handler_only")
        self.assertEqual(report["errorHandlerPids"],[21120])
        self.assertIn("expected_game_pid_not_running",report["blockers"])
        self.assertIn("window_identity_mismatch",report["blockers"])
        self.assertIn("no_unambiguous_active_game_process",report["blockers"])
        self.assertFalse(report["canAttemptSupervisedLogTest"])

    def test_foreground_window_must_belong_to_a_live_game_pid(self):
        path=self.docs/"RIFT"/"Log.txt"
        path.write_bytes(b"fixture\n")
        active=[{"name":"rift_x64.exe","pid":30000}]
        report=p.make_report(active,"AMD-DESKTOP",self.docs,"fixture",[path],
          {"hwnd":123,"present":True,"pid":40000},None,"AMD-DESKTOP")
        self.assertIn("window_identity_mismatch",report["blockers"])
        self.assertFalse(report["canAttemptSupervisedLogTest"])

    def test_wrong_hostname_is_blocking_and_cannot_infer_loaded_addon(self):
        f=self.docs/"RIFT"/"Log.txt";f.write_bytes(b"line\n")
        report=p.make_report([{"name":"rift_x64.exe","pid":30000}],"AMD-DESKTOP",
          self.docs,"fixture",[f],{"hwnd":123,"present":True,"pid":30000},
          30000,"LEGION")
        self.assertIn("unexpected_host",report["blockers"])
        self.assertFalse(report["canClaimGameLoaded"])
        self.assertFalse(report["canClaimLiveChatReception"])

    def test_log_metadata_is_only_stat_never_chat_contents(self):
        path=self.docs/"RIFT"/"Log.txt"
        secret="chat content must not appear"
        path.write_text(secret,encoding="utf-8")
        rows=p.inspect_log_candidates([path])
        self.assertTrue(rows[0]["exists"])
        self.assertEqual(rows[0]["bytes"],len(secret))
        self.assertNotIn(secret,json.dumps(rows))
        self.assertLessEqual(len(p.inspect_log_candidates([path]*100)),p.MAX_FILES)

    def test_tasklist_unavailable_is_not_an_empty_healthy_state(self):
        with mock.patch.object(p.subprocess,"run",side_effect=OSError("not installed")):
            output=io.StringIO()
            with contextlib.redirect_stdout(output):
                result=p.run(["--expect-host","AMD-DESKTOP"])
        self.assertEqual(result,1)
        parsed=json.loads(output.getvalue())
        self.assertEqual(parsed["status"],"unavailable")
        self.assertFalse(parsed["canClaimLiveChatReception"])

    def test_rift_cfg_client_document_directory_and_log_flags_are_whitelisted(self):
        custom=self.root/"CustomRiftData"
        custom.mkdir()
        source=("[Client]\n"
                f"DocumentsDirectory = {custom}\n"
                "LogConsole = False\n"
                "LogCombatConsole = False\n"
                "CombatLogFileFlushInterval = 0.500000\n"
                "UserPassword = should-not-be-output\n"
                "[Other]\nLogConsole = True\n")
        parsed=p.parse_rift_client_settings(source)
        self.assertEqual(Path(parsed["DocumentsDirectory"]),custom)
        self.assertFalse(parsed["LogConsole"])
        self.assertFalse(parsed["LogCombatConsole"])
        self.assertEqual(parsed["CombatLogFileFlushInterval"],0.5)
        self.assertNotIn("UserPassword",parsed)
        with self.assertRaises(ValueError):
            p.parse_rift_client_settings("x"*(512*1024+1))

    def test_real_game_config_file_is_read_only_and_controls_priority(self):
        appdata=self.root/"AppData"/"Roaming"
        cfg=appdata/"RIFT"/"Rift.cfg"
        cfg.parent.mkdir(parents=True)
        custom=self.root/"RIFT_Alternate_Output"
        custom.mkdir()
        cfg.write_text("[Client]\nDocumentsDirectory = "+str(custom)+
                       "\nLogConsole = False\n",encoding="utf-8")
        original=cfg.read_bytes()
        read=p.read_rift_config(self.root,{"APPDATA":str(appdata)})
        self.assertTrue(read["exists"])
        self.assertFalse(read["logFlagSemanticsConfirmed"])
        self.assertEqual(Path(read["settings"]["DocumentsDirectory"]),custom)
        self.assertEqual(cfg.read_bytes(),original)
        paths=p.candidate_log_paths(self.home,self.docs,{},[],custom)
        self.assertEqual(paths[0],custom/"Log.txt")
        self.assertIn(self.docs/"RIFT"/"Log.txt",paths)
        self.assertLess(len(paths),p.MAX_FILES)

    def test_rift_cfg_logconsole_false_is_hint_not_live_proof(self):
        log=self.docs/"RIFT"/"Log.txt"
        log.write_text("synthetic\n",encoding="utf-8")
        rows=[{"name":p.GAME,"pid":30000}]
        config={"exists":True,"path":"fixture/Rift.cfg",
                "settings":{"LogConsole":False,
                            "DocumentsDirectory":str(self.docs/"RIFT")},
                "logFlagSemanticsConfirmed":False}
        report=p.make_report(rows,"AMD-DESKTOP",self.docs,"fixture",[log],
                             None,None,"AMD-DESKTOP",config)
        self.assertTrue(report["canAttemptSupervisedLogTest"])
        self.assertIn("rift_cfg_logconsole_false_observed_runtime_semantics_unverified",
                      report["hints"])
        self.assertFalse(report["canClaimLiveChatReception"])
        self.assertFalse(report["gameConfig"]["logFlagSemanticsConfirmed"])

    def test_multibox_requires_exact_target_binding_before_log_correlation(self):
        log=self.docs/"RIFT"/"Log.txt"
        log.write_text("synthetic\n",encoding="utf-8")
        rows=[{"name":p.GAME,"pid":30000},{"name":p.GAME,"pid":30001}]
        report=p.make_report(rows,"AMD-DESKTOP",self.docs,"fixture",[log],
                             None,None,"AMD-DESKTOP")
        self.assertEqual(report["processState"],"multiple_game_processes")
        self.assertIn("multiple_game_processes_require_exact_target",report["blockers"])
        bound=p.make_report(rows,"AMD-DESKTOP",self.docs,"fixture",[log],
                            {"present":True,"hwnd":555,"pid":30000},
                            30000,"AMD-DESKTOP")
        self.assertTrue(bound["canAttemptSupervisedLogTest"])
        self.assertFalse(bound["readyForLiveChatAcceptance"])

    def test_error_handler_companion_is_not_crash_proof_when_game_is_running(self):
        log=self.docs/"RIFT"/"Log.txt"
        log.write_bytes(b"synthetic\n")
        rows=[{"name":p.GAME,"pid":42992},
              {"name":p.ERROR_HANDLER,"pid":31856}]
        output=p.make_report(rows,"AMD-DESKTOP",self.docs,"fixture",[log],
                             {"hwnd":24252650,"present":True,"pid":42992},
                             42992,"AMD-DESKTOP")
        self.assertEqual(output["processState"],"game_plus_error_handler")
        self.assertTrue(output["hasRunningGameProcess"])
        self.assertTrue(output["canAttemptSupervisedLogTest"])
        self.assertNotIn("no_unambiguous_active_game_process",output["blockers"])
        self.assertIn("error_handler_companion_present_not_crash_evidence",output["hints"])
        self.assertFalse(output["canClaimGameLoaded"])
        self.assertFalse(output["canClaimLiveChatReception"])

    def test_error_handler_only_remains_blocked_when_game_is_absent(self):
        log=self.docs/"RIFT"/"Log.txt"
        log.write_bytes(b"synthetic\n")
        output=p.make_report([{"name":p.ERROR_HANDLER,"pid":31856}],
                             "AMD-DESKTOP",self.docs,"fixture",[log],
                             None,None,"AMD-DESKTOP")
        self.assertFalse(output["hasRunningGameProcess"])
        self.assertFalse(output["canAttemptSupervisedLogTest"])
        self.assertIn("no_unambiguous_active_game_process",output["blockers"])

    def test_multibox_with_companion_requires_exact_target_window(self):
        log=self.docs/"RIFT"/"Log.txt"
        log.write_bytes(b"synthetic\n")
        rows=[{"name":p.GAME,"pid":42992},
              {"name":p.GAME,"pid":44556},
              {"name":p.ERROR_HANDLER,"pid":31856}]
        ambiguous=p.make_report(rows,"AMD-DESKTOP",self.docs,"fixture",[log],
                                None,None,"AMD-DESKTOP")
        self.assertEqual(ambiguous["processState"],
                         "multiple_games_plus_error_handler")
        self.assertIn("multiple_game_processes_require_exact_target",
                      ambiguous["blockers"])
        selected=p.make_report(rows,"AMD-DESKTOP",self.docs,"fixture",[log],
                               {"hwnd":24252650,"present":True,"pid":42992},
                               42992,"AMD-DESKTOP")
        self.assertTrue(selected["canAttemptSupervisedLogTest"])
        self.assertFalse(selected["canClaimLiveChatReception"])

if __name__=="__main__":
    unittest.main()
