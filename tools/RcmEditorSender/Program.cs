// Dedicated opt-in RCM import *typing* helper for an already focused RIFT
// RiftTextfield. Not a background service, not an addon-message receiver.
// Uses the shared pure validator from the READ-ONLY RcmEditorInput project.
using System.Diagnostics;
using System.Globalization;
using System.Runtime.InteropServices;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using System.Text.RegularExpressions;
using System.Threading;

internal static class Program
{
    private const uint InputKeyboard = 1;
    private const uint UnicodeFlag = 0x0004;
    private const uint KeyUpFlag = 0x0002;
    private const ushort VkReturn = 0x0D;
    private const uint RootAncestor = 2;
    private const int ExitNoInput = 2;
    private static bool keyCallAttempted;
    private static int insertedChars;
    private static int insertedEvents;
    private static bool submitAttempted;

    private static int Main(string[] args)
    {
        RcmImport? transfer = null;
        try
        {
            var o = Parse(args);
            if (o.ContainsKey("self-test"))
            {
                if (o.Count != 1) throw new ArgumentException("--self-test takes no extra options.");
                return SelfTest();
            }
            if (o.ContainsKey("help"))
            {
                if (o.Count != 1) throw new ArgumentException("--help takes no extra options.");
                Console.WriteLine("RCM editor transfer sender. Default: validate only, NO input.");
                Console.WriteLine("--command TEXT OR --stdin-command (exactly one :import line)");
                Console.WriteLine("To type: --send --ack-editor-focused plus all six pinned target options:");
                Console.WriteLine("  --expect-host HOST --pid PID --hwnd 0xHEX --start-ticks UTC_TICKS");
                Console.WriteLine("  --exe-path PATH --exe-sha256 SHA256");
                Console.WriteLine("Optional submission: --submit --ack-submit");
                Console.WriteLine("Never activates RIFT, never touches clipboard or game memory.");
                Console.WriteLine("Windows key insertion != verified game receipt or disk persistence.");
                return 0;
            }
            bool fromStdin = o.ContainsKey("stdin-command");
            bool fromArgv = o.ContainsKey("command");
            if (fromStdin == fromArgv)
                throw new ArgumentException("Supply exactly one --command or --stdin-command.");
            string command = fromStdin
                ? RcmImportContract.ReadOne(Console.In)
                : Required(o, "command");
            transfer = RcmImportContract.Parse(command);
            bool send = o.ContainsKey("send");
            bool ackFocus = o.ContainsKey("ack-editor-focused");
            bool submit = o.ContainsKey("submit");
            bool ackSubmit = o.ContainsKey("ack-submit");
            if (!send)
            {
                if (o.Count != 1 || ackFocus || submit || ackSubmit)
                    throw new ArgumentException("Read-only plan accepts only a command; --send is explicit.");
                Emit(new {
                    schema = "RCM_EDITOR_SEND_V1", status = "validated_no_input",
                    machine = Environment.MachineName,
                    chars = transfer.Chars, sha256 = transfer.Sha256,
                    part = transfer.Part, total = transfer.Total,
                    gameInputSent = false, editorFocusMachineVerified = false,
                    addonAcceptedVerified = false, diskSavedVerified = false,
                    clipboardChanged = false, gameFocusChanged = false
                });
                return 0;
            }

            if (!ackFocus)
                throw new ArgumentException("--send requires --ack-editor-focused (manual assertion).");
            if (submit != ackSubmit)
                throw new ArgumentException("--submit and --ack-submit must be requested together.");
            if (o.Count != 9 + (submit ? 2 : 0))
                throw new ArgumentException("Send requires exact six game identity pins, one input, --send and --ack-editor-focused.");
            Pin target = ParsePin(o);
            // One initial full executable hash, then cheap epoch/foreground
            // checks before each key pair. No focus changes or clipboard.
            RequireTarget(target, hashExecutable: true);
            for (int i = 0; i < command.Length; i++)
            {
                RequireTarget(target, hashExecutable: false);
                RequireNoModifiers();
                WinInput[] pair = UnicodePair(command[i]);
                InsertPair(pair, target);
                insertedChars++;
                // Allow RIFT's RiftTextfield time to process WM_CHAR/VK_PACKET.
                Thread.Sleep(3);
            }

            if (submit)
            {
                RequireTarget(target, hashExecutable: false);
                RequireNoModifiers();
                submitAttempted = true;
                InsertPair(VirtualKeyPair(VkReturn), target);
            }
            Emit(new {
                schema = "RCM_EDITOR_SEND_V1",
                status = submit
                    ? "windows_text_and_enter_inserted_game_receipt_unverified"
                    : "windows_text_inserted_draft_unverified",
                machine = Environment.MachineName, pid = target.Pid,
                hwnd = $"0x{target.Hwnd.ToInt64():X}",
                sha256 = transfer.Sha256, part = transfer.Part, total = transfer.Total,
                charsRequested = command.Length, charsInserted = insertedChars,
                keyEventsInserted = insertedEvents, enterAttempted = submitAttempted,
                operatorAttestedEditorFocus = ackFocus,
                editorFocusMachineVerified = false, addonAcceptedVerified = false,
                diskSavedVerified = false, nativePlayerChatVerified = false,
                gameInputSent = insertedEvents > 0,
                gameFocusChanged = false, clipboardChanged = false,
                nextStep = "Check RCM in-game import receipt/history #ID, then save and independently audit disk."
            });
            return 0;
        }
        catch (Exception e)
        {
            Emit(new {
                schema = "RCM_EDITOR_SEND_V1",
                status = keyCallAttempted ? "partial_or_unknown_input_no_retry" : "refused_before_input",
                error = e.GetType().Name, detail = e.Message,
                sha256 = transfer?.Sha256, charsInserted = insertedChars,
                keyEventsInserted = insertedEvents, enterAttempted = submitAttempted,
                gameInputSent = keyCallAttempted ? (bool?)null : false,
                editorFocusMachineVerified = false, addonAcceptedVerified = false,
                diskSavedVerified = false, gameFocusChanged = false,
                clipboardChanged = false,
                nextStep = "Inspect RCM editor draft in the actual game; do not automatically retry."
            });
            return keyCallAttempted ? ExitNoInput : 1;
        }
    }

