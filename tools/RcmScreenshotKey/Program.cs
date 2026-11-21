// RCM screenshot key trigger. This is intentionally separate from the
// read-only RcmEditorInput preflight: the only permitted synthetic input is
// one Numpad Multiply key-down and one key-up for an exact foreground RIFT HWND.
using System.Diagnostics;
using System.Globalization;
using System.Runtime.InteropServices;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using System.Text.RegularExpressions;

internal static class Program
{
    private const uint InputKeyboard = 1;
    private const ushort VkMultiply = 0x6A;
    private const uint KeyUp = 0x0002;
    private const uint RootAncestor = 2;
    private const long UnixEpochTicks = 621355968000000000L;
    private const int Inconclusive = 2;

    private static int Main(string[] args)
    {
        // If an exception occurs AFTER the native call begins, input delivery
        // is unknown; never report "nothing was sent" for that situation.
        bool keyCallAttempted = false;
        try
        {
            var options = Parse(args);
            if (options.ContainsKey("self-test"))
            {
                Only(options, "self-test");
                return SelfTest();
            }
            if (options.ContainsKey("help"))
            {
                Only(options, "help");
                Console.WriteLine("RCM RIFT in-game screenshot trigger; default is read-only.");
                Console.WriteLine("--inspect [--pid PID]           inspect exact RIFT window identity without input");
                Console.WriteLine("--dry-run TARGET_FLAGS         verify pinned RIFT target, send NO input");
                Console.WriteLine("--capture --ack-single-screenshot TARGET_FLAGS");
                Console.WriteLine("TARGET_FLAGS:");
                Console.WriteLine("  --expect-host HOST --pid PID --hwnd 0xHANDLE --start-ticks UTC_TICKS");
                Console.WriteLine("  --exe-path PATH --exe-sha256 SHA256");
                Console.WriteLine("The capture mode sends ONLY one VK_MULTIPLY down/up pair to an already");
                Console.WriteLine("foreground RIFT HWND. It never focuses a window or checks the game's JPG.");
                return 0;
            }
            if (options.ContainsKey("inspect"))
            {
                if (options.Count != 1 && !(options.Count == 2 && options.ContainsKey("pid")))
                    throw new ArgumentException("--inspect accepts only optional --pid.");
                return Inspect(options);
            }
            bool capture = options.ContainsKey("capture");
            if (!capture && !options.ContainsKey("dry-run"))
                throw new ArgumentException("Use --inspect, --dry-run or explicit --capture.");
            if (options.ContainsKey("dry-run") && capture)
                throw new ArgumentException("Cannot request both capture and dry-run.");
            if (capture != options.ContainsKey("ack-single-screenshot"))
                throw new ArgumentException("Capture requires --ack-single-screenshot; it is forbidden for dry-run.");
            int wantedCount = capture ? 8 : 7; // six pin values plus capture+ack or dry-run
            if (options.Count != wantedCount)
                throw new ArgumentException("Exactly six target identity arguments are required.");
            Target target = TargetFromOptions(options);
            var state = InspectTarget(target, mustBeForeground: false);
            if (state.Status != "exact_target_matched")
            {
                Emit(new
                {
                    schema = "RCM_GAME_SCREENSHOT_TRIGGER_V1",
                    status = "refused_before_keypress",
                    reason = state.Status,
                    gameInputSent = false,
                    screenshotFileVerified = false,
                    gameFocusChanged = false
                });
                return Inconclusive;
            }
            if (!state.Foreground)
            {
                Emit(new
                {
                    schema = "RCM_GAME_SCREENSHOT_TRIGGER_V1",
                    status = "game_not_foreground_no_input",
                    pid = target.Pid,
                    hwnd = $"0x{target.Hwnd.ToInt64():X}",
                    gameInputSent = false,
                    screenshotFileVerified = false,
                    gameFocusChanged = false
                });
                return Inconclusive;
            }
            if (!capture)
            {
                Emit(new
                {
                    schema = "RCM_GAME_SCREENSHOT_TRIGGER_V1",
                    status = "ready_no_input",
                    machine = Environment.MachineName,
                    pid = target.Pid,
                    hwnd = $"0x{target.Hwnd.ToInt64():X}",
                    scanCode = "VK_MULTIPLY",
                    screenshotFileVerified = false,
                    gameInputSent = false,
                    gameFocusChanged = false
                });
                return 0;
            }

            // Do not change focus or select an app. In particular, keyboard
            // modifiers may alter in-game interpretation of Numpad Multiply.
            RejectModifierKeys();
            state = InspectTarget(target, mustBeForeground: true);
            if (state.Status != "exact_target_matched" || !state.Foreground)
                throw new InvalidOperationException("Target changed before input; no key sent.");
            long before = (DateTime.UtcNow.Ticks - UnixEpochTicks) * 100;
            WinInput[] pair = MakeMultiplyPair();
            keyCallAttempted = true;
            uint inserted = SendInput(2, pair, Marshal.SizeOf<WinInput>());
            // The two events are inserted as a single atomic SendInput batch.
            // Never automatically retry a partial batch (double-capture risk).
            Emit(new
            {
                schema = "RCM_GAME_SCREENSHOT_TRIGGER_V1",
                status = inserted == 2 ? "windows_key_events_inserted" : "partial_or_blocked_input",
                machine = Environment.MachineName,
                pid = target.Pid,
                hwnd = $"0x{target.Hwnd.ToInt64():X}",
                baselineEpochNs = before,
                key = "VK_MULTIPLY",
                keyEventsRequested = 2,
                keyEventsInserted = inserted,
                gameInputSent = inserted > 0,
                gameFocusChanged = false,
                screenshotFileVerified = false,
                screenshotKeyHandledByGameVerified = false,
                nextStep = "Independently run rcm_game_screenshot_receipt.py --after-ns BASELINE --require-new"
            });
            return inserted == 2 ? 0 : Inconclusive;
        }
        catch (Exception exc)
        {
            Emit(new
            {
                schema = "RCM_GAME_SCREENSHOT_TRIGGER_V1",
                status = "refused",
                reason = exc.GetType().Name,
                detail = exc.Message,
                screenshotFileVerified = false,
                keyCallAttempted,
                // An exception after SendInput started does not prove that
                // Windows accepted zero events. Preserve the uncertainty.
                gameInputSent = keyCallAttempted ? (bool?)null : false
            });
            return 1;
        }
    }

