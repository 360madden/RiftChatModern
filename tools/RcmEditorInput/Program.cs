using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using System.Text.RegularExpressions;

// RCM editor command preflight. Intentionally read-only:
// no input APIs, no focus changes, no clipboard, no game launch, no file writes.
internal static class Program
{
    // The input-free RcmImportContract is also used by the separately
    // permissioned editor sender. Keep one validation implementation.

    private static int Main(string[] arguments)
    {
        try
        {
            var options = Options(arguments);
            if (options.ContainsKey("self-test"))
            {
                RequireOnly(options,"self-test");
                return SelfTest();
            }
            if (options.ContainsKey("help"))
            {
                RequireOnly(options,"help");
                Console.WriteLine("RCM / .NET 10 read-only editor preflight");
                Console.WriteLine("--command \":import TOKEN I/N BASE64URL\" (validate and report digest only)");
                Console.WriteLine("--stdin-command (one bounded command through standard input)");
                Console.WriteLine("--inspect (read-only RIFT process identities)");
                Console.WriteLine("--verify-target --pid PID --hwnd 0xHEX --expect-start-ticks N");
                Console.WriteLine("  --expect-path PATH --expect-sha256 SHA256");
                Console.WriteLine("--self-test | --help");
                Console.WriteLine("This utility NEVER types, pastes, focuses, or submits a game command.");
                return 0;
            }
            if (options.ContainsKey("inspect"))
            {
                RequireOnly(options, "inspect");
                return Inspect();
            }
            if (options.ContainsKey("verify-target"))
            {
                if (options.ContainsKey("command") || options.ContainsKey("stdin-command"))
                    throw new ArgumentException("Target inspection must not include an encoded chat command.");
                return VerifyTarget(options);
            }
            if (options.ContainsKey("command") || options.ContainsKey("stdin-command"))
            {
                if (options.Count != 1)
                    throw new ArgumentException("Command preflight accepts one input method only.");
                var c = ValidateCommand(options.ContainsKey("stdin-command")
                    ? ReadStdinCommand(Console.In) : options["command"]);
                Emit(new
                {
                    schema = "RCM_EDITOR_PREFLIGHT_V1",
                    status = "command_validated_no_input",
                    machine = Environment.MachineName,
                    commandChars = c.Chars, commandSha256 = c.Sha256,
                    part = c.Part, total = c.Total,
                    source = options.ContainsKey("stdin-command") ? "stdin" : "operator_supplied",
                    editorFocusVerified = false, nativeChatVerified = false,
                    addonImportAcceptedVerified = false, diskSaveVerified = false,
                    gameInputSent = false, clipboardModified = false,
                    gameWindowFocused = false
                });
                return 0;
            }
            throw new ArgumentException("Specify --command, --stdin-command, --inspect, --verify-target, --self-test or --help.");
        }
        catch (Exception ex)
        {
            Emit(new
            {
                schema = "RCM_EDITOR_PREFLIGHT_V1",
                status = "refused",
                reason = ex.GetType().Name,
                detail = ex.Message,
                gameInputSent = false,
                editorFocusVerified = false
            });
            return 1;
        }
    }

    private static void RequireOnly(Dictionary<string, string> request, string allowed)
    {
        if (request.Count != 1 || !request.ContainsKey(allowed))
            throw new ArgumentException($"--{allowed} does not accept other options.");
    }

    private static Dictionary<string, string> Options(string[] args)
    {
        var switches = new HashSet<string>(StringComparer.Ordinal)
            { "self-test", "help", "inspect", "verify-target", "stdin-command" };
        var values = new HashSet<string>(StringComparer.Ordinal)
            { "command", "pid", "hwnd", "expect-start-ticks", "expect-path", "expect-sha256" };
        var output = new Dictionary<string, string>(StringComparer.Ordinal);
        for (int i = 0; i < args.Length; i++)
        {
            if (!args[i].StartsWith("--", StringComparison.Ordinal))
                throw new ArgumentException("Positional options not supported.");
            string key = args[i][2..];
            if (!switches.Contains(key) && !values.Contains(key))
                throw new ArgumentException($"Unknown option --{key}.");
            if (output.ContainsKey(key))
                throw new ArgumentException($"Duplicate option --{key}.");
            if (switches.Contains(key)) output[key] = "true";
            else
            {
                if (i + 1 >= args.Length || string.IsNullOrEmpty(args[i + 1]) ||
                    args[i + 1].StartsWith("--", StringComparison.Ordinal))
                    throw new ArgumentException($"Missing option value for --{key}.");
                output[key] = args[++i];
            }
        }
        return output;
    }

