# Keep The Bald Spot

A Project Zomboid **Build 42** mod. Bald-pattern hairstyles like **Picard** keep their bald spot when your hair grows.

## The problem

In vanilla, hair grows one length step about every 20 in-game days while you sleep. The game does this by swapping your style for the next longer "grow reference" style, which is always a full head of hair. So a Picard character wakes up one morning as a Donny, and turning off hair stubble doesn't change that.

## What the mod does

When hair grows on a bald-pattern style, the mod puts the style back, so the bald area stays bald. By default this covers the vanilla styles Picard, Bald Spot, and Recede.

- Haircuts, trims, and shaving work exactly as before.
- Every other hairstyle grows normally.
- Beards are not affected.
- It's safe to add to an existing save. If your hair already grew back, cut it back to Picard with scissors and the mod takes over from there.

### Sandbox option

**Keep The Bald Spot → Bald-pattern hairstyles** lists the protected styles, separated by semicolons. The default is `Picard;Baldspot;Recede`.

Vanilla has no longer versions of these styles, so a protected style stays at its current length. If you install a hair mod that adds longer bald-pattern styles, you can chain them with `>`:

```
Picard>LongPicard>LongerPicard;Recede
```

With that setting, Picard grows into LongPicard, then into LongerPicard, and then stays there. Use the internal style names. In debug mode, you can see your current one with `getPlayer():getHumanVisual():getHairModel()`. Unknown names are ignored and listed in `console.txt`.

## How it works

The Java method that grows hair (`IsoGameCharacter.updateBeardAndHair`) fires the Lua event `OnClothingUpdated` right after it changes the style. The mod remembers each player's last style in the player's mod data. When the style gets longer and the old one was protected, the mod restores the old style, or the next style in the chain. Only growth can make vanilla hair longer, so haircuts are never mistaken for growth.

```
Contents/mods/KeepTheBaldSpot/42/
  mod.info
  media/sandbox-options.txt                          the sandbox option
  media/lua/shared/KeepTheBaldSpot/KeepTheBaldSpot.lua  decision logic (pure Lua, unit tested)
  media/lua/client/KeepTheBaldSpot/KeepTheBaldSpot_Client.lua  game event wiring
  media/lua/shared/Translate/EN/                     text
tests/                                               Lua 5.1 tests, not shipped to players
```

## Installing for development

Link this folder into `Zomboid/Workshop/` (`C:\Users\<you>\Zomboid\Workshop` on Windows). From the root of the mods repo, run `python3 tools/pzmods.py link KeepTheBaldSpot`. Then enable **Keep The Bald Spot** in the game's Mods menu.

To test without waiting 20 days, start the game with `-debug`, give your character Picard, and run this in the debug console:

```lua
getPlayer():getHumanVisual():setHairModel("Donny"); triggerEvent("OnClothingUpdated", getPlayer())
```

Your character should go back to Picard, and `console.txt` should show a `[KeepTheBaldSpot] hair grew from Picard into Donny, set to Picard` line.

## Running the tests

You need Lua 5.1 (`lua5.1`):

```bash
lua5.1 tests/test_keep_the_bald_spot.lua
lua5.1 tests/test_client_events.lua
```

## Publishing

1. Replace `preview.png` (256x256) and `Contents/mods/KeepTheBaldSpot/42/poster.png` with real art, and set `author=` in `mod.info`.
2. In the game's main menu, open **Workshop**, then **Create and update items**, and choose KeepTheBaldSpot. `workshop.txt` starts as `visibility=private`. Change it to `public` once you've checked the upload.
3. Commit the `id=` line the game adds to `workshop.txt`, so later uploads update the same Workshop item.

## Known limits

- Multiplayer hasn't been tested yet. The change is made on the player's own client.
- The style names `Baldspot` and `Recede` come from the vanilla style list. If a game update renames them, the log will say so and you can fix them in the sandbox option.
