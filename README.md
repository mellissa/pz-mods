# Project Zomboid Mods

A workspace for building independent **Project Zomboid Build 42** mods. Each mod has its own folder under `pz/`, can be released on its own, and is loaded by the game through a link, so you edit files here and the game picks them up.

## How Zomboid mods work

You don't change the game's own files. Project Zomboid loads mods from your **Zomboid user folder**:

| OS | Zomboid user folder |
| --- | --- |
| Windows | `C:\Users\<you>\Zomboid` |
| macOS / Linux | `~/Zomboid` |

This is not the Steam install folder. The game creates it the first time you launch it. Inside it, `Workshop/` holds mods you're developing, and that's also where the in-game Steam Workshop uploader looks.

A mod is mostly **Lua scripts** plus text and data files. The game runs your Lua and gives it access to its own API (players, items, events, UI). Your mod "integrates" by subscribing to game events like `Events.OnGameStart` or `Events.EveryTenMinutes` and calling game functions.

## Repo layout

```
pz/
  HelloZomboid/                    one releasable mod = one Workshop item
    workshop.txt                   Steam Workshop title, description, tags, visibility
    preview.png                    Workshop thumbnail, 256x256
    Contents/mods/HelloZomboid/
      common/                      files shared by every game version (required, may be empty)
      42/                          files for Build 42 and newer
        mod.info                   the mod's ID, name, and requirements
        poster.png, icon.png       pictures shown in the in-game Mods menu
        media/lua/client/          runs on the player's machine: UI, input, effects
        media/lua/server/          runs on the server, or locally in single-player
        media/lua/shared/          runs on both; Translate/EN/*.json holds text
templates/b42-mod/                 what `new` copies from
tools/pzmods.py                    helper CLI (Python 3.9+, no installs)
tests/                             tests for the helper CLI
```

## Getting started

You need [Python 3.9+](https://www.python.org/downloads/) and Project Zomboid on Steam, launched at least once. On Windows, use `py` in place of `python3`.

**1. Link the mods into the game.**

```bash
python3 tools/pzmods.py link
```

This creates links in `Zomboid/Workshop/` that point back to this repo, so you never copy files by hand. On Windows it uses folder junctions, which don't need admin rights. If your Zomboid folder is somewhere else, add `--zomboid-dir "D:\Games\Zomboid"` or set `ZOMBOID_HOME`. Run `python3 tools/pzmods.py paths` to see the folders it uses.

**2. Enable the mod in the game.** Start Project Zomboid, open **Mods** from the main menu, enable **Hello Zomboid**, and start a game. Your character should say "Hello Zomboid is running."

**3. Check the log when something goes wrong.** Everything `print()`s and every Lua error goes to `Zomboid/console.txt`. Search it for your mod ID. For more detail, add `-debug` to the game's Steam launch options (right-click the game, then Properties, then Launch Options). Debug mode shows Lua errors on screen and lets you reload Lua files without restarting.

## Making a new mod

```bash
python3 tools/pzmods.py new BetterRainBarrels --name "Better Rain Barrels" --author "Your Name" --description "Rain barrels fill faster."
python3 tools/pzmods.py validate BetterRainBarrels
python3 tools/pzmods.py link BetterRainBarrels
```

Mod IDs must be unique across all Zomboid mods, so choose something specific. Use letters, digits, and underscores only. The ID is what other mods and servers use to refer to yours, so don't rename it after release.

Run `validate` before testing in game. It catches mistakes the game ignores without telling you, such as a Build 41 file layout, `.txt` translations (Build 42 only loads `.json`), broken JSON, a missing `common/` folder, duplicate IDs, and the wrong preview size.

## Releasing on the Steam Workshop

1. Replace the placeholder `preview.png` (256x256), `poster.png`, and `icon.png` with your own art.
2. Edit `workshop.txt`. Set `visibility=public` when you're ready. It starts as `private` so you can test the upload first.
3. Bump `modversion=` in `mod.info`, then run `python3 tools/pzmods.py validate`.
4. In the game's main menu, open **Workshop**, then **Create and update items**, and pick your mod.
5. After the first upload, the game writes an `id=` line into `workshop.txt`. Commit that line, because the game uses it to update the same Workshop item later.

To depend on another mod, add `require=OtherModID` in `mod.info`. Use plain IDs separated by commas, without backslashes.

## Putting it on GitHub

Push this whole repo to one GitHub repository, and every mod ends up at `pz/<ModName>/...`, for example `pz/KeepTheBaldSpot/README.md`. Create an **empty** repository on GitHub with no README or license, then run:

```bash
git remote add github https://github.com/<your-username>/<repo-name>.git
git push github HEAD:main
```

Each mod folder is self-contained, with its own README, `.gitignore`, and tests. If you ever want a single mod in its own repo, `git subtree split --prefix=pz/<ModName> -b <branch>` makes a branch with just that folder, which you can push the same way.

## Running the tests

```bash
python3 -m unittest discover -s tests
```
