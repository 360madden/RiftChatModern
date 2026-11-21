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
        proc = subprocess.run(args, capture_output=True, text=True,
                              encoding="utf-8", timeout=10, check=False)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        record = json.loads(proc.stdout)
        self.assertEqual(record["event"], "rcm_manual_import")
        self.assertFalse(record["automaticGameInput"])
        self.assertFalse(record["liveGameDeliveryVerified"])
        for command in record["commands"]:
            self.assertTrue(command.startswith("/rcm import "))
            self.assertLessEqual(len(command), 160)
        return record

    def lua(self, saved_setup=""):
        lua = LuaRuntime(unpack_returned_tuples=True)
        lua.execute(RIFT_MOCK)
        for filename in MODULES:
            source = (ADDON / filename).read_text(encoding="utf-8")
            chunk = ("local f=assert(loadstring(" + _lua_quote(source)
                     + "));assert(f({identifier='RiftChatModern',"
                     "version='0.2.17'}, {})==nil)")
            lua.execute(chunk)
        if saved_setup:
            lua.execute(saved_setup)
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
assert(RiftChatModernAPI.GetStatus().hostEditorImportReady==true)
assert(RiftChatModernAPI.GetStatus().hostAutoImportAvailable==false)
assert(RiftChatModernAPI.GetHostIngressStatus().mode=="manual_slash_or_editor")
''')
        self.send(lua, record["commands"])
        lua.execute('''
local stat=RiftChatModernAPI.GetHostIngressStatus()
assert(stat.imported==1 and stat.pending==false)
local rows,total=RiftChatModernAPI.GetHistory("chat","host",10,0)
assert(total==1 and rows[1].source=="Atank")
assert(rows[1].text=="hello from host")
assert(rows[1].kind=="import" and rows[1].origin=="host_manual")
assert(rows[1].channelKind=="guild" and rows[1].channelName=="Guild")
assert(RiftChatModernSaved.schemaVersion==2)
assert(RiftChatModernCore.rowLabel(rows[1])=="HOST IMPORT / Guild")
assert(RiftChatModernAPI.interfaceVersion==2)
assert(RiftChatModernSaved.hostIngress==nil)
''')

    def test_rcm_editor_accepts_host_import_without_using_native_chat_field(self):
        record=self.encode("guild","RCMProbe","Guild","editor transport candidate")
        command=record["commands"][0]
        self.assertEqual(record["parts"],1)
        editor_command=":import "+command[len("/rcm import "):]
        lua=self.lua()
        lua.execute("assert(RiftChatModernAPI.Show())")
        lua.execute("assert(RiftChatModernAPI.FocusEditor())")
        lua.execute(
            "local field=frames.RCMInput;field:SetText("+
            _lua_quote(editor_command)+");field.Event:KeyDown('enter')")
        lua.execute(r'''
local rows,n=RiftChatModernAPI.GetHistory("imports","editor transport candidate",5,0)
assert(n==1 and rows[1].kind=="import" and rows[1].origin=="host_manual")
assert(rows[1].importToken=="ABCDEF123456")
assert(RiftChatModernAPI.GetHostIngressStatus().lastImportedMessageId==rows[1].id)
assert(RiftChatModernAPI.GetStatus().commandHistoryCount==0)
assert(frames.RCMInput:GetText()=="")
assert(RiftChatModernAPI.GetStatus().hostAutoImportAvailable==false)
assert(RiftChatModernAPI.GetStatus().hostEditorImportReady==true)
assert(not RiftChatModernAPI.RegisterCommand("import",function() return true end))
assert(RiftChatModernAPI.GetSaveCheckpointStatus().onDiskVerified==false)
''')
        # Same transfer through the API stays idempotent, not a second row.
        lua.execute("assert(RiftChatModernAPI.Submit("+_lua_quote(editor_command)+"))")
        lua.execute(r'''
