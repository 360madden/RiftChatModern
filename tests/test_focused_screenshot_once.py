"""Managed RIFT foreground screenshot orchestrator regression tests.

All focus, game-input, and screenshot operations are faked. No desktop actions.
"""
from pathlib import Path
import socket
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import rcm_focused_screenshot_once as focus_shot

HOST = socket.gethostname()
PIN = {
    "schema": "RCM_GAME_SCREENSHOT_TRIGGER_V1",
    "status": "read_only_target_candidate",
    "machine": HOST,
    "pid": 37676,
    "hwnd": "0x360BC4",
    "startUtcTicks": 639308249563595623,
    "exePath": r"C:\Program Files (x86)\Glyph\Games\RIFT\Live\rift_x64.exe",
    "exeSha256": "A"*64,
}


class FakeFocus:
    def __init__(self, *, previous=0x30ADA, target=0x360BC4, iconic=False):
        self.previous = previous
        self.target = target
        self.current = previous
        self.calls = []
        self.iconic = iconic

    def _validate_target(self, target):
        self.calls.append(("validate", dict(target)))
        if target["pid"] != PIN["pid"] or int(target["hwnd"], 16) != self.target:
            raise RuntimeError("mismatched_pid_or_hwnd")
        return self.target, PIN["pid"]

    def get_foreground(self):
        return self.current

    def _focus(self, hwnd, pid, delay):
        self.calls.append(("focus", hwnd, pid, delay))
        self.current = hwnd
        self.iconic = False
        return {"exactHwndForeground": True}

    def is_iconic(self, hwnd):
        return self.iconic

    def show_window(self, hwnd, how):
        assert how == 6
        self.calls.append(("minimize", hwnd))
        self.iconic = True

    def _owner(self, hwnd):
        return 400, 500

    def is_window(self, hwnd):
        return True

    def _restore(self, previous, target):
        self.calls.append(("restore", previous))
        self.current = previous


