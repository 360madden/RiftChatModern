using System.Globalization;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;

// Strict reader for ONE complete, opt-in Node encoder output. Validates the
// entire multipart transfer before any desktop-input path is reachable.
// Never logs or persists chat bytes. This contract is host-side only.
internal sealed record RcmBatchCommand(string Line, RcmImport Import);
internal sealed record RcmImportBatch(
    string Token, string Kind, RcmBatchCommand[] Commands,
    string Sha256, int Chars)
{
    internal int Parts => Commands.Length;
}

internal static class RcmImportBatchContract
{
    private const int MaxJsonBytes = 8192;
    private const int MaxRawBytes = 780;
    private static readonly UTF8Encoding StrictUtf8 = new(false, true);
    private static readonly HashSet<string> AllowedProperties = new(StringComparer.Ordinal)
    {
        "event", "protocol", "id", "kind", "inputMode", "parts",
        "source", "automaticGameInput", "liveGameDeliveryVerified",
        "requiresManualEntry", "commands"
    };
    private static readonly Dictionary<string, char> WireKinds = new(StringComparer.Ordinal)
    {
        ["general"] = 'S',
        ["party"] = 'P',
        ["guild"] = 'G',
        ["tell"] = 'T',
        ["public"] = 'C'
    };

    internal static RcmImportBatch ReadOne(TextReader reader)
    {
        var data = new StringBuilder();
        int ch;
        while ((ch = reader.Read()) != -1)
        {
            if (data.Length >= MaxJsonBytes)
                throw new ArgumentException("Batch JSON exceeds 8192 characters.");
            data.Append((char)ch);
        }
        if (Encoding.UTF8.GetByteCount(data.ToString()) > MaxJsonBytes)
            throw new ArgumentException("Batch JSON exceeds 8192 UTF-8 bytes.");
        return Parse(data.ToString());
    }

    internal static RcmImportBatch Parse(string json)
    {
        if (string.IsNullOrWhiteSpace(json) ||
            Encoding.UTF8.GetByteCount(json) > MaxJsonBytes)
            throw new ArgumentException("One bounded encoder JSON object is required.");

        try
        {
            using var doc = JsonDocument.Parse(json, new JsonDocumentOptions
            {
                CommentHandling = JsonCommentHandling.Disallow,
                AllowTrailingCommas = false,
                MaxDepth = 6
            });
            var root = doc.RootElement;
            if (root.ValueKind != JsonValueKind.Object)
                throw new ArgumentException("Batch must be one JSON object.");
            var seen = new HashSet<string>(StringComparer.Ordinal);
            foreach (var property in root.EnumerateObject())
            {
                if (!AllowedProperties.Contains(property.Name) || !seen.Add(property.Name))
                    throw new ArgumentException("Unknown or duplicate batch JSON property.");
            }
            if (RequiredString(root, "event") != "rcm_manual_import" ||
                RequiredString(root, "protocol") != "RCM1-B64URL" ||
                RequiredString(root, "inputMode") != "editor" ||
                RequiredString(root, "source") != "Windows_candidate_parser" ||
                RequiredBool(root, "automaticGameInput") ||
                RequiredBool(root, "liveGameDeliveryVerified") ||
                !RequiredBool(root, "requiresManualEntry"))
                throw new ArgumentException("Not an offline RCM editor encoder record.");

            var id = RequiredString(root, "id");
            var kind = RequiredString(root, "kind");
            if (id.Length != 12 ||
                id.Any(c => !(c is >= '0' and <= '9' or >= 'A' and <= 'F')) ||
                !WireKinds.TryGetValue(kind, out char wireKind))
                throw new ArgumentException("Batch transfer identity or kind is invalid.");

            if (!root.TryGetProperty("parts", out var number) ||
                number.ValueKind != JsonValueKind.Number ||
                !number.TryGetInt32(out int total) || total < 1 || total > 12)
                throw new ArgumentException("Batch part count must be 1 through 12.");
            if (!root.TryGetProperty("commands", out var list) ||
                list.ValueKind != JsonValueKind.Array ||
                list.GetArrayLength() != total)
                throw new ArgumentException("Batch must include every part exactly once.");

            var commands = new RcmBatchCommand[total];
            var joined = new StringBuilder(total * 88);
            int totalChars = 0;
            for (int i = 0; i < total; i++)
            {
                var element = list[i];
                if (element.ValueKind != JsonValueKind.String)
                    throw new ArgumentException("Batch commands must be strings.");
                string line = element.GetString()!;
                var command = RcmImportContract.Parse(line);
                if (command.Token != id || command.Total != total || command.Part != i + 1)
                    throw new ArgumentException("Incomplete, reordered or mixed-token batch.");
                string encoded = line[(line.LastIndexOf(' ') + 1)..];
                if (i < total - 1 && encoded.Length != 88)
                    throw new ArgumentException("Nonfinal batch fragments must be 88 characters.");
                totalChars += line.Length;
                joined.Append(encoded);
                commands[i] = new RcmBatchCommand(line, command);
            }

            var base64url = joined.ToString();
            var padded = base64url.Replace('-', '+').Replace('_', '/');
            if (padded.Length % 4 == 1)
                throw new ArgumentException("Invalid aggregate base64url length.");
            padded = padded.PadRight((padded.Length + 3) / 4 * 4, '=');
            byte[] raw;
            try { raw = Convert.FromBase64String(padded); }
            catch (FormatException) { throw new ArgumentException("Malformed batch payload."); }
            if (raw.Length < 7 || raw.Length > MaxRawBytes ||
                Convert.ToBase64String(raw).TrimEnd('=').Replace('+', '-').Replace('/', '_') != base64url)
                throw new ArgumentException("Batch payload is over limit or not canonical.");

            string decoded;
            try { decoded = StrictUtf8.GetString(raw); }
            catch (DecoderFallbackException) { throw new ArgumentException("Batch payload is not UTF-8."); }
            var fields = decoded.Split('\0');
            if (fields.Length != 4 || fields[0].Length != 1 || fields[0][0] != wireKind ||
                !ValidField(fields[1], 40) || !ValidField(fields[2], 72) ||
                !ValidField(fields[3], 512))
                throw new ArgumentException("Batch payload fields do not match encoder contract.");

            string sha = Convert.ToHexString(SHA256.HashData(Encoding.UTF8.GetBytes(json)));
            return new RcmImportBatch(id, kind, commands, sha, totalChars);
        }
        catch (JsonException)
        {
            throw new ArgumentException("Invalid batch JSON syntax.");
        }
    }

    private static string RequiredString(JsonElement parent, string name)
    {
        if (!parent.TryGetProperty(name, out var value) ||
            value.ValueKind != JsonValueKind.String)
            throw new ArgumentException("Missing or invalid batch string field: " + name);
        return value.GetString()!;
    }

    private static bool RequiredBool(JsonElement parent, string name)
    {
        if (!parent.TryGetProperty(name, out var value) ||
            value.ValueKind is not (JsonValueKind.True or JsonValueKind.False))
            throw new ArgumentException("Missing or invalid batch boolean field: " + name);
        return value.GetBoolean();
    }

    private static bool ValidField(string value, int maxBytes) =>
        value.Length > 0 && Encoding.UTF8.GetByteCount(value) <= maxBytes &&
        !value.Any(c => c < 0x20 || c == 0x7f);
}