local rows,n=RiftChatModernAPI.GetHistory("imports","editor transport candidate",5,0)
assert(n==1 and RiftChatModernAPI.GetHostIngressStatus().duplicates>=1)
assert(RiftChatModernAPI.GetStatus().commandHistoryCount==0)
''')
        # The editor preserves a rejected command as a draft; no fake import.
        bad=":import BAD"
        lua.execute(
            "local field=frames.RCMInput;field:SetText("+
            _lua_quote(bad)+");field.Event:KeyDown('enter')")
        lua.execute(r'''
assert(frames.RCMInput:GetText()==":import BAD")
assert(RiftChatModernAPI.GetStatus().commandHistoryCount==0)
local rows,n=RiftChatModernAPI.GetHistory("imports","editor transport candidate",5,0)
assert(n==1)
''')

    def test_editor_import_chunks_and_cancel_use_same_ingress_state(self):
        record=self.encode("party","RCMProbe","Party","🧭"*90,
                           token="FEDCBA987654")
        self.assertGreater(record["parts"],1)
        lua=self.lua()
        lua.execute("assert(RiftChatModernAPI.Show())")
        first=":import "+record["commands"][0][len("/rcm import "):]
        lua.execute(
            "local field=frames.RCMInput;field:SetText("+
            _lua_quote(first)+");field.Event:KeyDown('return')")
        lua.execute(r'''
local state=RiftChatModernAPI.GetHostIngressStatus()
assert(state.pending and state.pendingParts==1)
assert(RiftChatModernAPI.GetStatus().commandHistoryCount==0)
assert(frames.RCMInput:GetText()=="")
''')
        lua.execute('assert(RiftChatModernAPI.Submit(":import cancel"))')
        lua.execute(r'''
assert(not RiftChatModernAPI.GetHostIngressStatus().pending)
assert(RiftChatModernAPI.GetHostIngressStatus().cancelled==1)
assert(RiftChatModernAPI.GetStatus().commandHistoryCount==0)
''')
        # One fully fresh attempt after cancellation may import all chunks.
        for command in record["commands"]:
            rest=":import "+command[len("/rcm import "):]
            lua.execute("assert(RiftChatModernAPI.Submit("+_lua_quote(rest)+"))")
        lua.execute(r'''
local rows,n=RiftChatModernAPI.GetHistory("imports","",10,0)
assert(n==1 and rows[1].importToken=="FEDCBA987654")
assert(RiftChatModernAPI.GetHostIngressStatus().imported==1)
assert(RiftChatModernAPI.GetStatus().commandHistoryCount==0)
''')

    def test_import_receipt_exposes_exact_saved_history_id_without_disk_claim(self):
        record=self.encode("guild","RCMProbe","Guild","verifiable candidate")
        lua=self.lua()
        self.send(lua,record["commands"])
        lua.execute(r'''
