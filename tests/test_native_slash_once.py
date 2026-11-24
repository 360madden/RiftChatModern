"""Guarded RCM native slash one-shot — mocked RIFT foreground/input tests.

No physical RIFT window receives input in any test case.
"""
import socket
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import rcm_native_slash_once as slash

HOST = socket.gethostname()
IDENTITY = {
    "schema": "RCM_GAME_SCREENSHOT_TRIGGER_V1",
    "status": "read_only_target_candidate",
    "machine": HOST,
    "pid": 37676,
    "hwnd": "0x360BC4",
    "startUtcTicks": 639308249563595623,
    "exePath": str(Path(__file__).resolve().parent / "fixtures" / "rift_x64.exe"),
    "exeSha256": "A" * 64,
}

class FakeBackend:
    def __init__(self, prior=0x30ADA, iconic=False, fail_at=None, external=False):
        self.target = int(IDENTITY["hwnd"], 16)
        self.previous = prior
        self.current = prior
        self.iconic = iconic
        self.events = []
        self.allocated_events = []
        self.focus_calls = []
        self.fail_at = fail_at
        self.external = external

    def map_virtual_key(self, vk, map_type):
        return vk

    def _validate_target(self, target):
        assert target["pid"] == IDENTITY["pid"]
        assert int(target["hwnd"], 16) == self.target
        return self.target, IDENTITY["pid"]

    def get_foreground(self):
        return self.current

    def is_iconic(self, hwnd):
        return self.iconic

    def is_window(self, hwnd):
        return True

    def _focus(self, hwnd, pid, delay):
        self.focus_calls.append(hwnd)
        self.current = hwnd
        self.iconic = False
        return {"exactHwndForeground": True}

    def _assert_exact_foreground(self, target, hwnd, pid):
        if self.current != self.target:
            raise RuntimeError("foreground_changed")

    def _key(self, scan, *, release):
        # The fake owns its inert event representation just as Win32Input
        # owns and validates its native ctypes INPUT layout.
        event = SimpleNamespace(type=1, u=SimpleNamespace(ki=SimpleNamespace(
            wVk=0, wScan=scan, dwFlags=0x0008 | (0x0002 if release else 0),
            time=0, dwExtraInfo=0)))
        self.allocated_events.append(event)
        return event

    def _insert(self, action):
        if self.fail_at is not None and len(self.events) == self.fail_at:
            raise RuntimeError("simulated_os_key_failure")
        self.events.append(action)
        if self.external and len(self.events) == 2:
            self.current = 0x999999

    def _owner(self, hwnd):
        return 789, 111

    def _restore(self, previous, hwnd):
        self.current = previous

    def show_window(self, hwnd, cmd):
        assert cmd == slash.SW_MINIMIZE
        self.iconic = True


