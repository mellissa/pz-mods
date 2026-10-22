-- Client code: runs on each player's machine (UI, input, what the player sees).
-- Put game rules that must also run on servers in ../server or ../shared.

local MOD_ID = "__MOD_ID__"

local function onGameStart()
    print("[" .. MOD_ID .. "] loaded")

    local player = getPlayer()
    if player then
        player:Say(getText("UI___MOD_ID___Loaded"))
    end
end

Events.OnGameStart.Add(onGameStart)
