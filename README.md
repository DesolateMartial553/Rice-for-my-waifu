<div align="center">

# 王林 · 仙逆

### Akira's Wang Lin desktop

*A purple Renegade Immortal theme for Arch Linux, made for My princess * ♡

</div>

---

Hey princess, so after i finished stage 2 of building my product i decided to just start on building ur rice for  i hope u enjoy it...
its got a top bar, a dock, an app launcher, a lock screen, wallpapers,
and matching colours in your apps.

I made it so u dont need to do much in the installation process. The installer explains every step and asks
before it does anything. This page covers everything else.

## ✦ Installing it

**Before you start:** Arch Linux is installed, you can log in, and you're connected to the
internet. (No Wi-Fi yet? Type `nmtui`, press Enter and pick your network.)

1. **Open a terminal.** On a fresh Arch install, that's just the text screen you log in to.
2. **Copy this line, paste it in and press Enter(copy the lines in the bracket):**

   ```sh
   bash <(curl -fsSL https://raw.githubusercontent.com/DesolateMartial553/Rice-for-my-waifu/main/get.sh)
   ```

3. **Answer the questions.** Pressing **Enter** always picks the recommended answer.

A few things you'll see along the way:

- **It asks for your password.** Nothing appears while you type it. That's normal on Linux;
  just type it and press Enter.
- **It updates the rest of your system too.** Arch likes everything updated together.
- **It asks about your keyboard and screen size.** If the suggestion looks right, press Enter.
- **It takes 5–15 minutes**, depending on your internet.

When it finishes, restart the laptop. If you have a login screen, pick
**Hyprland (uwsm-managed)** on it; if you sign in on a text screen, the desktop starts by
itself. A welcome note with the most useful keys pops up the first time. 🌙

## ✦ The keys you'll use most

**Super** is the Windows key (⊞).

| Keys | What it does |
|---|---|
| **Super + A** | open an app (just start typing its name) |
| **Super + T** | terminal |
| **Super + B** | web browser |
| **Super + E** | files |
| **Super + Q** | close the window |
| **Super + W** | make the window full screen (press again to go back) |
| **Super + F** | let the window float freely (press again to snap it back) |
| **Super + 1 … 5** | switch between your 5 desktops |
| **Super + Shift + 1 … 5** | move the window to another desktop |
| **Super + arrows** | jump between windows |
| **Super + L** | lock the screen |
| **Super + /** | **every shortcut, searchable.** Use this whenever you forget one |

Hold **Super** and drag a window with the mouse to move it; hold **Super** and right-drag
to resize it.

## ✦ The top bar

Everything on the bar can be clicked:

| Icon | Click it for |
|---|---|
| sigil (far left) | your apps · *right-click*: every shortcut |
| **1 2 3 4 5** | switch desktop (or scroll over them) |
| « Ⅱ › | music: previous · play/pause · next |
| 🔊 volume | sound: volume, speakers, per-app volume · *right-click*: mute |
| ☕ coffee cup | **caffeine**: keeps the screen awake (for films or reading). Click again to turn off |
| 🔋 battery | quick settings: battery, brightness, power mode, Bluetooth, night light… |
| 📶 Wi-Fi | pick a Wi-Fi network (type the password right there) |
| 🕒 clock | calendar |
| ⏻ power | lock, log out, sleep, restart, shut down |

The **dock** at the bottom opens the terminal, files, Firefox, YouTube, Spotify, WhatsApp
and Telegram, plus the appearance settings.

## ✦ Wallpapers

- **Super + Shift + W** opens the wallpaper picker: use ← → to browse and Enter to apply.
- **Super + Alt + ← / →** switches to the previous / next wallpaper straight away.
- Add your own: put images in `~/wanglin-rice/wallpapers/` and they show up in the picker.

## ✦ Little extras

| Keys | |
|---|---|
| **Super + P** | screenshot of an area (saved in *Pictures/Screenshots* and copied) |
| **Print** | screenshot of the whole screen |
| **Super + V** | everything you've copied recently |
| **Super + ,** | emoji picker 🌸 |
| **Super + Shift + K** | calculator |
| **Super + Shift + /** | search the web |
| **Super + Alt + T** | a terminal that drops down from the top |
| **Super + N** | notifications |
| **Super + Alt + G** | game mode (turns off animations for smoother games) |

## ✦ Changing things

**Keyboard layout or screen size wrong?** Open the terminal (**Super + T**) and type:

```sh
nano ~/.config/hypr/machine.lua
```

Change `kb_layout` (e.g. `"us"`, `"gb"`) or `scale` (bigger number = bigger text), press
**Ctrl + O**, Enter, then **Ctrl + X**. Then type `hyprctl reload` and press Enter to apply it.

**App looks, colours, icons:** the ⚙ icon on the dock, or *battery icon → Appearance*.

## ✦ If something goes wrong

| Problem | Try this |
|---|---|
| **The installer stopped with an error** | Run the same command again; it's safe and picks up where it left off. If it fails again, send the log file it names to whoever set this up for you |
| **A window froze** | **Super + Q** closes it. If that doesn't work, **Super + Alt + F4** force-closes it |
| **Everything's stuck** | **Super + Delete** logs you out, or hold the power button to restart |
| **The bar disappeared** | **Super + Shift + B** brings it back |
| **No Wi-Fi in the menu** | Restart once after installing, then click the Wi-Fi icon again |
| **No sound** | Click the volume icon and check the right speaker is picked (and not muted) |
| **Text is too big / too small** | See *Changing things* above |
| **I want my old desktop back** | `cd ~/wanglin-rice && ./uninstall.sh` puts everything back exactly as it was |

## ✦ Getting updates

Whenever there's something new, run the same install command again. It downloads the
changes and keeps your settings.

---

<div align="center">

<sub>For the curious: palette, file layout and how it's built are in [TECHNICAL.md](TECHNICAL.md).</sub>

*顺为凡，逆则仙* ✦

</div>
