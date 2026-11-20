"""RiftChatModern v0.2.8 complete-message reader and clipboard controls."""
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_addon import RIFT_MOCK, _lua_quote

try:
    from lupa.lua51 import LuaRuntime
except ImportError:
    LuaRuntime = None

ADDON=Path(__file__).resolve().parents[1] / "addon" / "RiftChatModern"


@unittest.skipUnless(LuaRuntime is not None, "Lua 5.1 unavailable")
class MessageReaderTests(unittest.TestCase):
    def run_lua(self,source):
        lua=LuaRuntime(unpack_returned_tuples=True)
        lua.execute(RIFT_MOCK)
        for name in ("Core.lua","AddonMessages.lua","NativeChatProbe.lua","ConsoleMirror.lua"):
            lua.execute((ADDON / name).read_text(encoding="utf-8"))
        main=(ADDON/"Main.lua").read_text(encoding="utf-8")
        lua.execute("assert(loadstring("+_lua_quote(main)+"))"
                    "({identifier='RiftChatModern',version='0.2.8'})")
        lua.execute(source)

    def test_click_row_opens_full_text_and_copy_selected(self):
        self.run_lua(r'''
fire(Event.Addon.SavedVariables.Load.End,"RiftChatModern")
fire(Event.Addon.Load.End,"RiftChatModern")
local api=RiftChatModernAPI
assert(api.Show())
local long=string.rep("A",395)
local row=assert(api.Publish("addons",long,"RR2"))
assert(row.id==2)
assert(frames.RCMLineText2.text:find("...",1,true))
triggerFrame(frames.RCMLine2,Event.UI.Input.Mouse.Left.Click)
assert(frames.RCMDetailOverlay.visible==true)
assert(frames.RCMDetailBody.wrap==true)
local chunks={frames.RCMDetailBody.text}
for i=1,16 do
    triggerFrame(frames.RCMDetailNext,Event.UI.Input.Mouse.Left.Click)
    local nextChunk=frames.RCMDetailBody.text
    if nextChunk==chunks[#chunks] then break end
    chunks[#chunks+1]=nextChunk
end
assert(table.concat(chunks)==long)
assert(frames.RCMDetailPageStatus.text:find("/",1,true))
triggerFrame(frames.RCMDetailPrev,Event.UI.Input.Mouse.Left.Click)
assert(frames.RCMDetailBody.text==chunks[math.max(1,#chunks-1)])
local selected=assert(api.GetSelectedMessage())
assert(selected.id==2 and selected.text==long)
selected.text="altered"
assert(api.GetMessage(2).text==long)
assert(api.CopySelectedMessage())
assert(copied=="RR2: "..long)
triggerFrame(frames.RCMDetailClose,Event.UI.Input.Mouse.Left.Click)
assert(frames.RCMDetailOverlay.visible==false)
assert(not api.GetSelectedMessage())
''')

    def test_selected_id_stays_valid_across_filter_or_paging(self):
        self.run_lua(r'''
fire(Event.Addon.SavedVariables.Load.End,"RiftChatModern")
fire(Event.Addon.Load.End,"RiftChatModern")
local api=RiftChatModernAPI
assert(api.Show())
local keep=assert(api.Publish("dev",string.rep("p",300),"RRE"))
assert(api.OpenMessage(keep.id))
assert(api.GetSelectedMessage().text==string.rep("p",300))
local other=assert(api.Publish("addons","other", "RR2"))
assert(api.GetSelectedMessage().id==keep.id)
-- Switching filter or rendering cannot silently reassign selected ID.
assert(api.Submit(":filter addons"))
assert(api.GetSelectedMessage().id==keep.id)
assert(api.CopySelectedMessage())
assert(copied=="RRE: "..string.rep("p",300))
assert(api.Hide())
assert(not api.GetSelectedMessage())
''')

    def test_clear_history_invalidates_selected_record_and_rejects_stale_id(self):
        self.run_lua(r'''
fire(Event.Addon.SavedVariables.Load.End,"RiftChatModern")
fire(Event.Addon.Load.End,"RiftChatModern")
local api=RiftChatModernAPI
assert(api.Show())
local one=assert(api.Publish("dev","one","RR2"))
assert(api.OpenMessage(one.id))
assert(api.Submit(":clear"))
assert(not api.GetSelectedMessage())
assert(frames.RCMDetailOverlay.visible==false)
assert(not api.CopySelectedMessage())
local row,why=api.GetMessage(one.id)
assert(row==nil and why=="message_not_retained")
''')

    def test_copy_from_editor_command_performs_clipboard_not_placeholder(self):
        self.run_lua(r'''
fire(Event.Addon.SavedVariables.Load.End,"RiftChatModern")
fire(Event.Addon.Load.End,"RiftChatModern")
local api=RiftChatModernAPI
assert(api.Show())
assert(api.Publish("system","normal message","Game"))
frames.RCMInput:SetText(":copy")
frames.RCMInput.Event:KeyDown("enter")
assert(frames.RCMInput.text=="")
assert(type(copied)=="string")
assert(copied:find("normal message",1,true))
assert(api.Submit(":copy"))
assert(copied:find("normal message",1,true))
''')

if __name__=="__main__":
    unittest.main()