    private static string Required(Dictionary<string, string> options, string name) =>
        options.TryGetValue(name, out var value) ? value :
        throw new ArgumentException($"Missing --{name}.");

    private static string ReadStdinCommand(TextReader reader) => RcmImportContract.ReadOne(reader);

    private static RcmImport ValidateCommand(string command) => RcmImportContract.Parse(command);

    private static void Emit(object record) =>
        Console.WriteLine(JsonSerializer.Serialize(record));

    private static int Inspect()
    {
        using var group = new ProcessGroup(Process.GetProcessesByName("rift_x64"));
        if (group.Items.Length == 0)
        {
            Emit(new { schema = "RCM_EDITOR_PREFLIGHT_V1",
                status = "game_process_absent", machine = Environment.MachineName,
                gameInputSent = false });
            return 2;
        }
        // Do not automatically select a character when multiple game clients run.
        if (group.Items.Length != 1)
        {
            Emit(new { schema = "RCM_EDITOR_PREFLIGHT_V1",
                status = "ambiguous_multiple_game_processes",
                processCount = group.Items.Length, gameInputSent = false });
            return 2;
        }
        var p = group.Items[0];
        p.Refresh();
        string fullPath = p.MainModule?.FileName ??
            throw new InvalidOperationException("Process executable path unavailable.");
        string sha;
        using (var stream = File.OpenRead(fullPath))
            sha = Convert.ToHexString(SHA256.HashData(stream));
        Emit(new
        {
            schema = "RCM_EDITOR_PREFLIGHT_V1",
            status = "read_only_process_candidate",
            machine = Environment.MachineName,
            pid = p.Id,
            processStartUtcTicks = p.StartTime.ToUniversalTime().Ticks,
            hwnd = $"0x{p.MainWindowHandle.ToInt64():X}",
            title = p.MainWindowTitle, executablePath = fullPath,
            executableSha256 = sha,
            gameWindowIdentityVerified = false,
            editorFocusVerified = false,
            gameInputSent = false
        });
        return 0;
    }

    private static int VerifyTarget(Dictionary<string, string> args)
    {
        if (args.Count != 6) throw new ArgumentException(
            "Target verification requires exactly five identity parameters.");
        int pid = int.Parse(Required(args, "pid"), CultureInfo.InvariantCulture);
        long expectedTicks = long.Parse(Required(args, "expect-start-ticks"),
            CultureInfo.InvariantCulture);
        string hwndText = Required(args, "hwnd");
        if (!Regex.IsMatch(hwndText, @"^0x[0-9A-Fa-f]{1,12}$"))
            throw new ArgumentException("Window handle must be 0x-prefixed hex.");
        long expectedHwnd = Convert.ToInt64(hwndText[2..], 16);
        string expectedPath = Path.GetFullPath(Required(args, "expect-path"));
        string expectedHash = Required(args, "expect-sha256");
        if (!Regex.IsMatch(expectedHash, "^[A-Fa-f0-9]{64}$"))
            throw new ArgumentException("Expected hash must be SHA-256.");
        using var process = Process.GetProcessById(pid);
        process.Refresh();
        if (process.HasExited || process.ProcessName != "rift_x64" ||
            process.StartTime.ToUniversalTime().Ticks != expectedTicks ||
            process.MainWindowHandle.ToInt64() != expectedHwnd ||
            expectedHwnd == 0 || process.MainWindowTitle != "RIFT")
            throw new InvalidOperationException("Exact game PID/start/window/title did not match.");
        string currentPath = Path.GetFullPath(process.MainModule?.FileName ??
            throw new InvalidOperationException("Process executable path unavailable."));
        if (!string.Equals(currentPath, expectedPath, StringComparison.OrdinalIgnoreCase))
            throw new InvalidOperationException("Executable path mismatch.");
        string currentHash;
        using (var stream = File.OpenRead(currentPath))
            currentHash = Convert.ToHexString(SHA256.HashData(stream));
        if (!string.Equals(currentHash, expectedHash, StringComparison.OrdinalIgnoreCase))
            throw new InvalidOperationException("Executable SHA-256 mismatch.");
        Emit(new
        {
            schema = "RCM_EDITOR_PREFLIGHT_V1", status = "pinned_process_identity_matched",
            machine = Environment.MachineName,
            pid, processStartUtcTicks = expectedTicks,
            hwnd = $"0x{expectedHwnd:X}", executableSha256 = currentHash,
            executablePath = currentPath,
            foregroundVerified = false,
            editorFocusVerified = false,
            addonAcceptedVerified = false,
            gameInputSent = false
        });
        return 0;
    }