    private readonly record struct Target(
        int Pid, nint Hwnd, long StartTicks, string ExePath, string ExeSha256);
    private readonly record struct TargetState(string Status, bool Foreground);

    private static Target TargetFromOptions(Dictionary<string, string> o)
    {
        if (!string.Equals(Required(o, "expect-host"), Environment.MachineName,
                StringComparison.OrdinalIgnoreCase))
            throw new ArgumentException("Wrong expected computer.");
        if (!int.TryParse(Required(o, "pid"), NumberStyles.None,
                CultureInfo.InvariantCulture, out int pid) || pid < 1)
            throw new ArgumentException("PID must be a positive decimal integer.");
        string rawHwnd = Required(o, "hwnd");
        if (!Regex.IsMatch(rawHwnd, @"\A0x[0-9A-Fa-f]{1,12}\z"))
            throw new ArgumentException("HWND must be a bounded 0x-prefixed hex string.");
        var hwndValue = Convert.ToInt64(rawHwnd[2..], 16);
        if (hwndValue <= 0) throw new ArgumentException("Null HWND is not allowed.");
        if (!long.TryParse(Required(o, "start-ticks"), NumberStyles.None,
                CultureInfo.InvariantCulture, out long ticks) || ticks < UnixEpochTicks)
            throw new ArgumentException("Invalid UTC process-start ticks.");
        string exe = Path.GetFullPath(Required(o, "exe-path"));
        string sha = Required(o, "exe-sha256").ToUpperInvariant();
        if (!Regex.IsMatch(sha, @"\A[0-9A-F]{64}\z"))
            throw new ArgumentException("Expected 64 hexadecimal SHA-256 characters.");
        return new Target(pid, (nint)hwndValue, ticks, exe, sha);
    }

