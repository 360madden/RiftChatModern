using System.Globalization;
using System.Security.Cryptography;
using System.Text;
using System.Text.RegularExpressions;

// Shared, input-free contract used by the read-only command preflight and
// the separately permissioned Windows sender. Both use identical bounds.
internal sealed record RcmImport(
    string Token, int Part, int Total, int Chars, string Sha256);

internal static class RcmImportContract
{
    private static readonly Regex TransferPattern = new(
        @"\A:import ([A-F0-9]{12}) ([1-9]|1[0-2])/([1-9]|1[0-2]) ([A-Za-z0-9_-]{1,88})\z",
        RegexOptions.CultureInvariant | RegexOptions.Compiled);

    internal static RcmImport Parse(string command)
    {
        if (string.IsNullOrEmpty(command) || Encoding.UTF8.GetByteCount(command) > 160)
            throw new ArgumentException("RCM :import command missing or over 160 UTF-8 bytes.");
        var m = TransferPattern.Match(command);
        if (!m.Success)
            throw new ArgumentException("Expected one bounded :import TOKEN INDEX/TOTAL BASE64URL.");
        int part = int.Parse(m.Groups[2].Value, CultureInfo.InvariantCulture);
        int total = int.Parse(m.Groups[3].Value, CultureInfo.InvariantCulture);
        if (part > total) throw new ArgumentException("Chunk index exceeds chunk total.");
        return new RcmImport(m.Groups[1].Value, part, total, command.Length,
            Convert.ToHexString(SHA256.HashData(Encoding.UTF8.GetBytes(command))));
    }

    internal static string ReadOne(TextReader source)
    {
        var builder = new StringBuilder(160);
        int ch;
        while ((ch = source.Read()) != -1)
        {
            if (ch == '\n') break;
            if (ch == '\r')
            {
                if (source.Peek() == '\n') _ = source.Read();
                break;
            }
            if (builder.Length >= 160)
                throw new ArgumentException("Piped transfer exceeds 160 characters.");
            builder.Append((char)ch);
        }
        if (source.Peek() != -1)
            throw new ArgumentException("Only one transfer command per invocation.");
        if (builder.Length == 0)
            throw new ArgumentException("No transfer command provided.");
        return builder.ToString();
    }
}