    private sealed class ProcessGroup(Process[] items) : IDisposable
    {
        public Process[] Items { get; } = items;
        public void Dispose() { foreach (var item in Items) item.Dispose(); }
    }

    private static int SelfTest()
    {
        int passed = 0;
        void Assert(bool pass)
        {
            if (!pass) throw new InvalidOperationException($"Self-test failed at {passed + 1}.");
            passed++;
        }

        var valid = ValidateCommand(":import ABCDEF123456 1/1 QUJDRA");
        Assert(valid.Token == "ABCDEF123456" && valid.Part == 1 && valid.Total == 1);
        Assert(valid.Chars == 31);
        Assert(ValidateCommand(":import FEDCBA987654 12/12 AAA").Total == 12);
        foreach (var input in new[]
        {
            ":import ABCDEF123456 2/1 AAA", ":import ABCDEF123456 13/13 AAA",
            ":import abcdef123456 1/1 AAA", "/rcm import ABCDEF123456 1/1 AAA",
            ":import ABCDEF123456 1/1 A=", ":import ABCDEF123456 1/1 AAA\n",
            ":import ABCDEF123456 1/1 " + new string('A', 125),
            ":import ABCDEF123456 1/1",
            ":import ABCDEF123456 0/1 A",
            ":import ABCDEF123456 1/2 你好"
        })
        {
            bool refused = false;
            try { _ = ValidateCommand(input); }
            catch (ArgumentException) { refused = true; }
            Assert(refused);
        }
        bool duplicate = false;
        try { _ = Options(["--command", "x", "--command", "x"]); }
        catch (ArgumentException) { duplicate = true; }
        Assert(duplicate);
        Assert(!Options(["--command", ":import ABCDEF123456 1/1 AAA"])
            .ContainsKey("verify-target"));
        Assert(ReadStdinCommand(new StringReader(":import ABCDEF123456 1/1 AAA\n"))
            == ":import ABCDEF123456 1/1 AAA");
        Assert(ReadStdinCommand(new StringReader(":import ABCDEF123456 1/1 AAA\r\n"))
            == ":import ABCDEF123456 1/1 AAA");
        foreach (var piped in new[]
        {
            "", "first\nsecond\n", new string('A', 161)
        })
        {
            bool blocked = false;
            try { _ = ReadStdinCommand(new StringReader(piped)); }
            catch (ArgumentException) { blocked = true; }
            Assert(blocked);
        }
        bool exclusive = false;
        try { RequireOnly(Options(["--help", "--command", "x"]), "help"); }
        catch (ArgumentException) { exclusive = true; }
        Assert(exclusive);
        Emit(new { schema = "RCM_EDITOR_PREFLIGHT_V1",
            status = "self_tests_passed", tests = passed, machine = Environment.MachineName,
            gameInputSent = false, clipboardModified = false });
        return 0;
    }
}
