"""RCM v2 provenance schema: real Lua 5.1 migration and dependent UI/API contracts.

Synthetic fixtures only. This suite cannot claim live RIFT player-chat capture.
"""
from pathlib import Path
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parent))
from test_addon import RIFT_MOCK,_lua_quote

try:
    from lupa.lua51 import LuaRuntime
except ImportError:
    LuaRuntime=None

ROOT=Path(__file__).resolve().parents[1]
ADDON=ROOT/"addon"/"RiftChatModern"
MODULES=("Core.lua","AddonMessages.lua","NativeChatProbe.lua",
         "ConsoleMirror.lua","HostIngress.lua","Main.lua")

@unittest.skipUnless(LuaRuntime is not None,"Lupa Lua 5.1 required")
class ProvenanceSchemaTests(unittest.TestCase):
    def core(self,script):
        lua=LuaRuntime(unpack_returned_tuples=True)
        lua.execute((ADDON/"Core.lua").read_text(encoding="utf-8"))
        lua.execute(script)

    def live_mock(self,script):
        lua=LuaRuntime(unpack_returned_tuples=True)
        lua.execute(RIFT_MOCK)
        for module in MODULES:
            source=(ADDON/module).read_text(encoding="utf-8")
            lua.execute("assert(loadstring("+_lua_quote(source)+
                        "))({identifier='RiftChatModern',version='0.2.17'}, {})")
        lua.execute(script)

    def test_migrate_35_legacy_records_preserves_ids_times_and_real_category(self):
        self.core(r'''
local saved={schemaVersion=1,history={},nextId=36,
    ui={w=940,h=680,customKey="must stay"},customState="untouched"}
for i=1,34 do
    saved.history[i]={id=i,at=1700+i,kind="system",source="Game alert",
        text="Legacy event "..i}
end
saved.history[35]={id=35,at=1735,kind="guild",source="RCMTest",
    text="[HOST? Guild] RCM 0.2.10 live import check"}
local model,why=RiftChatModernCore.new(saved)
assert(model,why)
assert(saved.schemaVersion==2 and saved.customState=="untouched")
assert(saved.ui.customKey=="must stay" and saved.nextId==36)
local all,whole=model:getHistory("all","",240,0)
assert(whole==35 and all[1].id==1 and all[35].id==35)
for i=1,34 do
    assert(saved.history[i].kind=="system")
    assert(saved.history[i].origin=="legacy_unknown")
    assert(saved.history[i].text=="Legacy event "..i)
    assert(saved.history[i].at==1700+i)
end
local imports,count=model:getHistory("imports","",10,0)
assert(count==1 and imports[1].id==35)
local m=imports[1]
assert(m.kind=="import" and m.origin=="host_manual")
assert(m.channelKind=="guild" and m.channelName=="Guild")
assert(m.source=="RCMTest" and m.at==1735)
assert(m.text=="RCM 0.2.10 live import check")
assert(m.nativePlayerChatVerified==false)
assert(RiftChatModernCore.rowLabel(m)=="HOST IMPORT / Guild")
local chat,chatCount=model:getHistory("chat","",10,0)
assert(chatCount==1 and chat[1].kind=="import")
assert(model:getHistory("system","",50,0))
local output=assert(model:exportText("all","",6000))
assert(output:find("[HOST IMPORT / Guild] RCMTest:",1,true))
assert(not output:find("[guild] RCMTest:",1,true))
assert(not output:find("[HOST? Guild]",1,true))
local again=assert(RiftChatModernCore.new(saved))
assert(again:getHistory("imports","",20,0)[1].id==35)
assert(saved.schemaVersion==2 and #saved.history==35)
''')

    def test_invalid_migration_is_atomic_and_keeps_old_bytes_unmodified(self):
        self.core(r'''
local saved={schemaVersion=1,history={
 {id=1,at=1700,kind="guild",source="Test",
  text="[HOST? Guild] preserve exactly"},
 {id=2,at=1701,kind="bad_value",source="Test",text="invalid"}
}}
local prior=saved.history
local before=prior[1].text
local model,why=RiftChatModernCore.new(saved)
assert(not model and why=="invalid_saved_history")
assert(saved.schemaVersion==1)
assert(saved.history==prior and prior[1].kind=="guild")
assert(prior[1].text==before and prior[2].kind=="bad_value")
local corrupt={schemaVersion=1,history={
 {id=1,at=1700,kind="guild",source="Test",text="[HOST? Guild] one"},
 {id=1,at=1701,kind="guild",source="Test",text="[HOST? Guild] duplicate"}
}}
assert(not RiftChatModernCore.new(corrupt))
assert(corrupt.schemaVersion==1 and corrupt.history[1].kind=="guild")
''')

    def test_import_cannot_be_stored_or_published_as_native_social_chat(self):
        self.core(r'''
local c=assert(RiftChatModernCore.new({schemaVersion=1,history={}}))
assert(c.saved.schemaVersion==2)
for _,kind in ipairs({"general","guild","party","tell"}) do
    local row,error=c:publish(kind,"text","Test",1700)
    assert(row==nil and error=="native_chat_not_available")
end
assert(not c:publish("import","text","Test",1700))
assert(not c:publish("import","text","Test",1700,{
    origin="game_event",channelKind="guild",channelName="Guild"}))
assert(not c:publish("import","text","Test",1700,{
    origin="host_manual",channelKind="unknown",channelName="Guild"}))
local m=assert(c:publish("import","Unicode 東京 🍀","RCMTest",1700,{
    origin="host_manual",channelKind="guild",channelName="Guild"}))
assert(m.kind=="import" and m.origin=="host_manual")
assert(m.channelKind=="guild" and m.channelName=="Guild")
assert(m.text=="Unicode 東京 🍀" and not m.nativePlayerChatVerified)
local all,n=c:getHistory("all","",50,0)
assert(n==1 and all[1].kind=="import")
assert(c:getHistory("imports","",50,0)[1].id==m.id)
assert(c:getHistory("chat","",50,0)[1].id==m.id)
assert(c:getHistory("guild","",50,0)==nil)
local receipt=c:getMessage(m.id)
receipt.channelKind="forged"
assert(c:getMessage(m.id).channelKind=="guild")
''')

    def test_unmarked_legacy_social_entries_remain_explicitly_uncertain(self):
        self.core(r'''
local saved={schemaVersion=1,history={{
 id=7,at=1720,kind="tell",source="OtherPlayer",text="hello"}},nextId=8}
local c=assert(RiftChatModernCore.new(saved))
local row=c:getMessage(7)
assert(row.kind=="import" and row.origin=="legacy_unknown")
assert(row.channelKind=="tell" and row.channelName=="Tell")
assert(row.text=="hello")
assert(RiftChatModernCore.rowLabel(row)=="UNVERIFIED / Tell")
local out=assert(c:exportText("all","",1024))
assert(out:find("UNVERIFIED / Tell",1,true))
assert(not out:find("[tell]",1,true))
''')

    def test_version2_strict_metadata_validation_rejects_fake_native_claims(self):
        self.core(r'''
local baseline={id=1,at=1700,kind="import",source="Test",
 text="text",origin="host_manual",channelKind="guild",channelName="Guild"}
local bad={
 {id=1,at=1700,kind="guild",source="Test",text="false native",origin="game_event"},
 {id=1,at=1700,kind="import",source="Test",text="text",origin="game_event",
  channelKind="guild",channelName="Guild"},
 {id=1,at=1700,kind="import",source="Test",text="text",origin="host_manual",
  channelKind="guild",channelName=""},
 {id=1,at=1700,kind="import",source="Test",text="text",origin="host_manual"},
}
for _,row in ipairs(bad) do
    local saved={schemaVersion=2,history={row}}
    assert(not RiftChatModernCore.new(saved))
    assert(saved.schemaVersion==2 and saved.history[1]==row)
end
local c=assert(RiftChatModernCore.new({schemaVersion=2,history={baseline}}))
assert(c:getMessage(1).origin=="host_manual")
''')

    def test_optional_persisted_import_token_preserves_schema2_and_blocks_replay(self):
        self.core(r'''
local saved={schemaVersion=2,history={},nextId=1}
local c=assert(RiftChatModernCore.new(saved))
local token="B3A0705FD6AA"
local m=assert(c:publish("import","same bytes","RCMProbe",1700,{
    origin="host_manual",channelKind="guild",channelName="Guild",
    importToken=token}))
assert(m.importToken==token and saved.history[1].importToken==token)
assert(c:findImportToken(token)==m.id)
local rev=c:status().revision
local replay,why=c:publish("import","same bytes","RCMProbe",1701,{
    origin="host_manual",channelKind="guild",channelName="Guild",
    importToken=token})
assert(replay==nil and why=="duplicate_import_token")
assert(#saved.history==1 and c:status().revision==rev)
assert(not c:publish("system","test","System",1702,{importToken=token}))
assert(not c:publish("import","test","RCMProbe",1702,{
    origin="host_manual",channelKind="guild",channelName="Guild",
    importToken="lowerabcdef12"}))
local restored=assert(RiftChatModernCore.new(saved))
assert(restored:findImportToken(token)==m.id)
assert(restored:getMessage(m.id).importToken==token)
-- Older schema-v2 import rows intentionally have no token; no migration.
local old=assert(RiftChatModernCore.new({schemaVersion=2,history={{
    id=1,at=1700,kind="import",origin="host_manual",source="Old",
    text="older",channelKind="guild",channelName="Guild"}},nextId=2}))
assert(old:getMessage(1).importToken==nil)
local bad={schemaVersion=2,nextId=3,history={
    {id=1,at=1700,kind="import",origin="host_manual",source="A",
     text="one",channelKind="guild",channelName="Guild",importToken=token},
    {id=2,at=1701,kind="import",origin="host_manual",source="B",
     text="two",channelKind="guild",channelName="Guild",importToken=token}}}
assert(not RiftChatModernCore.new(bad))
assert(bad.history[1].importToken==token and bad.history[2].importToken==token)
''')

    def test_ui_detail_copy_filter_and_subscriber_preserve_origin(self):
        self.live_mock(r'''
RiftChatModernSaved={schemaVersion=1,history={{
    id=35,at=1735,kind="guild",source="RCMTest",
    text="[HOST? Guild] RCM 0.2.10 live import check"
}},nextId=36,filter="all"}
fire(Event.Addon.SavedVariables.Load.End,"RiftChatModern")
fire(Event.Addon.Load.End,"RiftChatModern")
local api=RiftChatModernAPI
assert(api.interfaceVersion==2 and RiftChatModernSaved.schemaVersion==2)
assert(api.GetStatus().schemaVersion==2)
assert(api.Show())
assert(frames.RCMTabimports and frames.RCMTabimportsLabel.text=="IMPORTS")
local imports,total=api.GetHistory("imports","",10,0)
assert(total==1 and imports[1].kind=="import")
assert(frames.RCMLineText1.text:find("HOST/GUILD",1,true))
assert(not frames.RCMLineText1.text:find(" GUILD  RCMTest",1,true))
assert(api.OpenMessage(imports[1].id))
assert(frames.RCMDetailTitle.text:find("HOST IMPORT / Guild",1,true))
assert(api.CopySelectedMessage())
assert(copied:find("HOST IMPORT / Guild RCMTest:",1,true))
assert(not copied:find("[guild]",1,true))
assert(api.CloseMessage())
assert(api.Copy())
assert(copied:find("[HOST IMPORT / Guild] RCMTest:",1,true))
assert(api.GetStatus().filter=="all")
fire(slash.rcm,"tab imports")
assert(api.GetStatus().filter=="imports")
assert(api.GetHistory("imports","",10,0)[1].channelKind=="guild")
local received
assert(api.Subscribe("monitor",function(row) received=row end))
assert(not api.Publish("guild","forged native social","Malicious"))
assert(api.Publish("addons","real addon data","RR2"))
assert(received.kind=="addons" and received.origin=="external_api")
assert(received.nativePlayerChatVerified==false)
''')

if __name__=="__main__":
    unittest.main()
