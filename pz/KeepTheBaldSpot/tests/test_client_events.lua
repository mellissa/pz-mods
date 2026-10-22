-- Loads the client file against a fake game API and simulates hair growth.
-- Run from anywhere:  lua5.1 tests/test_client_events.lua

local here = debug.getinfo(1, "S").source:match("^@(.*)tests/") or "./"
local lua = here .. "Contents/mods/KeepTheBaldSpot/42/media/lua/"

local LEVELS = { [""] = 0, Picard = 1, Short = 1, Donny = 2, Fabian = 3 }
local handlers = {}
local printed = {}

local function event(name)
    return { Add = function(fn) handlers[name] = fn end }
end
Events = { OnCreatePlayer = event("OnCreatePlayer"), OnClothingUpdated = event("OnClothingUpdated") }
SandboxVars = { KeepTheBaldSpot = { Styles = "Picard;Baldspot" } }
function require() end
function isClient() return false end
function instanceof(obj, class) return class == "IsoPlayer" and obj.isPlayer end
function getHairStylesInstance()
    local function find(_, name)
        local level = LEVELS[name]
        return level and { getLevel = function() return level end } or nil
    end
    return { FindMaleStyle = find, FindFemaleStyle = find }
end
local realPrint = print
function print(msg) printed[#printed + 1] = msg end

local function makePlayer(hair)
    local p = { isPlayer = true, hair = hair, modData = {}, resets = 0 }
    local visual = {
        getHairModel = function() return p.hair end,
        setHairModel = function(_, h) p.hair = h end,
    }
    function p:getHumanVisual() return visual end
    function p:getModData() return self.modData end
    function p:isFemale() return false end
    function p:isLocalPlayer() return true end
    function p:resetModelNextFrame() self.resets = self.resets + 1 end
    return p
end

dofile(lua .. "shared/KeepTheBaldSpot/KeepTheBaldSpot.lua")
dofile(lua .. "client/KeepTheBaldSpot/KeepTheBaldSpot_Client.lua")

local failures = 0
local function check(name, actual, expected)
    if actual ~= expected then
        failures = failures + 1
        realPrint(("FAIL %s: expected %s, got %s"):format(name, tostring(expected), tostring(actual)))
    end
end

local player = makePlayer("Picard")
handlers.OnCreatePlayer(0, player)
check("remembers starting style", player.modData.KeepTheBaldSpot_lastHair, "Picard")

player.hair = "Donny"
handlers.OnClothingUpdated(player)
check("growth is undone", player.hair, "Picard")
check("model refreshed", player.resets, 1)

handlers.OnClothingUpdated(player)
check("unrelated clothing update leaves hair alone", player.hair, "Picard")

player.hair = ""
handlers.OnClothingUpdated(player)
check("shaving works", player.hair, "")

player.hair = "Short"
handlers.OnClothingUpdated(player)
player.hair = "Donny"
handlers.OnClothingUpdated(player)
check("normal styles still grow", player.hair, "Donny")

local zombie = makePlayer("Picard")
zombie.isPlayer = false
zombie.hair = "Donny"
handlers.OnClothingUpdated(zombie)
check("non-players ignored", zombie.hair, "Donny")

local logged = table.concat(printed, "\n")
check("logs unknown configured styles", logged:find("Baldspot", 1, true) ~= nil, true)

print = realPrint
print(failures == 0 and "client event checks passed" or (failures .. " client check(s) failed"))
os.exit(failures == 0 and 0 or 1)
