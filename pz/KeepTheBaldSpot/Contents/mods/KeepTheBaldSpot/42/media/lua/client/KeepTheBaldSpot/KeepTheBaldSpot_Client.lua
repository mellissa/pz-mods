-- The game grows hair in Java (IsoGameCharacter.updateBeardAndHair): every
-- ~20 in-game days, while asleep, it swaps the style for the first longer
-- "grow reference" style, which for Picard is a full head of hair. It fires
-- OnClothingUpdated right after, which is where this file undoes the swap.

require "KeepTheBaldSpot/KeepTheBaldSpot"

local M = KeepTheBaldSpot
local LAST_HAIR_KEY = "KeepTheBaldSpot_lastHair"

local function log(message)
    print("[" .. M.MOD_ID .. "] " .. message)
end

local function rules()
    local options = SandboxVars and SandboxVars.KeepTheBaldSpot
    local text = options and options.Styles
    if text == nil or text == "" then
        text = M.DEFAULT_STYLES
    end
    return M.parseStyles(text)
end

local function levelFinder(player)
    local styles = getHairStylesInstance()
    local female = player:isFemale()
    return function(name)
        if name == nil then
            return nil
        end
        local style
        if female then
            style = styles:FindFemaleStyle(name)
        else
            style = styles:FindMaleStyle(name)
        end
        if style == nil then
            return nil
        end
        return style:getLevel()
    end
end

local function isLocalPlayer(character)
    return instanceof(character, "IsoPlayer") and character:isLocalPlayer()
end

local function remember(player)
    player:getModData()[LAST_HAIR_KEY] = player:getHumanVisual():getHairModel()
end

local function onClothingUpdated(character)
    if not isLocalPlayer(character) then
        return
    end

    local visual = character:getHumanVisual()
    local previous = character:getModData()[LAST_HAIR_KEY]
    local current = visual:getHairModel()
    local target = M.resolve(rules(), previous, current, levelFinder(character))

    if target then
        visual:setHairModel(target)
        character:resetModelNextFrame()
        if isClient() and sendVisual then
            pcall(sendVisual, character)
        end
        log("hair grew from " .. tostring(previous) .. " into " .. tostring(current) .. ", set to " .. target)
    end

    remember(character)
end

local function onCreatePlayer(_, player)
    if not isLocalPlayer(player) then
        return
    end
    if player:getModData()[LAST_HAIR_KEY] == nil then
        remember(player)
    end

    local missing = M.unknownStyles(rules(), levelFinder(player))
    if #missing > 0 then
        log("these configured styles don't exist for this character and are ignored: " .. table.concat(missing, ", "))
    end
    log("watching hair style " .. tostring(player:getHumanVisual():getHairModel()))
end

Events.OnCreatePlayer.Add(onCreatePlayer)
Events.OnClothingUpdated.Add(onClothingUpdated)
