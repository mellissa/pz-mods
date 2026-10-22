-- Pure decision logic, kept free of game calls so it can be unit tested
-- outside the game (see tests/ at the repo root).

KeepTheBaldSpot = KeepTheBaldSpot or {}
local M = KeepTheBaldSpot

M.MOD_ID = "KeepTheBaldSpot"

-- Vanilla male styles that have a bald area.
M.DEFAULT_STYLES = "Picard;Baldspot;Recede"

local function trim(s)
    return (s:gsub("^%s+", ""):gsub("%s+$", ""))
end

-- Turns the sandbox text into rules: { [style] = growsInto | false }.
--   "Picard;Recede"           Picard and Recede never grow into full hair.
--   "Picard>LongPicard"       Picard grows into LongPicard, which then stays.
--   "A>B>C"                   A grows into B, B grows into C, C stays.
-- Entries are separated by ";" (or ","), unknown style names are harmless.
function M.parseStyles(text)
    local rules = {}
    for entry in string.gmatch(text or "", "[^;,]+") do
        local chain = {}
        for name in string.gmatch(entry, "[^>]+") do
            name = trim(name)
            if name ~= "" then
                chain[#chain + 1] = name
            end
        end
        for i, name in ipairs(chain) do
            local nextStyle = chain[i + 1] or false
            if rules[name] == nil or nextStyle then
                rules[name] = nextStyle
            end
        end
    end
    return rules
end

-- Decides what to do after the character's hair style changed from
-- `previous` to `current`. Returns the style to put back, or nil to keep
-- the change. `levelOf(name)` returns a style's length level (0 bald,
-- 1 short, 2 medium, 3 long) or nil if the game doesn't know the style.
--
-- Only growth is undone. Growth is the one way vanilla hair gets longer;
-- haircuts and trims always keep or lower the level, so they pass through.
function M.resolve(rules, previous, current, levelOf)
    if previous == nil or current == nil or previous == current then
        return nil
    end
    local rule = rules[previous]
    if rule == nil then
        return nil
    end
    local before, after = levelOf(previous), levelOf(current)
    if before == nil or after == nil or after <= before then
        return nil
    end
    if rule and rule ~= current and levelOf(rule) ~= nil then
        return rule
    end
    if rule == current then
        return nil
    end
    return previous
end

-- Style names from the rules that the game doesn't have, for the log.
function M.unknownStyles(rules, levelOf)
    local seen, missing = {}, {}
    local function check(name)
        if name and not seen[name] and levelOf(name) == nil then
            seen[name] = true
            missing[#missing + 1] = name
        end
    end
    for name, growsInto in pairs(rules) do
        check(name)
        check(growsInto)
    end
    table.sort(missing)
    return missing
end

return M