    private static TargetState InspectTarget(Target target, bool mustBeForeground)
    {
        if (!OperatingSystem.IsWindows()) return new TargetState("requires_windows", false);
        if (!IsWindow(target.Hwnd) || !IsWindowVisible(target.Hwnd) ||
            IsIconic(target.Hwnd) || GetAncestor(target.Hwnd, RootAncestor) != target.Hwnd)
            return new TargetState("window_missing_or_hidden", false);
        if (GetWindowThreadProcessId(target.Hwnd, out uint ownerPid) == 0 ||
            ownerPid != (uint)target.Pid)
            return new TargetState("window_pid_mismatch", false);

        using var process = Process.GetProcessById(target.Pid);
        process.Refresh();
        if (process.HasExited || process.ProcessName != "rift_x64")
            return new TargetState("not_rift_x64", false);
        if (process.StartTime.ToUniversalTime().Ticks != target.StartTicks)
            return new TargetState("process_start_changed", false);
        if (process.SessionId != Process.GetCurrentProcess().SessionId)
            return new TargetState("different_windows_session", false);
        if (process.MainWindowHandle != target.Hwnd)
            return new TargetState("window_handle_changed", false);
        string actualPath = Path.GetFullPath(process.MainModule?.FileName ??
            throw new InvalidOperationException("Cannot inspect RIFT executable path."));
        if (!string.Equals(actualPath, target.ExePath, StringComparison.OrdinalIgnoreCase))
            return new TargetState("executable_path_mismatch", false);

        string currentSha;
        using (var stream = File.OpenRead(actualPath))
            currentSha = Convert.ToHexString(SHA256.HashData(stream));
        if (!string.Equals(currentSha, target.ExeSha256, StringComparison.Ordinal))
            return new TargetState("executable_sha_mismatch", false);
        var name = new StringBuilder(128);
        var klass = new StringBuilder(128);
        _ = GetWindowTextW(target.Hwnd, name, name.Capacity);
        _ = GetClassNameW(target.Hwnd, klass, klass.Capacity);
        if (name.ToString() != "RIFT" || klass.ToString() != "TWNClientFramework")
            return new TargetState("rift_window_title_or_class_mismatch", false);
        bool foreground = GetForegroundWindow() == target.Hwnd;
        if (mustBeForeground && !foreground)
            return new TargetState("rift_window_not_foreground", false);
        return new TargetState("exact_target_matched", foreground);
    }

