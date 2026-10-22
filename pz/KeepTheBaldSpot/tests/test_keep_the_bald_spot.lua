-- Run from the mod folder:  lua5.1 tests/test_keep_the_bald_spot.lua

local here = debug.getinfo(1, "S").source:match("^@(.*)tests/") or "./"
dofile(here .. "Contents/mods/KeepTheBaldSpot/42/media/lua/shared/KeepTheBaldSpot/KeepTheBaldSpot.lua")
local M = KeepTheBaldSpot

-- Levels as the game reports them: 0 bald, 1 short, 2 medium, 3 long.
local LEVELS = {
    [""] = 0,
    Picard = 1,
    Baldspot = 1,
    Recede = 1,
    Short = 1,
    Donny = 2,
    Fabian = 3,
    LongPicard = 2,
    LongerPicard = 3,
}
local function levelOf(name)
    return LEVELS[name]
end

local failures, count = 0, 0
local function check(name, actual, expected)
    count = count + 1
    if actual ~= expected then
        failures = failures + 1
        print(("FAIL %s: expected %s, got %s"):format(name, tostring(expected), tostring(actual)))
    end
end

local defaults = M.parseStyles(M.DEFAULT_STYLES)

check("picard growing into full hair is undone", M.resolve(defaults, "Picard", "Donny", levelOf), "Picard")
check("baldspot growing is undone", M.resolve(defaults, "Baldspot", "Donny", levelOf), "Baldspot")
check("recede growing is undone", M.resolve(defaults, "Recede", "Fabian", levelOf), "Recede")
check("shaving picard bald is allowed", M.resolve(defaults, "Picard", "", levelOf), nil)
check("same-level trim is allowed", M.resolve(defaults, "Picard", "Short", levelOf), nil)
check("normal styles grow as usual", M.resolve(defaults, "Short", "Donny", levelOf), nil)
check("haircut down to picard is allowed", M.resolve(defaults, "Fabian", "Picard", levelOf), nil)
check("no previous style does nothing", M.resolve(defaults, nil, "Donny", levelOf), nil)
check("unchanged style does nothing", M.resolve(defaults, "Picard", "Picard", levelOf), nil)
check("unknown new style is left alone", M.resolve(defaults, "Picard", "SomeModHair", levelOf), nil)

local chain = M.parseStyles("Picard>LongPicard>LongerPicard; Recede")
check("chain: picard grows into long picard", M.resolve(chain, "Picard", "Donny", levelOf), "LongPicard")
check("chain: long picard grows into longer picard", M.resolve(chain, "LongPicard", "Fabian", levelOf), "LongerPicard")
check("chain: last step stays put",
    M.resolve(M.parseStyles("Picard>LongPicard"), "LongPicard", "Fabian", levelOf), "LongPicard")
check("chain: growth that already landed on the target is kept", M.resolve(chain, "Picard", "LongPicard", levelOf), nil)
check("chain: missing target falls back to keeping the style",
    M.resolve(M.parseStyles("Picard>NotInstalled"), "Picard", "Donny", levelOf), "Picard")
check("chain: other entries still parse", chain.Recede, false)

local parsed = M.parseStyles("  Picard ,Baldspot;;  Recede>LongPicard ")
check("parse: trims spaces", parsed.Picard, false)
check("parse: accepts commas", parsed.Baldspot, false)
check("parse: arrow", parsed.Recede, "LongPicard")
check("parse: empty text", next(M.parseStyles("")), nil)
check("parse: nil text", next(M.parseStyles(nil)), nil)

local missing = M.unknownStyles(M.parseStyles("Picard>Nope;Nope;Ghost"), levelOf)
check("unknown styles listed once and sorted", table.concat(missing, ","), "Ghost,Nope")

print(("%d checks, %d failed"):format(count, failures))
os.exit(failures == 0 and 0 or 1)
