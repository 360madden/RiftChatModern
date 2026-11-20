"""RCM host-to-addon manual slash bridge, tested under Lua 5.1.

The test uses the real Node encoder and the RIFT Lua mock. This proves the
wire contract, not physical game delivery or automatic RIFT log ingestion.
"""
from pathlib import Path
import json
import shutil
import subprocess
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_addon import RIFT_MOCK, _lua_quote

try:
    from lupa.lua51 import LuaRuntime
except ImportError:
    LuaRuntime = None

ROOT = Path(__file__).resolve().parents[1]
ADDON = ROOT / "addon" / "RiftChatModern"
ENCODER = ROOT / "tools" / "rcm-chat-import.cjs"
NODE = shutil.which("node") or r"C:\Program Files\nodejs\node.exe"
MODULES = ("Core.lua", "AddonMessages.lua", "NativeChatProbe.lua",
           "ConsoleMirror.lua", "HostIngress.lua", "Main.lua")


@unittest.skipUnless(LuaRuntime is not None, "Lua 5.1 via Lupa is required")
class ManualHostIngressTests(unittest.TestCase):
    def encode(self, kind, sender, channel, text, token="ABCDEF123456"):
        args = [NODE, str(ENCODER), "--kind", kind, "--sender", sender,
                "--channel", channel, "--text", text, "--id", token]
        proc = subprocess.run(args, capture_output=True, text=True, timeout=10,
                              check=False)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        record = json.loads(proc.stdout)
        self.assertEqual(record["event"], "rcm_manual_import")
        self.assertFalse(record["automaticGameInput"])
        self.assertFalse(record["liveGameDeliveryVerified"])
        for command in record["commands"]:
            self.assertTrue(command.startswith("/rcm import "))
            self.assertLessEqual(len(command), 160)
        return record

    def lua(self):
        lua = LuaRuntime(unpack_returned_tuples=True)
        lua.execute(RIFT_MOCK)
        for filename in MODULES:
            source = (ADDON / filename).read_text(encoding="utf-8")
            chunk = ("local f=assert(loadstring(" + _lua_quote(source)
                     + "));assert(f({identifier='RiftChatModern',"
                     "version='0.2.9'}, {})==nil)")
            lua.execute(chunk)
        lua.execute('fire(Event.Addon.SavedVariables.Load.End,"RiftChatModern")')
        lua.execute('fire(Event.Addon.Load.End,"RiftChatModern")')
        return lua

    def send(self, lua, commands):
        for command in commands:
            assert command.startswith("/rcm ")
            lua.execute("fire(slash.rcm," + _lua_quote(command[5:]) + ")")

    def test_single_part_manual_slash_import_and_status(self):
        record = self.encode("guild", "Atank", "Guild", "hello from host")
        lua = self.lua()
        lua.execute('''
local stat=RiftChatModernAPI.GetHostIngressStatus()
assert(stat.ready==true and stat.liveChatVerified==false)
assert(stat.autoInputAvailable==false)
assert(stat.imported==0)
assert(RiftChatModernAPI.GetStatus().hostManualImportReady==true)
assert(RiftChatModernAPI.GetStatus().hostAutoImportAvailable==false)
''')
        self.send(lua, record["commands"])
        lua.execute('''
local stat=RiftChatModernAPI.GetHostIngressStatus()
assert(stat.imported==1 and stat.pending==false)
local rows,total=RiftChatModernAPI.GetHistory("chat","host",10,0)
assert(total==1 and rows[1].source=="Atank")
assert(rows[1].text=="[HOST? Guild] hello from host")
assert(RiftChatModernSaved.hostIngress==nil)
''')

    def test_utf8_multichunk_out_of_order_and_duplicate_replay(self):
        message = "🌋東京" * 50
        record = self.encode("public", "Iño", "World@Deepwood", message)
        self.assertGreater(record["parts"], 1)
        lua = self.lua()
        commands = record["commands"]
        self.send(lua, [commands[-1]] + commands[:-1])
        lua.execute('''
local stat=RiftChatModernAPI.GetHostIngressStatus()
assert(stat.imported==1 and stat.pending==false)
local rows,total=RiftChatModernAPI.GetHistory("chat","HOST?",10,0)
assert(total==1 and rows[1].source=="Iño")
assert(rows[1].text:find("[HOST? World@Deepwood]",1,true)==1)
assert(#rows[1].text<=512)
''')
        self.send(lua, record["commands"])
        lua.execute('''
local stat=RiftChatModernAPI.GetHostIngressStatus()
assert(stat.imported==1 and stat.duplicates>=1)
local rows,total=RiftChatModernAPI.GetHistory("chat","HOST?",10,0)
assert(total==1)
''')

    def test_conflicting_chunks_and_busy_session_are_rejected(self):
        first = self.encode("tell", "Sam", "Tell", "message"*55,
                            token="AA11BB22CC33")
        second = self.encode("guild", "Sam", "Guild", "hello",
                             token="DD44EE55FF66")
        self.assertGreater(first["parts"], 1)
        lua = self.lua()
        self.send(lua, [first["commands"][0]])
        self.send(lua, second["commands"])
        lua.execute('''
local stat=RiftChatModernAPI.GetHostIngressStatus()
assert(stat.imported==0 and stat.pending==true and stat.rejected>=1)
''')
        self.send(lua, first["commands"][1:])
        lua.execute('''
assert(RiftChatModernAPI.GetHostIngressStatus().imported==1)
assert(RiftChatModernAPI.GetStatus().nativePlayerChatCaptureAvailable==false)
''')

    def test_corrupted_chunk_and_timeout_fail_without_publication(self):
        lua=self.lua()
        lua.execute('''
local receiver=assert(RiftChatModernHostIngress.new(function()
    return true
end))
local ok,reason=receiver:receiveLine("ABCDEF123456 1/1 @@",1700)
assert(ok==nil and reason=="invalid_chunk")
ok,reason=receiver:receiveLine("ABCDEF123456 1/1 AAAA",1700)
assert(ok==nil and reason=="invalid_fields")
ok,reason=receiver:receiveLine("ABCDEF123456 1/2 AAAA",1701)
assert(ok==true and receiver:status().pending)
ok,reason=receiver:receiveLine("ABCDEF123456 2/2 AAAA",1760)
assert(ok==true and receiver:status().expired==1)
assert(receiver:status().imported==0)
''')

    def test_max_size_and_invalid_cli_fields_rejected(self):
        for bad in [("guild", "Sam", "Guild", "a"*513),
                    ("guild", "Sam\nname", "Guild", "hello"),
                    ("unknown", "Sam", "Guild", "hello")]:
            args=[NODE,str(ENCODER),"--kind",bad[0],"--sender",bad[1],
                  "--channel",bad[2],"--text",bad[3]]
            r=subprocess.run(args,capture_output=True,text=True,timeout=10)
            self.assertNotEqual(r.returncode,0)
        lua=self.lua()
        lua.execute('''
assert(RiftChatModernHostIngress.decode("A") == nil)
assert(RiftChatModernHostIngress.decode("AAAA!") == nil)
assert(RiftChatModernHostIngress.parsePayload("broken") == nil)
''')

    def test_external_observer_jsonl_to_encoder_to_lua_history(self):
        # Use the exact candidate event shape emitted by rcm-chat-observer.
        event = {"event": "candidate_chat", "source": "RIFT_Log.txt",
                 "kind": "party", "sender": "Friend", "channel": "Party",
                 "text": "External observer fixture — not live RIFT",
                 "verifiedLiveFormat": False}
        proc = subprocess.run([NODE, str(ENCODER), "--stdin-json"],
                              input=json.dumps(event, ensure_ascii=False) + "\n",
                              capture_output=True, text=True, timeout=10)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        lines = [json.loads(line) for line in proc.stdout.splitlines()]
        self.assertEqual(lines[0]["event"], "rcm_manual_import")
        self.assertTrue(lines[0]["requiresManualEntry"])
        self.assertFalse(lines[0]["automaticGameInput"])
        self.assertEqual(lines[1]["generated"], 1)
        lua = self.lua()
        self.send(lua, lines[0]["commands"])
        lua.execute('''
local rows,total=RiftChatModernAPI.GetHistory("chat","External observer",5,0)
assert(total==1 and rows[1].kind=="party" and rows[1].source=="Friend")
assert(rows[1].text:find("HOST? Party",1,true))
assert(RiftChatModernAPI.GetHostIngressStatus().imported==1)
''')

    def test_corrupt_utf8_never_published_and_failed_publisher_not_acked(self):
        import base64
        bad = base64.urlsafe_b64encode(b"G\x00Sam\x00Guild\x00\xff").rstrip(b"=").decode()
        good = self.encode("guild", "Sam", "Guild", "text")
        lua = self.lua()
        lua.execute("""
local received=0
local recv=assert(RiftChatModernHostIngress.new(function()
    received=received+1
    return false
end))
local ok,reason=recv:receiveLine("ABCDEF123456 1/1 """ + bad + """",1700)
assert(ok==nil and reason=="invalid_fields" and received==0)
""")
        line = good["commands"][0][len("/rcm import "):]
        lua.execute("local recv=assert(RiftChatModernHostIngress.new(function() return false end))\n"
                    "local ok,err=recv:receiveLine(" + _lua_quote(line) + ",1700)\n"
                    "assert(ok==nil and err=='publisher_refused')\n"
                    "assert(recv:status().publishFailed==1 and recv:status().imported==0)\n"
                    "assert(not recv:status().pending)")

    def test_stale_or_duplicate_fragments_are_idempotent(self):
        record=self.encode("tell","Sam","Tell","T"*350)
        lua=self.lua()
        first=record["commands"][0]
        self.send(lua,[first,first])
        lua.execute('''
local stat=RiftChatModernAPI.GetHostIngressStatus()
assert(stat.pending and stat.pendingParts==1)
assert(stat.duplicates>=1 and stat.acceptedChunks==1)
''')
        self.send(lua,record["commands"][1:])
        lua.execute('''
local stat=RiftChatModernAPI.GetHostIngressStatus()
assert(stat.imported==1 and stat.pending==false)
''')

if __name__ == "__main__":
    unittest.main()