local rows,total=RiftChatModernAPI.GetHistory("imports","verifiable candidate",10,0)
assert(total==1 and rows[1].kind=="import")
local id=rows[1].id
local stat=RiftChatModernAPI.GetHostIngressStatus()
assert(stat.imported==1 and stat.lastImportedMessageId==id)
assert(stat.lastImportToken=="ABCDEF123456")
assert(displays[#displays]:find("history #"..id,1,true))
assert(displays[#displays]:find("NOT verified on disk",1,true))
assert(RiftChatModernAPI.GetSaveCheckpointStatus().pendingSessionChanges)
fire(slash.rcm,"import status")
assert(displays[#displays]:find("last imported history #"..id,1,true))
assert(displays[#displays]:find("NOT verified on disk",1,true))
''')
        self.send(lua,record["commands"])
        lua.execute(r'''
local rows,total=RiftChatModernAPI.GetHistory("imports","verifiable candidate",10,0)
assert(total==1)
assert(RiftChatModernAPI.GetHostIngressStatus().lastImportedMessageId==rows[1].id)
assert(displays[#displays]:find("duplicate chunk ignored",1,true))
''')

    def test_broken_retained_token_lookup_refuses_new_import(self):
        command=self.encode("guild","RCMProbe","Guild","test lookup")["commands"][0]
        line=command[len("/rcm import "):]
        lua=self.lua()
        lua.execute(r'''
publishes=0
recv=assert(RiftChatModernHostIngress.new(
    function() publishes=publishes+1 return true end,
    function() error("broken saved-history lookup") end))
''')
        lua.execute("local ok,reason=recv:receiveLine(" + _lua_quote(line) + ",1700)\n" +
                    "assert(ok==nil and reason=='duplicate_lookup_failed')\n" +
                    "assert(recv:status().imported==0 and recv:status().rejected==1)\n" +
                    "assert(publishes==0)")

    def test_import_history_id_survives_fresh_session_status_lookup(self):
        saved=r'''
RiftChatModernSaved={schemaVersion=2,nextId=52,history={
    {id=50,at=1700,kind="system",origin="local_addon",source="RIFT",text="earlier"},
    {id=51,at=1701,kind="import",origin="host_manual",source="RCMProbe",
        channelKind="guild",channelName="Guild",text="previous import retained"}
},saveCheckpoint={formatVersion=1,schemaVersion=2,sequence=1,at=1702,
    historyCount=2,nextId=52,lastHistoryId=51,lastImportId=51}}
'''
        lua=self.lua(saved_setup=saved)
        lua.execute(r'''
local state=RiftChatModernAPI.GetHostIngressStatus()
assert(state.ready and state.imported==0)
assert(state.lastImportedMessageId==nil) -- Not imported this session
assert(state.retainedImportCount==1)
assert(state.lastRetainedImportMessageId==51)
local rows,count=RiftChatModernAPI.GetHistory("imports","",5,0)
assert(count==1 and rows[1].id==51)
fire(slash.rcm,"import status")
assert(displays[#displays]:find("latest retained import history #51",1,true))
assert(displays[#displays]:find("NOT verified on disk",1,true))
assert(RiftChatModernAPI.GetSaveCheckpointStatus().eventSequence==1)
assert(RiftChatModernAPI.GetSaveCheckpointStatus().onDiskVerified==false)
''')

    def test_boolean_publisher_cannot_invent_history_id(self):
        record=self.encode("party","RCMProbe","Party","boolean callback receipt")
        lua=self.lua()
        command=record["commands"][0][len("/rcm import "):]
        lua.execute(r'''
local recv=assert(RiftChatModernHostIngress.new(function() return true end))
local ok,reply=recv:receiveLine('''+_lua_quote(command)+r''',1700)
assert(ok==true and reply=="imported_unverified")
local state=recv:status()
assert(state.imported==1 and state.lastImportedMessageId==nil)
assert(state.lastImportToken=="ABCDEF123456")
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
local rows,total=RiftChatModernAPI.GetHistory("chat","HOST IMPORT",10,0)
assert(total==1 and rows[1].source=="Iño")
assert(rows[1].kind=="import" and rows[1].channelKind=="public")
assert(rows[1].channelName=="World@Deepwood")
assert(rows[1].text:find("🌋",1,true)==1)
assert(#rows[1].text<=512)
''')
        self.send(lua, record["commands"])
        lua.execute('''
local stat=RiftChatModernAPI.GetHostIngressStatus()
assert(stat.imported==1 and stat.duplicates>=1)
local rows,total=RiftChatModernAPI.GetHistory("chat","HOST IMPORT",10,0)
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
                              capture_output=True, text=True, encoding="utf-8", timeout=10)
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
assert(total==1 and rows[1].kind=="import" and rows[1].source=="Friend")
assert(rows[1].channelKind=="party" and rows[1].origin=="host_manual")
assert(rows[1].text=="External observer fixture — not live RIFT")
assert(RiftChatModernCore.rowLabel(rows[1])=="HOST IMPORT / Party")
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


    def test_native_chat_receipts_remain_visible_with_rcm_window_hidden(self):
        record = self.encode("tell", "Sam", "Tell", "progress message " * 15)
        self.assertGreater(record["parts"], 1)
        lua = self.lua()
        self.send(lua, [record["commands"][0]])
        lua.execute(r'''
assert(RiftChatModernAPI.GetStatus().windowVisible==false)
assert(displays[#displays]:find("1/",1,true))
assert(displays[#displays]:find("NOT verified native chat",1,true))
fire(slash.rcm,"import status")
local stat=RiftChatModernAPI.GetHostIngressStatus()
assert(stat.pending==true and stat.pendingParts==1)
assert(displays[#displays]:find("host candidate imports=0",1,true))
''')
        # Repeated parts must generate a native-chat receipt without publishing.
        self.send(lua, [record["commands"][0]])
        lua.execute(r'''
assert(displays[#displays]:find("duplicate chunk ignored",1,true))
assert(RiftChatModernAPI.GetHostIngressStatus().duplicates==1)
assert(RiftChatModernAPI.GetHostIngressStatus().imported==0)
''')
        self.send(lua, record["commands"][1:])
        lua.execute(r'''
assert(displays[#displays]:find("NOT verified native chat",1,true))
assert(RiftChatModernAPI.GetHostIngressStatus().imported==1)
fire(slash.rcm,"import status")
assert(displays[#displays]:find("Host import idle",1,true))
local rows,total=RiftChatModernAPI.GetHistory("chat","HOST IMPORT",10,0)
assert(total==1 and rows[1].kind=="import" and rows[1].channelKind=="tell")
''')

    def test_manual_cancel_native_and_editor_only_clears_transient_parts(self):
        record = self.encode("party", "Friend", "Party", "long message " * 25)
        self.assertGreater(record["parts"], 1)
        lua = self.lua()
        self.send(lua, [record["commands"][0]])
        lua.execute(r'''
assert(RiftChatModernAPI.GetHostIngressStatus().pending)
fire(slash.rcm,"import cancel")
local st=RiftChatModernAPI.GetHostIngressStatus()
assert(st.pending==false and st.cancelled==1 and st.imported==0)
assert(displays[#displays]:find("saved chat unchanged",1,true))
assert(RiftChatModernSaved.hostIngress==nil)
fire(slash.rcm,"import cancel")
assert(RiftChatModernAPI.GetHostIngressStatus().cancelled==1)
assert(displays[#displays]:find("No pending host import",1,true))
''')
        # Starting the transfer again uses the same record ID and succeeds.
        self.send(lua, record["commands"])
        lua.execute(r'''
assert(RiftChatModernAPI.GetHostIngressStatus().imported==1)
assert(RiftChatModernAPI.Submit(":host status"))
local rows=RiftChatModernAPI.GetHistory("dev","host candidate imports",1,0)
assert(rows and #rows==1)
assert(RiftChatModernAPI.Submit(":host cancel"))
local more=RiftChatModernAPI.GetHistory("dev","No pending host import",1,0)
assert(more and #more==1)
assert(RiftChatModernAPI.GetHostIngressStatus().imported==1)
''')

    def test_expired_buffer_is_reclaimed_on_status_query_without_new_chunk(self):
        lua = self.lua()
        lua.execute(r'''
local recv=assert(RiftChatModernHostIngress.new(function() return true end))
assert(not recv:cancelPending())
local ok,message=recv:receiveLine("ABCDEF123456 1/2 AAAA",1700)
assert(ok and message=="part 1/2")
assert(recv:status(1745).pending==true)
assert(recv:status(1746).pending==false)
assert(recv:status(1800).expired==1)
assert(recv:status(1800).cancelled==0)
assert(recv:status(1800).imported==0)
''')

if __name__ == "__main__":
    unittest.main()