class NativeSlashTests(unittest.TestCase):
    def invoke(self, flags, *, fake=None, inspector=None, modifiers=None):
        return slash.run(
            ["--expect-host", HOST, "--action", "reload", *flags],
            inspection=inspector or (lambda pid: IDENTITY),
            backend=fake, modifiers=modifiers or (lambda: None),
            hostname=HOST
        )

    def test_dry_run_does_not_access_focus_or_send_keys(self):
        code, record = self.invoke(["--dry-run", "--pid", str(IDENTITY["pid"])])
        self.assertEqual(code, 0)
        self.assertEqual(record["status"], "verified_dry_run")
        self.assertFalse(record["gameInputSent"])

    def test_explicit_ack_required(self):
        code, record = self.invoke(["--execute"])
        self.assertEqual(code, 1)
        self.assertFalse(record["gameInputSent"])

    def test_plan_uses_virtual_enter_and_unicode_characters(self):
        plan = slash._input_plan("/reloadui")
        self.assertEqual(len(plan), len("/reloadui") + 2)
        self.assertEqual(plan[0], ("virtual", slash.VK_RETURN))
        self.assertEqual(plan[-1], ("virtual", slash.VK_RETURN))
        self.assertEqual(plan[1], ("unicode", ord("/")))
        self.assertEqual(plan[2], ("unicode", ord("r")))
        with self.assertRaisesRegex(ValueError, "not_allowlisted"):
            slash._input_plan("/dance")
        with self.assertRaisesRegex(ValueError, "recovery_only_allowed"):
            slash._input_plan("/rcm", True)
        recover = slash._input_plan("/reloadui", True)
        self.assertEqual(recover[:2], [("virtual",slash.VK_BACKSPACE)]*2)
        self.assertEqual(recover[2], ("unicode",ord("/")))
        self.assertEqual(recover[-1], ("virtual",slash.VK_RETURN))

    def test_keyboard_event_preserves_backend_owned_layout_and_defaults(self):
        f = FakeBackend()
        for kind, value in (("virtual", slash.VK_RETURN), ("unicode", ord("/"))):
            for release in (False, True):
                with self.subTest(kind=kind, release=release):
                    event = slash._keyboard_event(f, kind, value, release=release)
                    self.assertIs(event, f.allocated_events[-1])
                    self.assertEqual(event.type, 1)
                    self.assertEqual(event.u.ki.wVk, value if kind == "virtual" else 0)
                    self.assertEqual(event.u.ki.wScan, value if kind == "unicode" else 0)
                    self.assertEqual(event.u.ki.dwFlags,
                        (slash.UNICODE_FLAG if kind == "unicode" else 0)
                        | (slash.KEYUP_FLAG if release else 0))
                    self.assertEqual((event.u.ki.time, event.u.ki.dwExtraInfo), (0, 0))

    def test_injected_backend_needs_no_private_module_import(self):
        f = FakeBackend()
        # Block the sibling import even on a developer PC where it exists.
        # The injected backend must supply every event object it receives.
        with mock.patch.dict(sys.modules, {"python_win32_input": None}):
            code, report = self.invoke(["--execute", "--ack-native-chat"], fake=f)
        self.assertEqual(code, 0, report)
        self.assertEqual(len(f.events), 2 * (len("/reloadui") + 2))
        self.assertEqual(len(f.allocated_events), len(f.events))
        for allocated, inserted in zip(f.allocated_events, f.events):
            self.assertIs(allocated, inserted)
        self.assertTrue(report["restoredPreviousForeground"])

    def test_event_construction_failure_refuses_before_focus_or_input(self):
        class BrokenFactory(FakeBackend):
            def _key(self, scan, *, release):
                raise RuntimeError("event_factory_unavailable")
        f = BrokenFactory()
        code, report = self.invoke(["--execute", "--ack-native-chat"], fake=f)
        self.assertEqual(code, 2)
        self.assertEqual(report["status"], "input_plan_refused")
        self.assertEqual(report["reason"], "event_factory_unavailable")
        self.assertFalse(report["gameInputSent"])
        self.assertEqual(f.focus_calls, [])
        self.assertEqual(f.events, [])

    def test_realistic_session_restores_prior_and_minimized_state(self):
        f = FakeBackend(iconic=True)
        code, report = self.invoke(["--execute", "--ack-native-chat",
                                    "--pid", str(IDENTITY["pid"])], fake=f)
        self.assertEqual(code, 0)
        self.assertEqual(report["status"], "windows_keys_inserted_game_consumption_unverified")
        self.assertFalse(report["inGameCommandVerified"])
        self.assertTrue(report["restoredPreviousForeground"])
        self.assertTrue(report["minimizedStateRestored"])
        self.assertEqual(f.current, f.previous)
        self.assertTrue(f.iconic)
        self.assertEqual(report["keyEventsInserted"], 2*(len("/reloadui")+2))
        self.assertEqual(len(f.events), 2*(len("/reloadui")+2))
        self.assertEqual((f.events[0].u.ki.wVk, f.events[0].u.ki.dwFlags),
                         (slash.VK_RETURN, 0))
        self.assertEqual((f.events[1].u.ki.wVk, f.events[1].u.ki.dwFlags),
                         (slash.VK_RETURN, slash.KEYUP_FLAG))
        self.assertEqual((f.events[2].u.ki.wVk, f.events[2].u.ki.wScan,
                          f.events[2].u.ki.dwFlags),
                         (0, ord("/"), slash.UNICODE_FLAG))
        self.assertEqual((f.events[-1].u.ki.wVk, f.events[-1].u.ki.dwFlags),
                         (slash.VK_RETURN, slash.KEYUP_FLAG))

    def test_log_toggle_requires_explicit_ack_and_never_claims_live_state(self):
        f=FakeBackend()
        baseline=["--execute","--ack-native-chat","--action","log-toggle"]
        # invoke() already supplies --action reload: command-line parsing should
        # reject duplicates; use the underlying action directly.
        code,receipt=slash.run([
            "--expect-host",HOST,"--action","log-toggle",
            "--execute","--ack-native-chat"],
            inspection=lambda pid:IDENTITY,backend=f,
            modifiers=lambda:None,hostname=HOST)
        self.assertEqual(code,1)
        self.assertEqual(receipt["status"],"log_toggle_requires_explicit_ack")
        self.assertEqual(f.events,[])
        code,receipt=slash.run([
            "--expect-host",HOST,"--action","log-toggle",
            "--execute","--ack-native-chat","--ack-log-toggle"],
            inspection=lambda pid:IDENTITY,backend=f,
            modifiers=lambda:None,hostname=HOST)
        self.assertEqual(code,0)
        self.assertEqual(receipt["keyEventsInserted"],2*(len("/log")+2))
        self.assertFalse(receipt["inGameCommandVerified"])
        self.assertTrue(receipt["restoredPreviousForeground"])
        self.assertEqual(f.current,f.previous)

    def test_exact_public_canary_only_with_separate_ack(self):
        f=FakeBackend()
        token="RCM_CHAT_TEST_20261121"
        def attempt(extra):
            return slash.run([
                "--expect-host",HOST,"--action","say-canary",
                "--chat-canary",token,"--execute","--ack-native-chat",
                *extra],
                inspection=lambda pid:IDENTITY,backend=f,
                modifiers=lambda:None,hostname=HOST)
        code,receipt=attempt([])
        self.assertEqual(code,1)
        self.assertEqual(receipt["status"],"public_canary_requires_explicit_ack")
        self.assertEqual(f.events,[])
        code,receipt=attempt(["--ack-public-say"])
        self.assertEqual(code,0)
        self.assertEqual(receipt["keyEventsInserted"],2*(len("/say "+token)+2))
        self.assertTrue(receipt["gameInputSent"])
        self.assertFalse(receipt["inGameCommandVerified"])
        self.assertEqual(f.current,f.previous)
        # Restrict the path to an ASCII test token, not arbitrary social text.
        for invalid in ("hello there","RCM_BAD:TEXT","RCM_BAD\nOTHER",
                        "RCM_"+"A"*81):
            code,receipt=slash.run([
                "--expect-host",HOST,"--action","say-canary",
                "--chat-canary",invalid,"--execute","--ack-native-chat",
                "--ack-public-say"],
                inspection=lambda pid:IDENTITY,backend=FakeBackend(),
                modifiers=lambda:None,hostname=HOST)
            self.assertEqual(code,1)
            self.assertFalse(receipt["gameInputSent"])

    def test_exact_open_native_chat_recovery_requires_separate_ack(self):
        f = FakeBackend()
        code, report = self.invoke(
            ["--execute","--ack-native-chat","--recover-two-stars"],fake=f)
        self.assertEqual(code,1)
        self.assertEqual(f.events,[])
        code, report = self.invoke(
            ["--execute","--ack-native-chat","--recover-two-stars",
             "--ack-current-chat-open"],fake=f)
        self.assertEqual(code,0)
        self.assertEqual(report["keyEventsInserted"],
                         2*(len("/reloadui")+3))
        self.assertEqual(f.events[0].u.ki.wVk, slash.VK_BACKSPACE)
        self.assertEqual(f.events[2].u.ki.wVk, slash.VK_BACKSPACE)
        self.assertEqual(f.events[4].u.ki.wScan, ord("/"))
        self.assertEqual(f.events[-1].u.ki.wVk,slash.VK_RETURN)

    def test_focus_throws_after_activation_restores_previous_window(self):
        class HalfFocused(FakeBackend):
            def _focus(self, hwnd, pid, delay):
                super()._focus(hwnd, pid, delay)
                raise RuntimeError("simulated_focus_error_after_activation")
        f = HalfFocused()
        code, report = self.invoke(["--execute", "--ack-native-chat"], fake=f)
        self.assertEqual(code, 2)
        self.assertEqual(f.events, [])
        self.assertEqual(f.current, f.previous)
        self.assertTrue(report["restoredPreviousForeground"])

    def test_transient_zero_foreground_during_restore_is_not_false_failure(self):
        class SettlingBackend(FakeBackend):
            def __init__(self):
                super().__init__()
                self.waiting = False
                self.polls = 0
            def _restore(self, previous, hwnd):
                self.current = 0
                self.waiting = True
            def get_foreground(self):
                if self.waiting:
                    self.polls += 1
                    if self.polls >= 3:
                        self.waiting = False
                        self.current = self.previous
                return self.current
        f = SettlingBackend()
        code, report = self.invoke(["--execute", "--ack-native-chat"], fake=f)
        self.assertEqual(code, 0)
        self.assertTrue(report["restoredPreviousForeground"])
        self.assertEqual(f.current, f.previous)
        self.assertGreaterEqual(f.polls, 3)

    def test_unknown_modifier_refuses_before_focus(self):
        f=FakeBackend()
        code, report=self.invoke(["--execute","--ack-native-chat"],fake=f,
                                 modifiers=lambda: (_ for _ in ()).throw(RuntimeError("held")))
        self.assertEqual(code, 2)
        self.assertEqual(report["status"], "input_plan_refused")
        self.assertEqual(f.focus_calls, [])
        self.assertEqual(f.events, [])

    def test_partial_key_insert_stops_and_reports_uncertainty(self):
        f=FakeBackend(fail_at=5)
        code, report=self.invoke(["--execute","--ack-native-chat"],fake=f)
        self.assertEqual(code, 2)
        self.assertIn(report["status"], ("partial_or_refused_no_retry",))
        self.assertLess(len(f.events), 2*(len("/reloadui")+2))
        self.assertEqual(f.current, f.previous)
        self.assertTrue(report["restoredPreviousForeground"])

    def test_external_focus_change_does_not_override_new_user_window(self):
        f=FakeBackend(external=True)
        code, report=self.invoke(["--execute","--ack-native-chat"],fake=f)
        self.assertEqual(code, 2)
        self.assertTrue(report.get("externalFocusChangePreserved"))
        self.assertEqual(f.current, 0x999999)

    def test_wrong_pid_or_host_rejected_before_native_input(self):
        f=FakeBackend()
        code, report=self.invoke(["--execute","--ack-native-chat","--pid","12"],fake=f)
        self.assertEqual(code, 2)
        self.assertFalse(report["gameInputSent"])
        self.assertEqual(f.events, [])
        code, report=slash.run(["--expect-host","WRONG-PC","--action","reload",
                               "--execute","--ack-native-chat"],
                               hostname=HOST,backend=f)
        self.assertEqual(code,1)

if __name__ == "__main__":
    unittest.main()