    private static void Emit(object o) => Console.WriteLine(JsonSerializer.Serialize(o));

    private static Dictionary<string, string> Parse(string[] args)
    {
        var switches = new HashSet<string>(StringComparer.Ordinal) {
            "self-test", "help", "stdin-command", "send", "ack-editor-focused",
            "submit", "ack-submit" };
        var valued = new HashSet<string>(StringComparer.Ordinal) {
            "command", "expect-host", "pid", "hwnd", "start-ticks",
            "exe-path", "exe-sha256" };
        var o = new Dictionary<string, string>(StringComparer.Ordinal);
        for (int i = 0; i < args.Length; i++)
        {
            if (!args[i].StartsWith("--", StringComparison.Ordinal))
                throw new ArgumentException("Positional input is forbidden.");
            string key = args[i][2..];
            if (!switches.Contains(key) && !valued.Contains(key))
                throw new ArgumentException($"Unsupported option --{key}.");
            if (o.ContainsKey(key))
                throw new ArgumentException($"Duplicate option --{key}.");
            if (switches.Contains(key)) o.Add(key, "true");
            else
            {
                if (i + 1 >= args.Length || string.IsNullOrEmpty(args[i + 1]) ||
                    args[i + 1].StartsWith("--", StringComparison.Ordinal))
                    throw new ArgumentException($"Missing value for --{key}.");
                o.Add(key, args[++i]);
            }
        }
        return o;
    }

    private static string Required(Dictionary<string, string> o, string key)
        => o.TryGetValue(key, out var v) && v.Length > 0
            ? v : throw new ArgumentException($"Missing --{key}.");

    private sealed record Pin(int Pid, nint Hwnd, long StartUtcTicks,
                              string ExePath, string ExeHash);

    private static Pin ParsePin(Dictionary<string, string> o)
    {
        if (!string.Equals(Required(o, "expect-host"), Environment.MachineName,
                StringComparison.OrdinalIgnoreCase))
            throw new ArgumentException("Target host identity does not match.");
        if (!int.TryParse(Required(o, "pid"), NumberStyles.None,
                CultureInfo.InvariantCulture, out int pid) || pid <= 0)
            throw new ArgumentException("Invalid RIFT PID.");
        string handle = Required(o, "hwnd");
        if (!Regex.IsMatch(handle, @"\A0x[0-9a-fA-F]{1,12}\z"))
            throw new ArgumentException("Expected 0x-prefixed RIFT HWND.");
        nint hwnd = (nint)Convert.ToInt64(handle[2..], 16);
        if (hwnd == nint.Zero) throw new ArgumentException("Cannot bind null HWND.");
        if (!long.TryParse(Required(o, "start-ticks"), NumberStyles.None,
                CultureInfo.InvariantCulture, out long ticks) || ticks <= 621355968000000000L)
            throw new ArgumentException("Invalid RIFT process start ticks.");
        string exe = Path.GetFullPath(Required(o, "exe-path"));
        string sha = Required(o, "exe-sha256").ToUpperInvariant();
        if (!Regex.IsMatch(sha, @"\A[0-9A-F]{64}\z"))
            throw new ArgumentException("Expected exactly one SHA-256 digest.");
        return new Pin(pid, hwnd, ticks, exe, sha);
    }