    private static int Inspect(Dictionary<string, string> o)
    {
        if (!OperatingSystem.IsWindows()) return Inconclusive;
        using var processes = new ProcessGroup(Process.GetProcessesByName("rift_x64"));
        var matched = processes.Items;
        if (o.TryGetValue("pid", out string? pidText))
        {
            if (!int.TryParse(pidText, out int pid) || pid < 1)
                throw new ArgumentException("Invalid inspection PID.");
            matched = matched.Where(x => x.Id == pid).ToArray();
        }
        if (matched.Length != 1)
        {
            Emit(new
            {
                schema = "RCM_GAME_SCREENSHOT_TRIGGER_V1",
                status = matched.Length == 0 ? "game_process_absent" : "multiple_rift_processes_require_pid",
                count = matched.Length,
                gameInputSent = false
            });
            return Inconclusive;
        }
        var p = matched[0];
        p.Refresh();
        var hwnd = p.MainWindowHandle;
        string path = Path.GetFullPath(p.MainModule?.FileName ??
            throw new InvalidOperationException("RIFT executable path unavailable."));
        string sha;
        using (var stream = File.OpenRead(path))
            sha = Convert.ToHexString(SHA256.HashData(stream));
        var title = new StringBuilder(128);
        var klass = new StringBuilder(128);
        _ = GetWindowTextW(hwnd, title, title.Capacity);
        _ = GetClassNameW(hwnd, klass, klass.Capacity);
        bool exactWindow = IsWindow(hwnd) &&
            GetWindowThreadProcessId(hwnd, out uint actualPid) != 0 &&
            actualPid == (uint)p.Id && title.ToString() == "RIFT" &&
            klass.ToString() == "TWNClientFramework";
        Emit(new
        {
            schema = "RCM_GAME_SCREENSHOT_TRIGGER_V1",
            status = exactWindow ? "read_only_target_candidate" : "window_unverified",
            machine = Environment.MachineName,
            pid = p.Id,
            hwnd = $"0x{hwnd.ToInt64():X}",
            startUtcTicks = p.StartTime.ToUniversalTime().Ticks,
            exePath = path,
            exeSha256 = sha,
            windowTitle = title.ToString(),
            windowClass = klass.ToString(),
            foreground = GetForegroundWindow() == hwnd,
            gameInputSent = false,
            screenshotFileVerified = false
        });
        return exactWindow ? 0 : Inconclusive;
    }

    private sealed class ProcessGroup(Process[] items) : IDisposable
    {
        public Process[] Items { get; } = items;
        public void Dispose()
        {
            foreach (var item in Items) item.Dispose();
        }
    }

    private static void RejectModifierKeys()
    {
        foreach (int vk in new[] { 0x10, 0x11, 0x12, 0x5B, 0x5C })
            if ((GetAsyncKeyState(vk) & 0x8000) != 0)
                throw new InvalidOperationException("Modifier key currently held; no screenshot key sent.");
    }

    private static WinInput[] MakeMultiplyPair()
    {
        var down = new WinInput
        {
            Type = InputKeyboard,
            Data = new InputUnion { Key = new KeyInput { Vk = VkMultiply } }
        };
        var up = new WinInput
        {
            Type = InputKeyboard,
            Data = new InputUnion { Key = new KeyInput { Vk = VkMultiply, Flags = KeyUp } }
        };
        return [down, up];
    }

    private static Dictionary<string, string> Parse(string[] args)
    {
        var flags = new HashSet<string>(StringComparer.Ordinal)
            { "inspect", "dry-run", "capture", "ack-single-screenshot", "self-test", "help" };
        var values = new HashSet<string>(StringComparer.Ordinal)
            { "expect-host", "pid", "hwnd", "start-ticks", "exe-path", "exe-sha256" };
        var o = new Dictionary<string, string>(StringComparer.Ordinal);
        for (int i = 0; i < args.Length; ++i)
        {
            if (!args[i].StartsWith("--", StringComparison.Ordinal))
                throw new ArgumentException("Positional commands are unsupported.");
            string name = args[i][2..];
            if (!flags.Contains(name) && !values.Contains(name))
                throw new ArgumentException($"Unknown option --{name}.");
            if (o.ContainsKey(name))
                throw new ArgumentException($"Duplicate option --{name}.");
            if (flags.Contains(name)) o[name] = "true";
            else
            {
                if (i + 1 >= args.Length || args[i + 1].StartsWith("--", StringComparison.Ordinal))
                    throw new ArgumentException($"Missing value for --{name}.");
                o[name] = args[++i];
            }
        }
        return o;
    }

    private static string Required(Dictionary<string, string> values, string key) =>
        values.TryGetValue(key, out string? value) && value.Length > 0
            ? value : throw new ArgumentException($"Missing --{key}.");
    private static void Only(Dictionary<string, string> o, string key)
    {
        if (o.Count != 1 || !o.ContainsKey(key))
            throw new ArgumentException($"--{key} cannot be combined with other options.");
    }
    private static void Emit(object value) =>
        Console.WriteLine(JsonSerializer.Serialize(value));

