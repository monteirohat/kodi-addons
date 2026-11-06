# Monteiro skin

A dark skin for Kodi in the design of Easy Channel and Easy Movie. **TV**, **Movies** and **Series** on the home screen open the Easy add-ons directly, without the menu services they use with other skins.

> [!WARNING]
> Preview. The home screen, Videos, Music and Pictures, dialogs, keyboard, settings, add-on browser, file manager, media sources, system information, profiles, favourites, games, live TV, power menu and player controls are included. Some rarely used windows of Kodi are not included yet, and open nothing in this skin: the playlist and smart playlist editors, video bookmarks, the color picker, game controllers and the in-game menu, the PVR channel and group managers, and screen calibration.

The live TV windows were written without a PVR client to test them with. TV on the home screen opens Easy Channel, and Easy Channel also takes over the TV windows of Kodi when its **TV menu** setting is on.

## Install

1. Install the **Monteiro** repository, as described in the [repository README](../README.md#installation).
2. Open **Settings > Add-ons > Install from repository > Monteiro > Look and feel > Skin > Monteiro** and select **Install**.
3. Kodi asks whether to switch to the skin. Select **Yes**, then **Yes** again to keep it.

To go back, open **Settings > Interface > Skin** and select **Estuary**.

## Home screen

| Item | Opens |
| --- | --- |
| **TV** | Easy Channel. Without it, Kodi offers to install it. |
| **Movies** | Easy Movie. Without it, Kodi offers to install it. |
| **Series** | Easy Movie on its series. |
| **Videos** | The video sources and folders of Kodi. |
| **Music** | Easy Music. Without it, Kodi offers to install it. |

The smaller row under the tiles:

| Item | Opens |
| --- | --- |
| **Pictures** | Easy Picture. Without it, Kodi offers to install it. |
| **Files** | Easy Files. Without it, Kodi offers to install it. |
| **Speed** | Easy Speed. Without it, Kodi offers to install it. |
| **Add-ons** | The installed add-ons, with a toolbar for search, updates, recently updated add-ons, repositories, installing from a ZIP file, checking for updates and the add-on settings. **Repositories** opens [Monteiro Add-ons](../script.monteiro.addons/README.md), which lists the add-ons of each repository with their categories. The skin installs it with itself. |

The round buttons at the top right open:

| Button | Opens |
| --- | --- |
| **Bluetooth** | [Easy Bluetooth](../script.easy.bluetooth/README.md), which pairs and connects Bluetooth devices. Without it, Kodi offers to install it. It shows on LibreELEC, and wherever Easy Bluetooth is installed. |
| **Wi-Fi** | [Easy Connect](../script.easy.connect/README.md), which manages the Wi-Fi. Without it, on LibreELEC, Kodi offers to install it; on other systems, the system information. Its icon shows the Wi-Fi signal while Easy Connect is installed, or a cable for a wired connection. |
| **Settings** | The settings sections of Kodi, the file manager and the system information. |
| **Power** | The power menu. |

Videos played outside the Easy add-ons show round controls to go back or forward 10 seconds, play and pause, and stop, and a time bar while paused.

## License

MIT. See [LICENSE](LICENSE). The skin is written from scratch and contains no part of other skins.

The fonts are Noto Sans by the Noto Project Authors, under the SIL Open Font License, included in `fonts/OFL.txt`. The icons and textures are drawn by `tools/generate_monteiro_skin.py` or come from the Monteiro add-ons.