    private static void RequireTarget(Pin pin, bool hashExecutable)
    {
        if (!OperatingSystem.IsWindows())
            throw new PlatformNotSupportedException("Windows only.");
        if (GetForegroundWindow() != pin.Hwnd || !IsWindow(pin.Hwnd) ||
            !IsWindowVisible(pin.Hwnd) || IsIconic(pin.Hwnd) ||
            GetAncestor(pin.Hwnd, RootAncestor) != pin.Hwnd)
            throw new InvalidOperationException("Pinned RIFT HWND is not foreground, visible and root.");
        uint thread = GetWindowThreadProcessId(pin.Hwnd, out uint owner);
        if (thread == 0 || owner != (uint)pin.Pid)
            throw new InvalidOperationException("Window is no longer owned by the pinned game process.");

        using var game = Process.GetProcessById(pin.Pid);
        game.Refresh();
        if (game.HasExited || game.ProcessName != "rift_x64" ||
            game.StartTime.ToUniversalTime().Ticks != pin.StartUtcTicks ||
            game.MainWindowHandle != pin.Hwnd ||
            game.SessionId != Process.GetCurrentProcess().SessionId)
            throw new InvalidOperationException("RIFT process epoch, main HWND or desktop session changed.");
        var cls = new StringBuilder(128);
        var title = new StringBuilder(128);
        _ = GetClassNameW(pin.Hwnd, cls, cls.Capacity);
        _ = GetWindowTextW(pin.Hwnd, title, title.Capacity);
        if (cls.ToString() != "TWNClientFramework" || title.ToString() != "RIFT")
            throw new InvalidOperationException("Unexpected foreground window class/title.");
        string exe = Path.GetFullPath(game.MainModule?.FileName ??
            throw new InvalidOperationException("Unable to inspect game executable."));
        if (!string.Equals(exe, pin.ExePath, StringComparison.OrdinalIgnoreCase))
            throw new InvalidOperationException("RIFT executable pathname changed.");
        if (hashExecutable)
        {
            using var stream = File.OpenRead(exe);
            var digest = Convert.ToHexString(SHA256.HashData(stream));
            if (!string.Equals(digest, pin.ExeHash, StringComparison.Ordinal))
                throw new InvalidOperationException("Pinned RIFT build hash mismatched.");
        }
    }

    private static void RequireNoModifiers()
    {
        // Avoid ctrl/alt/shift/global shortcuts instead of unknowingly
        // directing keys to the wrong app or invoking RIFT keybindings.
        foreach (int vk in new[] { 0x10, 0x11, 0x12, 0x5B, 0x5C })
            if ((GetAsyncKeyState(vk) & 0x8000) != 0)
                throw new InvalidOperationException("Modifier key held; input aborted.");
    }

    private static WinInput[] UnicodePair(char character) =>
    [
        new WinInput { Type = InputKeyboard, Data = new InputUnion {
            Key = new KeyInput { Scan = character, Flags = UnicodeFlag } } },
        new WinInput { Type = InputKeyboard, Data = new InputUnion {
            Key = new KeyInput { Scan = character, Flags = UnicodeFlag | KeyUpFlag } } }
    ];

    private static WinInput[] VirtualKeyPair(ushort vk) =>
    [
        new WinInput { Type = InputKeyboard, Data = new InputUnion {
            Key = new KeyInput { Vk = vk } } },
        new WinInput { Type = InputKeyboard, Data = new InputUnion {
            Key = new KeyInput { Vk = vk, Flags = KeyUpFlag } } }
    ];

