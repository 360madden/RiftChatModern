"""RCM read-only Windows session/log preflight; all tests use local fixtures."""
import contextlib, csv, errno, io, json, os, stat
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

    def test_explicit_invalid_documents_overrides_fail_closed(self):
        for assignment in ("DocumentsDirectory = relative", "DocumentsDirectory =",
                           'DocumentsDirectory = ""', 'DocumentsDirectory = "' + str(self.root),
                           "DocumentsDirectory: " + str(self.root),
                           "DocumentsDirectory = " + str(self.root / "%RCM_MISSING_FIXTURE%")):
            with self.subTest(assignment=assignment), mock.patch.dict(os.environ, {}, clear=True):
                with self.assertRaisesRegex(ValueError, "invalid_documents_directory"):
                    p.parse_rift_client_settings("[Client]\n" + assignment)

    def test_duplicate_case_insensitive_documents_overrides_refused(self):
        with self.assertRaisesRegex(ValueError, "invalid_documents_directory"):
            p.parse_rift_client_settings("[Client]\nDocumentsDirectory = " +
                str(self.root) + "\ndocumentsdirectory = " + str(self.docs))

    def test_valid_quoted_override_and_nonclient_dotted_section(self):
        result=p.parse_rift_client_settings('[client]\ndocumentsdirectory = "' +
            str(self.root) + '"\n[Other.Section]\nDocumentsDirectory = ignored')
        self.assertEqual(result, {"DocumentsDirectory": str(self.root)})

    def test_unreadable_or_invalid_config_is_not_missing(self):
        env={"APPDATA": str(self.root / "roaming")}
        cfg=Path(env["APPDATA"])/"RIFT"/"Rift.cfg"
        cfg.parent.mkdir(parents=True)
        self.assertNotIn("readError", p.read_rift_config(self.root,env))
        cfg.write_bytes(b"[Client]\nDocumentsDirectory = relative\n")
        self.assertIn("readError",p.read_rift_config(self.root,env))
        cfg.write_bytes(b"[Client]\nDocumentsDirectory = \xff")
        self.assertIn("readError",p.read_rift_config(self.root,env))
        cfg.unlink()
        cfg.mkdir()
        self.assertIn("readError",p.read_rift_config(self.root,env))

    def test_stale_fallback_log_does_not_qualify_configured_root(self):
        stale=self.docs/"RIFT"/"Log.txt"
        stale.write_text("fixture\n",encoding="utf-8")
        current=self.root/"configured"
        current.mkdir()
        active=current/"Log.txt"
        rows=[{"name":p.GAME,"pid":30000}]
        config={"settings":{"DocumentsDirectory":str(current)}}
        report=p.make_report(rows,"LEGION",self.docs,"fixture",[active,stale],
                             None,None,"LEGION",config)
        self.assertIn("no_log_file_in_configured_documents_directory",report["blockers"])
        self.assertFalse(report["canAttemptSupervisedLogTest"])
        active.write_text("new fixture\n",encoding="utf-8")
        report=p.make_report(rows,"LEGION",self.docs,"fixture",[active,stale],
                             None,None,"LEGION",config)
        self.assertTrue(report["canAttemptSupervisedLogTest"])
        self.assertFalse(report["canClaimLiveChatReception"])

    def test_config_read_error_blocks_supervised_test_even_with_log(self):
        log=self.docs/"RIFT"/"Log.txt"
        log.write_text("fixture\n",encoding="utf-8")
        report=p.make_report([{"name":p.GAME,"pid":30000}],"LEGION",
            self.docs,"fixture",[log],None,None,"LEGION",
            {"settings":{},"readError":"unavailable"})
        self.assertIn("rift_config_unreadable",report["blockers"])
        self.assertFalse(report["canAttemptSupervisedLogTest"])

    def test_unreadable_configured_log_cannot_fall_back_to_readable_old_log(self):
        current=self.root/"configured"
        current.mkdir()
        active=current/"Log.txt"
        active.write_bytes(b"private current log")
        stale=self.docs/"RIFT"/"Log.txt"
        stale.write_bytes(b"readable stale log")
        denied={"readable":False,"readError":"cloud_file_provider_not_running",
                "readErrno":22,"readWinerror":362}
        completed=p.subprocess.CompletedProcess([],0,json.dumps(denied),"")
        with mock.patch.object(p.subprocess,"run",return_value=completed) as probe:
            report=p.make_report([{"name":p.GAME,"pid":30000}],"LEGION",
                self.docs,"fixture",[active,stale],None,None,"LEGION",
                {"settings":{"DocumentsDirectory":str(current)}})
        self.assertFalse(report["canAttemptSupervisedLogTest"])
        self.assertIn("configured_log_not_readable",report["blockers"])
        self.assertEqual(probe.call_count,1)
        self.assertEqual(probe.call_args.args[0][-1],str(active))
        self.assertEqual(report["logCandidates"][0]["readWinerror"],362)
        self.assertNotIn("readable",report["logCandidates"][1])
        self.assertNotIn("private current log",json.dumps(report))

    def test_log_read_probe_timeout_blocks_supervised_test(self):
        log=self.docs/"RIFT"/"Log.txt"
        log.write_bytes(b"fixture")
        with mock.patch.object(p.subprocess,"run",side_effect=p.subprocess.TimeoutExpired(
                ["private path must not be output"],3,output=b"private log")):
            report=p.make_report([{"name":p.GAME,"pid":30000}],"LEGION",
                self.docs,"fixture",[log],None,None,"LEGION",
                {"settings":{"DocumentsDirectory":str(log.parent)}})
        self.assertFalse(report["canAttemptSupervisedLogTest"])
        self.assertEqual(report["logCandidates"][0]["readError"],"probe_timeout")
        self.assertNotIn("private",json.dumps(report))

    def test_log_read_probe_failure_or_bad_response_cannot_qualify(self):
        log=self.docs/"RIFT"/"Log.txt"
        log.write_bytes(b"fixture")
        cases=[(1,'{"readable": true}'),(0,"not json"),
               (0,'{"readable": "true"}'),(0,'{"readable": true, "chat": "secret"}'),
               (0,'{"readable": true, "readError": "unavailable"}'),
               (0,'{"readable":false,"readError":[]}'),
               (0,'{"readable":false,"readError":"unavailable","readWinerror":"private"}'),
               (0,"x"*5000)]
        for exit_code,stdout in cases:
            with self.subTest(exit_code=exit_code,stdout=stdout[:80]), mock.patch.object(
                    p.subprocess,"run",return_value=p.subprocess.CompletedProcess(
                        [],exit_code,stdout,"private stderr")):
                report=p.make_report([{"name":p.GAME,"pid":30000}],"LEGION",
                    self.docs,"fixture",[log],None,None,"LEGION",
                    {"settings":{"DocumentsDirectory":str(log.parent)}})
            self.assertFalse(report["canAttemptSupervisedLogTest"])
            self.assertIn("configured_log_not_readable",report["blockers"])
            self.assertNotIn("secret",json.dumps(report))
            self.assertNotIn("private stderr",json.dumps(report))

    def test_existing_but_unreadable_logs_without_override_do_not_qualify(self):
        log=self.docs/"RIFT"/"Log.txt"
        log.write_bytes(b"fixture")
        completed=p.subprocess.CompletedProcess([],0,
            '{"readable":false,"readError":"permission_denied","readErrno":13}',"")
        with mock.patch.object(p.subprocess,"run",return_value=completed):
            report=p.make_report([{"name":p.GAME,"pid":30000}],"LEGION",
                self.docs,"fixture",[log],None,None,"LEGION")
        self.assertFalse(report["canAttemptSupervisedLogTest"])
        self.assertIn("no_readable_log_file_found_in_known_paths",report["blockers"])

    def test_probe_reads_only_one_byte_and_empty_log_is_readable(self):
        log=self.docs/"RIFT"/"Log.txt"
        original=b"private contents\n"*1000
        log.write_bytes(original)
        with mock.patch.object(p.os,"read",wraps=os.read) as read:
            result=p._read_log_probe(log)
        self.assertEqual(result,{"readable":True})
        self.assertEqual(read.call_count,1)
        self.assertEqual(read.call_args.args[1],1)
        self.assertEqual(log.read_bytes(),original)
        log.write_bytes(b"")
        report=p.make_report([{"name":p.GAME,"pid":30000}],"LEGION",
            self.docs,"fixture",[log],None,None,"LEGION",
            {"settings":{"DocumentsDirectory":str(log.parent)}})
        self.assertTrue(report["canAttemptSupervisedLogTest"])
        self.assertTrue(report["logCandidates"][0]["readable"])
        self.assertFalse(report["canClaimLiveChatReception"])
        self.assertFalse(report["canClaimGameLoaded"])
        self.assertFalse(report["readyForLiveChatAcceptance"])
        self.assertFalse(report["gameInputSent"])
        self.assertFalse(report["gameLoggingChanged"])
        self.assertEqual(log.read_bytes(),b"")

    def test_probe_os_errors_are_sanitized_and_close_the_open_handle(self):
        log=self.docs/"RIFT"/"Log.txt"
        log.write_bytes(b"fixture")
        cloud=[]
        for code in (362,0x8007016A,-2147024534):
            error=OSError(errno.EIO,"private exception content")
            error.winerror=code
            cloud.append((error,"cloud_file_provider_not_running"))
        cases=cloud+[(PermissionError(errno.EACCES,"private"),"permission_denied"),
                     (FileNotFoundError(errno.ENOENT,"private"),"missing"),
                     (OSError(errno.EINVAL,"private"),"unavailable"),
                     (OSError(errno.EIO,"private"),"unavailable")]
        for error,reason in cases:
            with self.subTest(reason=reason,winerror=getattr(error,"winerror",None)), \
                    mock.patch.object(p.os,"read",side_effect=error), \
                    mock.patch.object(p.os,"close",wraps=os.close) as close:
                result=p._read_log_probe(log)
            self.assertFalse(result["readable"])
            self.assertEqual(result["readError"],reason)
            self.assertEqual(close.call_count,1)
            self.assertNotIn("private",json.dumps(result))

    def test_probe_rejects_disappearance_and_nonregular_objects(self):
        log=self.docs/"RIFT"/"Log.txt"
        log.mkdir()
        with mock.patch.object(p.os,"open") as opened:
            self.assertEqual(p._read_log_probe(log),
                {"readable":False,"readError":"not_regular_file"})
        opened.assert_not_called()
        log.rmdir()
        self.assertEqual(p._read_log_probe(log)["readError"],"missing")
        log.write_bytes(b"fixture")
        with mock.patch.object(p.Path,"lstat",return_value=mock.Mock(st_mode=stat.S_IFLNK)), \
                mock.patch.object(p.os,"open") as opened:
            self.assertEqual(p._read_log_probe(log),
                {"readable":False,"readError":"not_regular_file"})
        opened.assert_not_called()
        with mock.patch.object(p.os,"open",side_effect=FileNotFoundError(
                errno.ENOENT,"removed between stat and open")):
            self.assertEqual(p._read_log_probe(log)["readError"],"missing")
        with mock.patch.object(p.os,"fstat",return_value=mock.Mock(st_mode=stat.S_IFIFO)), \
                mock.patch.object(p.os,"read") as read, \
                mock.patch.object(p.os,"close",wraps=os.close) as close:
            self.assertEqual(p._read_log_probe(log),
                {"readable":False,"readError":"not_regular_file"})
        read.assert_not_called()
        close.assert_called_once()

    def test_unconfigured_probe_stops_at_readable_log_and_never_reads_combat_log(self):
        first=self.docs/"RIFT"/"Log.txt"
        first.write_bytes(b"fixture")
        second=self.root/"Log.txt"
        second.write_bytes(b"fixture")
        combat=self.root/"CombatLog.txt"
        combat.write_bytes(b"combat fixture")
        outcomes=[p.subprocess.CompletedProcess([],0,
                  '{"readable":false,"readError":"unavailable"}',""),
                  p.subprocess.CompletedProcess([],0,'{"readable":true}',"")]
        with mock.patch.object(p.subprocess,"run",side_effect=outcomes) as probe:
            report=p.make_report([{"name":p.GAME,"pid":30000}],"LEGION",
                self.docs,"fixture",[combat,first,second,first],None,None,"LEGION")
        self.assertTrue(report["canAttemptSupervisedLogTest"])
        self.assertEqual([call.args[0][-1] for call in probe.call_args_list],
                         [str(first),str(second)])
        self.assertNotIn("readable",report["logCandidates"][0])
        self.assertNotIn("readable",report["logCandidates"][3])

if __name__=="__main__":
    unittest.main()
