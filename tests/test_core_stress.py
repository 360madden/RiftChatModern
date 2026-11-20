"""Bounded 1,200-message functional stress for the addon history model."""
from pathlib import Path
import unittest
try:
    from lupa.lua51 import LuaRuntime
except ImportError:
    LuaRuntime = None

CORE = Path(__file__).resolve().parents[1] / "addon" / "RiftChatModern" / "Core.lua"


@unittest.skipUnless(LuaRuntime is not None, "Lua 5.1 unavailable")
class CoreStressTests(unittest.TestCase):
    def test_bounded_history_sequence_callbacks_and_reload(self):
        lua = LuaRuntime(unpack_returned_tuples=True)
        lua.execute(CORE.read_text(encoding="utf-8"))
        lua.execute(r'''
local saved={schemaVersion=1,history={}}
local core=assert(RiftChatModernCore.new(saved))
local callbacks=0
assert(core:subscribe("monitor",function(event)
    callbacks=callbacks+1
end))
for i=1,1200 do
    assert(core:publish("dev","stress event "..i,"RRE",i))
end
assert(#saved.history==240 and callbacks==1200)
local entries,total=core:getHistory("all","",240,0)
assert(total==240 and entries[1].id==961 and entries[#entries].id==1200)
assert(core:execute(":status",1300))
assert(core:execute(":filter dev",1301))
assert(core:execute(":find event 1200",1302))
local filtered,count=core:getHistory(nil,nil,10,0)
assert(count>=1)
local hasEvent=false
for _,row in ipairs(filtered) do
    if row.text=="stress event 1200" then hasEvent=true end
end
assert(hasEvent)
assert(not core:execute("/say never fake native social send",1303))
local nextId=saved.nextId
local reloaded=assert(RiftChatModernCore.new(saved))
assert(reloaded:publish("dev","after-reload","RPT",1304).id==nextId)
''')

    def test_subscriber_does_not_mutate_saved_rows(self):
        lua = LuaRuntime(unpack_returned_tuples=True)
        lua.execute(CORE.read_text(encoding="utf-8"))
        lua.execute(r'''
local core=assert(RiftChatModernCore.new({schemaVersion=1,history={}}))
local called=0
assert(core:subscribe("test",function(row)
    called=called+1
    row.text="tampered"
    if called==1 then core:publish("dev","reentrant","RR2",11) end
end))
local row=assert(core:publish("addons","original","RRE",10))
assert(row.text=="original" and called==1)
local entries=core:getHistory("all","",10,0)
assert(entries[1].text=="original" and entries[2].text=="reentrant")
''')

if __name__ == "__main__":
    unittest.main()