    private static void InsertPair(WinInput[] pair, Pin pin)
    {
        keyCallAttempted = true;
        uint inserted = SendInput(2, pair, Marshal.SizeOf<WinInput>());
        insertedEvents += (int)inserted;
        if (inserted == 2) return;
        if (inserted == 1 && GetForegroundWindow() == pin.Hwnd &&
            GetWindowThreadProcessId(pin.Hwnd, out uint owner) != 0 &&
            owner == (uint)pin.Pid)
        {
            // One key-up only. Never repeat a partial key-down, never auto-resubmit.
            uint released = SendInput(1, new[] { pair[1] }, Marshal.SizeOf<WinInput>());
            insertedEvents += (int)released;
        }
        throw new InvalidOperationException("Partial Windows input; editor draft may be incomplete.");
    }

    private static int SelfTest()
    {
        int count = 0;
        void Check(bool yes) { if (!yes) throw new InvalidOperationException("self-test #" + (count + 1)); count++; }
        var x = RcmImportContract.Parse(":import ABCDEF123456 1/1 QUJDRA");
        Check(x.Part == 1 && x.Total == 1 && x.Chars == 31);
        Check(x.Sha256.Length == 64);
        foreach (var bad in new[] {
            ":import ABCDEF123456 2/1 AAA",
            "/rcm import ABCDEF123456 1/1 AAA",
            ":import abcdef123456 1/1 AAA",
            ":import ABCDEF123456 1/1 AAA\n"})
        {
            bool rejected = false;
            try { _ = RcmImportContract.Parse(bad); }
            catch (ArgumentException) { rejected = true; }
            Check(rejected);
        }
        Check(RcmImportContract.ReadOne(new StringReader(":import ABCDEF123456 1/1 AAA\n"))
            == ":import ABCDEF123456 1/1 AAA");
        var chars = UnicodePair(':');
        Check(chars.Length == 2 && chars[0].Data.Key.Scan == ':' &&
            chars[0].Data.Key.Flags == UnicodeFlag &&
            chars[1].Data.Key.Flags == (UnicodeFlag | KeyUpFlag));
        var enter = VirtualKeyPair(VkReturn);
        Check(enter[0].Data.Key.Vk == VkReturn && enter[1].Data.Key.Flags == KeyUpFlag);
        Check(Marshal.SizeOf<WinInput>() == (IntPtr.Size == 8 ? 40 : 28));
        Check(!Parse(["--command", "X"]).ContainsKey("send"));
        bool duplicate = false;
        try { _ = Parse(["--send", "--send"]); } catch (ArgumentException) { duplicate = true; }
        Check(duplicate);
        Emit(new { schema = "RCM_EDITOR_SEND_V1", status = "self_tests_passed", checks = count,
                   gameInputSent = false, clipboardChanged = false });
        return 0;
    }

    [StructLayout(LayoutKind.Sequential)]
    private struct WinInput { public uint Type; public InputUnion Data; }

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
        public int X, Y; public uint MouseData, Flags, Time; public nuint ExtraInfo;
    }
    [StructLayout(LayoutKind.Sequential)]
    private struct KeyInput
    {
        public ushort Vk, Scan; public uint Flags, Time; public nuint ExtraInfo;
    }
    [StructLayout(LayoutKind.Sequential)]
    private struct HardwareInput { public uint Msg; public ushort ParamL, ParamH; }

    [DllImport("user32.dll", SetLastError = true)]
    private static extern uint SendInput(uint count, [In] WinInput[] inputs, int size);
    [DllImport("user32.dll")]
    private static extern nint GetForegroundWindow();
    [DllImport("user32.dll")]
    private static extern uint GetWindowThreadProcessId(nint hwnd, out uint owner);
    [DllImport("user32.dll")]
    private static extern nint GetAncestor(nint hwnd, uint flags);
    [DllImport("user32.dll")]
    [return: MarshalAs(UnmanagedType.Bool)]
    private static extern bool IsWindow(nint hwnd);
    [DllImport("user32.dll")]
    [return: MarshalAs(UnmanagedType.Bool)]
    private static extern bool IsWindowVisible(nint hwnd);
    [DllImport("user32.dll")]
    [return: MarshalAs(UnmanagedType.Bool)]
    private static extern bool IsIconic(nint hwnd);
    [DllImport("user32.dll", CharSet = CharSet.Unicode)]
    private static extern int GetClassNameW(nint hwnd, StringBuilder value, int length);
    [DllImport("user32.dll", CharSet = CharSet.Unicode)]
    private static extern int GetWindowTextW(nint hwnd, StringBuilder value, int length);
    [DllImport("user32.dll")]
    private static extern short GetAsyncKeyState(int vk);
}
