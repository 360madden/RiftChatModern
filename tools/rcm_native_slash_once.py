"""One exact RIFT native chat command through the proven Windows focus backend.

Only fixed /reloadui, /rcm, /log and a bounded /say RCM_* canary are
allowed. /log toggles an important noncombat-log setting; explicit extra ack
is required and a separate game/file receipt must establish its result.
Public /say canaries require their own acknowledgement. Default is read-only.
"""
from __future__ import annotations

import argparse
import ctypes
from ctypes import wintypes
import json
import re
import time
import socket
import sys
from pathlib import Path

import rcm_focused_screenshot_once as focused

SCHEMA = "RCM_NATIVE_SLASH_V1"
COMMANDS = {"reload": "/reloadui", "show": "/rcm",
            "log-toggle": "/log", "say-canary": "/say"}
VK_RETURN = 0x0D
VK_BACKSPACE = 0x08
UNICODE_FLAG = 0x0004
KEYUP_FLAG = 0x0002
SW_MINIMIZE = 6
MAX_ACTION_KEYS = 85


def _modifier_guard():
    user = ctypes.WinDLL("user32", use_last_error=True)
    key_state = user.GetAsyncKeyState
    key_state.argtypes = (ctypes.c_int,)
    key_state.restype = ctypes.c_short
    for code in (0x10, 0x11, 0x12, 0x5B, 0x5C):
        if key_state(code) & 0x8000:
            raise RuntimeError("modifier_held_abort_before_input")


def _input_plan(command: str, recover_two_stars: bool = False):
    if command not in COMMANDS.values() and not re.fullmatch(
            r"/say RCM_[A-Z0-9_]{8,64}", command):
        raise ValueError("command_not_allowlisted")
    if recover_two_stars and command != "/reloadui":
        raise ValueError("recovery_only_allowed_for_reloadui")
    # RIFT's native chat does not accept scan-code Enter as a submission.
    # Use the existing RCM editor sender's proven Windows event formats:
    # virtual-key Enter/Backspace and Unicode text (VK_PACKET).
    prefix = ([("virtual", VK_BACKSPACE)] * 2 if recover_two_stars
              else [("virtual", VK_RETURN)])
    plan = prefix + [("unicode", ord(ch)) for ch in command]
    plan.append(("virtual", VK_RETURN))
    if len(plan) > MAX_ACTION_KEYS:
        raise RuntimeError("command_plan_exceeds_bound")
    return plan


def _keyboard_event(kind: str, value: int, *, release: bool):
    # Reuse the validated 64-bit Win32 INPUT layout from the existing helper.
    backend_folder = str(focused.FOCUS_BACKEND.parent)
    if backend_folder not in sys.path:
        sys.path.insert(0, backend_folder)
    from python_win32_input import INPUT, INPUTUNION, KEYBDINPUT, INPUT_KEYBOARD
    flags = (UNICODE_FLAG if kind == "unicode" else 0) | (KEYUP_FLAG if release else 0)
    return INPUT(type=INPUT_KEYBOARD, u=INPUTUNION(
        ki=KEYBDINPUT(0 if kind == "unicode" else value,
                      value if kind == "unicode" else 0, flags, 0, 0)))