class ManagedScreenshotTests(unittest.TestCase):
    def call(self, flags, *, inspector=None, backend=None, shot=None):
        inspected = []
        def inspect(pid):
            inspected.append(pid)
            return PIN if inspector is None else inspector(pid)
        code, receipt = focus_shot.execute(
            ["--expect-host", HOST, *flags],
            inspector=inspect,
            backend=backend,
            shot=shot,
            hostname=HOST,
        )
        return code, receipt, inspected

    def test_capture_temporarily_focuses_game_once_then_restores(self):
        f = FakeFocus()
        input_calls = []
        def shoot(args):
            input_calls.append(args)
            self.assertEqual(f.current, f.target)
            return 0, {"schema": "RCM_SCREENSHOT_SESSION_V1",
                       "screenshotFileVerified": True, "gameInputSent": True,
                       "status": "new_post_key_image_verified"}
        code, report, inspected = self.call(
            ["--pid", str(PIN["pid"]), "--capture", "--ack-temporary-focus",
             "--ack-single-screenshot"], backend=f, shot=shoot,
        )
        self.assertEqual(code, 0)
        self.assertEqual(report["status"], "capture_verified")
        self.assertTrue(report["restoredPreviousForeground"])
        self.assertEqual(report["restoreStatus"], "restored")
        self.assertTrue(report["gameInputSent"])
        self.assertEqual(f.current, f.previous)
        self.assertEqual(inspected, [PIN["pid"]])
        self.assertEqual(len(input_calls), 1)
        self.assertIn("--ack-single-screenshot", input_calls[0])
        self.assertEqual([c[0] for c in f.calls], ["validate", "focus", "restore"])

    def test_original_minimized_state_is_restored_after_real_screenshot(self):
        f = FakeFocus(iconic=True)
        code, report, _ = self.call(
            ["--capture", "--ack-temporary-focus", "--ack-single-screenshot"],
            backend=f, shot=lambda args:(0, {"status":"new_post_key_image_verified",
                                           "gameInputSent":True,
                                           "screenshotFileVerified":True}))
        self.assertEqual(code, 0)
        self.assertTrue(report["restoredPreviousForeground"])
        self.assertTrue(report["minimizedStateRestored"])
        self.assertTrue(f.iconic)
        self.assertEqual(f.current, f.previous)
        self.assertIn(("minimize", f.target), f.calls)
        self.assertTrue(any(c[0]=="focus" and c[3]>=1200 for c in f.calls))

    def test_dryrun_never_constructs_focus_or_triggers_input(self):
        def shot(args):
            self.fail("dry run needs only verified identity, no child action")
        code, report, inspected = self.call(["--dry-run"], shot=shot)
        self.assertEqual(code, 0)
        self.assertEqual(report["status"], "ready_to_focus_no_input")
        self.assertFalse(report["focusChanged"])
        self.assertFalse(report["gameInputSent"])
        self.assertEqual(inspected, [None])

    def test_missing_ack_rejected_without_inspection_or_input(self):
        code, report, inspected = self.call(["--capture", "--ack-single-screenshot"])
        self.assertEqual(code, 1)
        self.assertEqual(report["status"], "refused")
        self.assertEqual(inspected, [])

    def test_wrong_host_rejected_before_ever_inspecting_game(self):
        code, report = focus_shot.execute(
            ["--expect-host", "NONEXISTENT-PC", "--capture",
             "--ack-temporary-focus", "--ack-single-screenshot"],
            inspector=lambda pid: self.fail("must not inspect"),
            backend=FakeFocus(), shot=lambda a: self.fail("must not capture"),
            hostname=HOST
        )
        self.assertEqual(code, 1)
        self.assertEqual(report["reason"], "wrong_host")

    def test_stale_target_refused_without_foreground_change(self):
        f = FakeFocus()
        code, report, inspected = self.call(
            ["--pid", "12345", "--capture", "--ack-temporary-focus",
             "--ack-single-screenshot"], backend=f,
            shot=lambda a: self.fail("must not capture"))
        self.assertEqual(code, 2)
        self.assertEqual(report["status"], "refused_before_focus")
        self.assertEqual(f.calls, [])

    def test_exception_after_focus_restores_and_preserves_input_uncertainty(self):
        f = FakeFocus()
        def fails(args):
            self.assertEqual(f.current, f.target)
            raise RuntimeError("post_send_return_unavailable")
        code, report, _ = self.call(
            ["--capture", "--ack-temporary-focus", "--ack-single-screenshot"],
            backend=f, shot=fails)
        self.assertEqual(code, 2)
        self.assertEqual(report["status"], "capture_or_focus_exception")
        self.assertIsNone(report["gameInputSent"])
        self.assertEqual(f.current, f.previous)
        self.assertTrue(report["restoredPreviousForeground"])

    def test_screenshot_child_success_without_file_is_not_success(self):
        f = FakeFocus()
        code, report, _ = self.call(
            ["--capture", "--ack-temporary-focus", "--ack-single-screenshot"],
            backend=f, shot=lambda args:(0, {"status": "inconsistent_receipt",
                                           "gameInputSent": True,
                                           "screenshotFileVerified": False}))
        self.assertEqual(code, 2)
        self.assertEqual(report["status"], "capture_inconclusive")
        self.assertTrue(report["gameInputSent"])
        self.assertTrue(report["restoredPreviousForeground"])

    def test_external_focus_change_not_overwritten(self):
        f=FakeFocus()
        external=0x999999
        def during_capture(args):
            f.current = external
            return 2, {"status": "foreground_lost_no_input", "gameInputSent": False}
        code, report, _ = self.call(
            ["--capture", "--ack-temporary-focus", "--ack-single-screenshot"],
            backend=f, shot=during_capture)
        self.assertEqual(code, 2)
        self.assertEqual(report["restoreStatus"], "external_focus_change_preserved")
        self.assertEqual(f.current, external)
        self.assertNotIn("restore", [x[0] for x in f.calls])

    def test_foreground_stolen_during_restore_is_not_reclaimed(self):
        class InterruptedRestore(FakeFocus):
            def _restore(self, previous, target):
                self.calls.append(("restore", previous))
                self.current = 0x999999  # another application became active
        f = InterruptedRestore()
        code, report, _ = self.call(
            ["--capture", "--ack-temporary-focus", "--ack-single-screenshot"],
            backend=f, shot=lambda args:(0, {
                "status":"new_post_key_image_verified",
                "gameInputSent":True, "screenshotFileVerified":True}))
        self.assertEqual(code, 0)
        self.assertEqual(f.current, 0x999999)
        self.assertEqual(report["restoreStatus"], "restore_unverified")
        self.assertFalse(report["restoredPreviousForeground"])
        self.assertEqual(len([c for c in f.calls if c[0]=="focus"]), 1)

    def test_user_starts_in_foreground_does_not_switch_away(self):
        f=FakeFocus(previous=PIN["pid"],target=0x360BC4)
        f.previous=f.target
        f.current=f.target
        code, report, _=self.call(
            ["--capture", "--ack-temporary-focus", "--ack-single-screenshot"],
            backend=f, shot=lambda args:(0, {"status":"new_post_key_image_verified",
                                           "gameInputSent":True,
                                           "screenshotFileVerified":True}))
        self.assertEqual(code, 0)
        self.assertEqual(f.current, f.target)
        self.assertEqual(report["restoreStatus"],"rift_was_already_foreground")


if __name__ == "__main__":
    unittest.main()
