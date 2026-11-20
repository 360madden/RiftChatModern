"""RIFT Save.Begin/Save.End receipt audit and disk-persistence separation.

Tests real Lua 5.1 addon functions in an isolated fake RIFT. No real game
input or live character SavedVariables is changed.
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

ADDON=Path(__file__).resolve().parents[1]/"addon"/"RiftChatModern"
FILES=("Core.lua","AddonMessages.lua","NativeChatProbe.lua",
       "ConsoleMirror.lua","HostIngress.lua","Main.lua")

@unittest.skipUnless(LuaRuntime is not None,"Lua 5.1 via Lupa required")
class SaveLifecycleTests(unittest.TestCase):
    def run_game(self,body,setup=""):
        lua=LuaRuntime(unpack_returned_tuples=True)
        lua.execute(RIFT_MOCK)
        for name in FILES:
            src=(ADDON/name).read_text(encoding="utf-8")
            lua.execute("assert(loadstring("+_lua_quote(src)+
                        "))({identifier='RiftChatModern',version='0.2.12'}, {})")
        if setup:lua.execute(setup)
        lua.execute(body)

    def test_no_native_save_event_means_no_receipt_despite_live_import(self):
        self.run_game(r'''
fire(Event.Addon.SavedVariables.Load.End,"RiftChatModern")
fire(Event.Addon.Load.End,"RiftChatModern")
local api=RiftChatModernAPI
local status=api.GetSaveCheckpointStatus()
assert(status.saveEventReceiptAvailable==false)
assert(status.saveBeginEventsThisSession==0)
assert(status.saveEndEventsThisSession==0)
assert(status.onDiskVerified==false and status.diskPersistedVerified==false)
assert(api.Publish("addons","candidate","RR2"))
status=api.GetSaveCheckpointStatus()
assert(status.pendingSessionChanges==true)
assert(RiftChatModernSaved.saveCheckpoint==nil)
fire(Event.Addon.SavedVariables.Save.End,"OtherAddon")
assert(status.diskPersistedVerified==false)
''')

    def test_native_save_begin_stamps_bounded_receipt_and_end_is_memory_only(self):
        self.run_game(r'''
fire(Event.Addon.SavedVariables.Load.End,"RiftChatModern")
fire(Event.Addon.Load.End,"RiftChatModern")
local api=RiftChatModernAPI
assert(api.GetStatus().ready)
local imported=assert(RiftChatModernCore.new({schemaVersion=2,history={}}))
-- Main's actual RCM model receives the same kind of validated import data.
local s="2A7B39E4C1F0 1/1 RwBSQ01UZXN0AEd1aWxkAHYwLjIuMTEgcHJvdmVuYW5jZSBjbGFzc2lmaWNhdGlvbiBjaGVjaw"
fire(slash.rcm,"import "..s)
local rows,total=api.GetHistory("imports","",50,0)
assert(total==1 and rows[1].kind=="import" and rows[1].origin=="host_manual")
assert(rows[1].channelKind=="guild")
local testId=rows[1].id
assert(RiftChatModernSaved.saveCheckpoint==nil)
fire(Event.Addon.SavedVariables.Save.Begin,"AnotherAddon")
assert(RiftChatModernSaved.saveCheckpoint==nil)
now=1795192200
fire(Event.Addon.SavedVariables.Save.Begin,"RiftChatModern")
local receipt=assert(RiftChatModernSaved.saveCheckpoint)
assert(receipt.formatVersion==1 and receipt.schemaVersion==2)
assert(receipt.sequence==1 and receipt.at==1795192200)
assert(receipt.historyCount==#RiftChatModernSaved.history)
assert(receipt.lastHistoryId==testId)
assert(receipt.lastImportId==testId)
assert(receipt.nextId==testId+1)
local status=api.GetSaveCheckpointStatus()
assert(status.saveEventReceiptAvailable)
assert(status.saveBeginEventsThisSession==1)
assert(status.saveEndEventsThisSession==0)
assert(status.pendingSessionChanges==false)
assert(status.onDiskVerified==false and status.requiredDiskVerification)
fire(Event.Addon.SavedVariables.Save.End,"AnotherAddon")
assert(api.GetSaveCheckpointStatus().saveEndEventsThisSession==0)
fire(Event.Addon.SavedVariables.Save.End,"RiftChatModern")
status=api.GetSaveCheckpointStatus()
assert(status.saveEndEventsThisSession==1 and status.saveEndObservedThisSession)
assert(status.onDiskVerified==false and status.diskPersistedVerified==false)
assert(api.GetStatus().saveCheckpoint.eventSequence==1)
assert(api.GetStatus().saveCheckpoint.lastImportIdAtEvent==testId)
assert(api.Publish("addons","changed after checkpoint","RR2"))
status=api.GetSaveCheckpointStatus()
assert(status.pendingSessionChanges==true)
assert(status.eventSequence==1)
now=1795192250
fire(Event.Addon.SavedVariables.Save.Begin,"RiftChatModern")
receipt=RiftChatModernSaved.saveCheckpoint
assert(receipt.sequence==2 and receipt.at==1795192250)
assert(receipt.lastHistoryId==testId+1)
assert(receipt.lastImportId==testId)
assert(api.GetSaveCheckpointStatus().pendingSessionChanges==false)
assert(api.GetSaveCheckpointStatus().diskPersistedVerified==false)
''')

    def test_save_events_do_not_execute_a_forced_reload_or_change_native_chat(self):
        self.run_game(r'''
fire(Event.Addon.SavedVariables.Load.End,"RiftChatModern")
fire(Event.Addon.Load.End,"RiftChatModern")
local before=#displays
fire(slash.rcm,"checkpoint")
assert(#displays==before+1)
assert(displays[#displays]:find("on-disk save NOT independently verified",1,true))
assert(RiftChatModernAPI.Submit(":checkpoint status"))
local dev=RiftChatModernAPI.GetHistory("dev","on-disk save",5,0)
assert(dev and #dev>=1)
assert(RiftChatModernSaved.saveCheckpoint==nil)
fire(Event.Addon.SavedVariables.Save.Begin,"RiftChatModern")
fire(slash.rcm,"checkpoint")
assert(displays[#displays]:find("Save.Begin receipt #1",1,true))
assert(displays[#displays]:find("on-disk save NOT independently verified",1,true))
assert(RiftChatModernSaved.saveCheckpoint.formatVersion==1)
''')

    def test_checkpoint_receipt_survives_model_reload_without_claiming_disk_proof(self):
        lua=LuaRuntime(unpack_returned_tuples=True)
        lua.execute((ADDON/"Core.lua").read_text(encoding="utf-8"))
        lua.execute(r'''
local saved={schemaVersion=2,history={},nextId=1}
local model=assert(RiftChatModernCore.new(saved))
assert(model:publish("import","synthetic test","Tester",1700,{
    origin="host_manual",channelKind="guild",channelName="Guild"}))
assert(model:checkpointStatus().saveEventReceiptAvailable==false)
local receipt=assert(model:recordSaveBegin(1701))
assert(receipt.eventSequence==1 and receipt.lastImportIdAtEvent==1)
assert(receipt.onDiskVerified==false)
-- Re-enter as if the RIFT engine had loaded the serialized table.
local reopened=assert(RiftChatModernCore.new(saved))
local status=reopened:checkpointStatus()
assert(status.saveEventReceiptAvailable and status.eventSequence==1)
assert(status.historyCountAtEvent==1 and status.lastImportIdAtEvent==1)
assert(status.pendingSessionChanges==false)
assert(status.onDiskVerified==false)
assert(reopened:getHistory("imports","",5,0)[1].kind=="import")
''')

    def test_invalid_checkpoint_data_is_ignored_without_undoing_valid_history(self):
        lua=LuaRuntime(unpack_returned_tuples=True)
        lua.execute((ADDON/"Core.lua").read_text(encoding="utf-8"))
        lua.execute(r'''
local saved={schemaVersion=2,history={{id=4,at=1700,
    kind="system",origin="game_event",source="RIFT",text="hello"}},
    nextId=5,saveCheckpoint={formatVersion=1,schemaVersion=2,
        sequence="untrusted",historyCount=1,lastImportId=3,lastHistoryId=4,
        nextId=5,at=1700}}
local old=saved.saveCheckpoint
local model=assert(RiftChatModernCore.new(saved))
assert(model:getHistory("system","",5,0)[1].id==4)
assert(not model:checkpointStatus().saveEventReceiptAvailable)
assert(saved.saveCheckpoint==old)
local status=assert(model:recordSaveBegin(1800))
assert(status.eventSequence==1 and status.lastImportIdAtEvent==0)
assert(status.historyCountAtEvent==1)
local invalid,why=model:recordSaveBegin(0/0)
assert(not invalid and why=="invalid_time")
assert(saved.saveCheckpoint.sequence==1)
''')

    def test_max_sequence_rolls_over_without_corrupting_history(self):
        lua=LuaRuntime(unpack_returned_tuples=True)
        lua.execute((ADDON/"Core.lua").read_text(encoding="utf-8"))
        lua.execute(r'''
local saved={schemaVersion=2,history={},nextId=1,
    saveCheckpoint={formatVersion=1,schemaVersion=2,sequence=1000000000,
    at=1700,historyCount=0,nextId=1,lastHistoryId=0,lastImportId=0}}
local model=assert(RiftChatModernCore.new(saved))
local newStatus=assert(model:recordSaveBegin(1800))
assert(newStatus.eventSequence==1)
assert(newStatus.historyCountAtEvent==0)
assert(saved.saveCheckpoint.nextId==1)
''')

    def test_window_geometry_changes_are_tracked_as_unsaved_state(self):
        self.run_game(r'''
fire(Event.Addon.SavedVariables.Load.End,"RiftChatModern")
fire(Event.Addon.Load.End,"RiftChatModern")
local api=RiftChatModernAPI
assert(api.Show())
fire(Event.Addon.SavedVariables.Save.Begin,"RiftChatModern")
local stat=api.GetSaveCheckpointStatus()
assert(stat.pendingSessionChanges==false)
assert(api.SetWindowSize(860,655))
stat=api.GetSaveCheckpointStatus()
assert(stat.pendingSessionChanges==true)
assert(stat.onDiskVerified==false)
local revision=api.GetStatus().revision
assert(api.SetWindowSize(860,655)) -- no geometry change, no new dirty revision
assert(api.GetStatus().revision==revision)
fire(Event.Addon.SavedVariables.Save.Begin,"RiftChatModern")
stat=api.GetSaveCheckpointStatus()
assert(stat.pendingSessionChanges==false)
assert(stat.eventSequence==2)
assert(RiftChatModernSaved.ui.w==860)
assert(RiftChatModernSaved.ui.h==655)
''')

if __name__=="__main__":
    unittest.main()