    private static int SelfTest()
    {
        int tests = 0;
        void Check(bool ok)
        {
            if (!ok) throw new InvalidOperationException($"Self-test assertion {tests + 1} failed.");
            ++tests;
        }
        var pair = MakeMultiplyPair();
        Check(pair.Length == 2);
        Check(pair[0].Type == InputKeyboard && pair[1].Type == InputKeyboard);
        Check(pair[0].Data.Key.Vk == VkMultiply && pair[0].Data.Key.Flags == 0);
        Check(pair[1].Data.Key.Vk == VkMultiply && pair[1].Data.Key.Flags == KeyUp);
        Check(Marshal.SizeOf<WinInput>() == (IntPtr.Size == 8 ? 40 : 28));
        Check(Parse(["--inspect"]).ContainsKey("inspect"));
        Check(Parse(["--dry-run"]).ContainsKey("dry-run"));
        Check(Parse(["--capture", "--ack-single-screenshot"]).Count == 2);
        foreach (var broken in new[]
        {
            new[] { "--capture", "--capture" },
            new[] { "--capture", "--arbitrary-key" },
            new[] { "a-positional-key" },
            new[] { "--expect-host" }
        })
        {
            bool refused = false;
            try { _ = Parse(broken); } catch (ArgumentException) { refused = true; }
            Check(refused);
        }
        Check(UnixEpochTicks == 621355968000000000L);
        Emit(new
        {
            schema = "RCM_GAME_SCREENSHOT_TRIGGER_V1",
            status = "self_tests_passed",
            assertions = tests,
            gameInputSent = false
        });
        return 0;
    }

    [StructLayout(LayoutKind.Sequential)]
    private struct WinInput
    {
        public uint Type;
        public InputUnion Data;
    }
    [StructLayout(LayoutKind.Explicit)]
    private struct InputUnion
    {
        [FieldOffset(0)] public MouseInput Mouse;
        [FieldOffset(0)] public KeyInput Key;
        [FieldOffset(0)] public HardwareInput Hardware;
    }
    [StructLayout(LayoutKind.Sequential)]
    private struct MouseInput
    {
        public int X, Y;
        public uint MouseData, Flags, Time;
        public nuint ExtraInfo;
    }
    [StructLayout(LayoutKind.Sequential)]
    private struct KeyInput
    {
        public ushort Vk, Scan;
        public uint Flags, Time;
        public nuint ExtraInfo;
    }
    [StructLayout(LayoutKind.Sequential)]
    private struct HardwareInput
    {
        public uint Msg;
        public ushort ParamL, ParamH;
    }

    [DllImport("user32.dll", SetLastError = true)]
    private static extern uint SendInput(uint count, [In] WinInput[] input, int cbSize);
    [DllImport("user32.dll")]
    private static extern nint GetForegroundWindow();
    [DllImport("user32.dll")]
    private static extern uint GetWindowThreadProcessId(nint hwnd, out uint ownerPid);
    [DllImport("user32.dll")]
    [return: MarshalAs(UnmanagedType.Bool)]
    private static extern bool IsWindow(nint hwnd);
    [DllImport("user32.dll")]
    [return: MarshalAs(UnmanagedType.Bool)]
    private static extern bool IsWindowVisible(nint hwnd);
    [DllImport("user32.dll")]
    [return: MarshalAs(UnmanagedType.Bool)]
    private static extern bool IsIconic(nint hwnd);
    [DllImport("user32.dll")]
    private static extern nint GetAncestor(nint hwnd, uint flag);
    [DllImport("user32.dll", CharSet = CharSet.Unicode)]
    private static extern int GetWindowTextW(nint hwnd, StringBuilder title, int capacity);
    [DllImport("user32.dll", CharSet = CharSet.Unicode)]
    private static extern int GetClassNameW(nint hwnd, StringBuilder className, int capacity);
    [DllImport("user32.dll")]
    private static extern short GetAsyncKeyState(int vk);
}