def run(argv=None, *, inspection=None, backend=None, keyscan=None,
        modifiers=None, hostname=None):
    p = argparse.ArgumentParser(description=__doc__)
    mode = p.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--execute", action="store_true")
    p.add_argument("--expect-host", required=True)
    p.add_argument("--pid", type=int)
    p.add_argument("--action", choices=tuple(COMMANDS), required=True)
    p.add_argument("--ack-native-chat", action="store_true")
    p.add_argument("--ack-log-toggle", action="store_true")
    p.add_argument("--ack-public-say", action="store_true")
    p.add_argument("--chat-canary", type=str, default=None)
    p.add_argument("--recover-two-stars", action="store_true")
    p.add_argument("--ack-current-chat-open", action="store_true")
    args = p.parse_args(argv)
    host = hostname or socket.gethostname()
    if args.expect_host.casefold() != host.casefold():
        return 1, {"schema": SCHEMA, "status": "wrong_host", "gameInputSent": False}
    if args.execute != args.ack_native_chat:
        return 1, {"schema": SCHEMA, "status": "execute_requires_ack",
                   "gameInputSent": False}
    if (args.recover_two_stars != args.ack_current_chat_open or
        (args.recover_two_stars and (args.action != "reload" or not args.execute))):
        return 1, {"schema": SCHEMA, "status": "recovery_requires_exact_ack_and_reload",
                   "gameInputSent": False}
    if args.execute and args.action=="log-toggle" and not args.ack_log_toggle:
        return 1, {"schema": SCHEMA, "status": "log_toggle_requires_explicit_ack",
                   "gameInputSent": False}
    if args.ack_log_toggle and args.action!="log-toggle":
        return 1, {"schema": SCHEMA, "status": "unexpected_log_toggle_ack",
                   "gameInputSent": False}
    if args.execute and args.action=="say-canary" and not args.ack_public_say:
        return 1, {"schema": SCHEMA, "status": "public_canary_requires_explicit_ack",
                   "gameInputSent": False}
    if args.ack_public_say and args.action!="say-canary":
        return 1, {"schema": SCHEMA, "status": "unexpected_public_chat_ack",
                   "gameInputSent": False}
    token=args.chat_canary
    if args.action=="say-canary":
        if not isinstance(token,str) or not re.fullmatch(r"RCM_[A-Z0-9_]{8,64}",token):
            return 1, {"schema": SCHEMA, "status": "invalid_public_chat_canary",
                       "gameInputSent": False}
    elif token is not None:
        return 1, {"schema": SCHEMA, "status": "unexpected_canary_argument",
                   "gameInputSent": False}
    if args.pid is not None and args.pid < 1:
        return 1, {"schema": SCHEMA, "status": "invalid_pid", "gameInputSent": False}
    command = "/say "+token if args.action=="say-canary" else COMMANDS[args.action]
    try:
        ident = (inspection or focused._inspect)(args.pid)
        focused.screenshot._pin_from_inspection(ident, host)
        if args.pid is not None and ident["pid"] != args.pid:
            raise RuntimeError("pid_mismatch")
    except Exception as exc:
        return 2, {"schema": SCHEMA, "status": "identity_refused_before_input",
                   "reason": str(exc), "gameInputSent": False}
    if args.dry_run:
        return 0, {"schema": SCHEMA, "status": "verified_dry_run",
                   "pid": ident["pid"], "hwnd": ident["hwnd"],
                   "action": args.action, "gameInputSent": False}

    try:
        focus = backend or focused._focus_backend()
        plan = _input_plan(command, args.recover_two_stars)
        check_modifiers = modifiers or _modifier_guard
        check_modifiers()
    except Exception as exc:
        return 2, {"schema": SCHEMA, "status": "input_plan_refused",
                   "reason": str(exc), "gameInputSent": False}
    target = {"pid": ident["pid"], "hwnd": ident["hwnd"], "title": "RIFT"}
    previous = None
    hwnd = None
    events = 0
    attempted_down = False
    began_focus = False
    before_iconic = False
    receipt = {"schema": SCHEMA, "status": "not_attempted",
               "action": args.action, "pid": ident["pid"],
               "hwnd": ident["hwnd"], "keyEventsInserted": 0,
               "gameInputSent": False, "inGameCommandVerified": False,
               "restoredPreviousForeground": False}
    result_code = 2
    try:
        hwnd, pid = focus._validate_target(target)
        before_iconic = bool(focus.is_iconic(hwnd))
        previous = int(focus.get_foreground() or 0)
        began_focus = True  # restoration also required if _focus itself raises
        focus._focus(hwnd, pid, 1250 if before_iconic else 250)
        for index, (kind, value) in enumerate(plan):
            focus._assert_exact_foreground(target, hwnd, pid)
            check_modifiers()
            attempted_down = True
            try:
                focus._insert(_keyboard_event(kind, value, release=False))
                events += 1
            finally:
                if attempted_down:
                    # Release key only when the exact game remains foreground.
                    focus._assert_exact_foreground(target, hwnd, pid)
                    focus._insert(_keyboard_event(kind, value, release=True))
                    events += 1
                    attempted_down = False
            # A rendered chat input may need a frame to acquire focus after
            # the opening Enter. Never race a new command against focus.
            time.sleep(0.14 if index == 0 and not args.recover_two_stars else 0.008)
        receipt["keyEventsInserted"] = events
        receipt["gameInputSent"] = events > 0
        receipt["status"] = "windows_keys_inserted_game_consumption_unverified"
        result_code = 0
    except Exception as exc:
        receipt["reason"] = str(exc)
        receipt["status"] = "partial_or_refused_no_retry" if attempted_down or events else "refused_before_input"
        receipt["keyEventsInserted"] = events
        receipt["gameInputSent"] = None if attempted_down else events > 0
    finally:
        if began_focus and focus and hwnd is not None:
            try:
                current = int(focus.get_foreground() or 0)
                if previous == hwnd:
                    receipt["restoredPreviousForeground"] = current == hwnd
                elif previous and current == hwnd and focus.is_window(previous):
                    focus._restore(previous, hwnd)
                    restored, observed, reason = focused._observe_foreground_restore(
                        focus.get_foreground, previous, hwnd)
                    if not restored and observed == hwnd:
                        tid, owner = focus._owner(previous)
                        if tid and owner:
                            try:
                                focus._focus(previous, owner, 250)
                            except RuntimeError:
                                pass
                            restored, observed, reason = focused._observe_foreground_restore(
                                focus.get_foreground, previous, hwnd)
                    receipt["restoredPreviousForeground"] = restored
                    receipt["restoreObservation"] = reason
                elif previous and current != hwnd:
                    restored, observed, reason = focused._observe_foreground_restore(
                        focus.get_foreground, previous, hwnd)
                    receipt["restoredPreviousForeground"] = restored
                    receipt["restoreObservation"] = reason
                    receipt["externalFocusChangePreserved"] = reason == "external"
                # Restore the original minimized state only after focus has
                # left RIFT; avoid minimizing an active user-owned window.
                if (before_iconic and previous != hwnd and
                    int(focus.get_foreground() or 0) != hwnd and
                    focus.is_window(hwnd)):
                    focus.show_window(hwnd, SW_MINIMIZE)
                    receipt["minimizedStateRestored"] = bool(focus.is_iconic(hwnd))
            except Exception as exc:
                receipt["restoreError"] = str(exc)
    return result_code, receipt


def main(argv=None):
    code, result = run(argv)
    print(json.dumps(result, indent=2))
    return code


if __name__ == "__main__":
    sys.exit(main())
