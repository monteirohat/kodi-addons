![Easy Movie](resources/fanart.jpg)

# Easy Movie

Easy Movie is a Kodi add-on that shows the movies of your M3U lists as a poster catalog. Add a list in a few steps, browse movies by genre with the remote, open a movie to see its details, and remove movies that no longer work as soon as they fail. It is the movie companion of [Easy Channel](../script.m3u.channels/README.md), with the same design, list manager and tools.

## Features

- Poster catalog with genres on the left and six posters per row, showing title and running time.
- Movie details with a large poster, genre, running time and source list, and **Play**, **Favorite** and **Remove movie** buttons.
- Add lists from a web address, a file on the device or network, or the M3U files of a GitHub repository. No playlist configuration is required.
- When a movie fails to open, or stops right after starting, Easy Movie offers to remove it.
- **Check movies** tests a whole genre at once and removes the movies that do not respond.
- **Favorites** genre at the top, kept across list updates.
- Search across all lists, restore removed movies, and export a clean M3U file for other apps.
- With an empty movie library, selecting **Movies** in Kodi's main menu opens Easy Movie.
- Interface in English and Brazilian Portuguese.

## Screenshots

| Poster catalog | Movie details | GitHub repositories |
| --- | --- | --- |
| ![Poster catalog](resources/screenshots/screenshot-01.jpg) | ![Movie details](resources/screenshots/screenshot-02.jpg) | ![GitHub repositories](resources/screenshots/screenshot-03.jpg) |

## Installation

1. Install the **Monteiro** repository once, following the [repository instructions](../README.md#register-the-repository-in-kodi).
2. Open **Add-ons > Install from repository > Monteiro > Video add-ons > Easy Movie** and select **Install**.

Easy Movie requires Kodi 21 (Omega) or later. It was developed and tested on LibreELEC 12.2 with Kodi 21 on a Raspberry Pi 4, using the default Estuary skin.

## Getting started

1. Open Easy Movie from **Movies** in the main menu, or from **Add-ons > Video add-ons**. On first use the list manager opens automatically.
2. Select **GitHub**, then the suggested repository `OnlineM3U/publicdomainm3u`, choose **Search lists**, and pick `movies.m3u`. You can also use **Add list** with a web address or a file.
3. Close the manager. The genres of every list appear on the left and their posters on the right.

## Using Easy Movie

### Remote control

| Key | On the genres | On a poster |
| --- | --- | --- |
| **Up / Down** | Move between genres. The catalog follows the highlighted genre. | Move between rows. |
| **Right** | Move to the posters. | Move to the next poster. |
| **Left** | Move to the toolbar, keeping the highlighted genre. | Move to the previous poster. In the first column, return to the genres. |
| **OK** | Move to the posters. | Open the movie details. |
| **Back** | Close Easy Movie. | Return to the genres. |
| **Menu** (**C** on a keyboard) | | Favorite, remove or check the movie. |

### Movie details

The details window shows the poster, title, genre, running time and source list. **Play** starts the movie, **Favorite** adds it to or removes it from **Favorites**, and **Remove movie** removes it after confirmation. **Back** closes the window.

Running time comes from the `#EXTINF` duration in seconds. Lists that use `-1` show no running time.

### Toolbar

The toolbar above the genres shows the name of the focused tool.

| Icon | Tool |
| --- | --- |
| Gear | **Manage lists** opens the list manager. |
| Magnifier | **Search movies** by title across all lists. |
| Check mark | **Check movies** tests every movie of the shown genre. The tool shows the genre name. Movies that do not respond can be removed all at once or one by one. |
| Trash can | **Removed movies** lists what you removed. Select movies to restore them. |

### Movies that do not work

When a movie fails to open, stops before it starts, or ends within a minute of starting, Easy Movie asks whether to **Remove** it, **Keep** it, or **Try again**. Kodi stops waiting for an unreachable server after 8 seconds, and a movie still opening after 15 seconds is checked, so a dead link is reported in about 20 seconds. Stopping a movie after it started is never treated as a failure.

The original M3U is never changed. Removed movies are recorded by stream address and hidden from every list, so a removal keeps working when a web list is downloaded again. Restore a movie from **Removed movies** if it works again later. **Export clean M3U** in the list manager saves a list without its removed movies.

Genres are taken from `group-title`. Movies without a genre, or with a placeholder such as `Undefined`, are listed together under **Other** at the end of the genres. Posters come from `tvg-logo`. Movies without a poster show a clapperboard.

## Managing lists

The list manager opens over the catalog, and the genres behind it are reloaded after every change.

- **Add list** adds a list from a web address or a file and suggests a name.
- Select a list to **Update list**, **Rename list**, **Export clean M3U** or **Delete list**.
- **GitHub** opens the repository manager.
- **Settings** opens the add-on settings.

### GitHub repositories

**Search lists** reads every `.m3u` and `.m3u8` file of a repository and shows the ones not added yet, with their size. When a repository has more than 30 lists, a filter narrows them first. Empty files are left out of the results. Files without movies and playlists of a single stream are skipped when adding, and the summary shows how many were skipped.

**Add repository** accepts `owner/name`, a GitHub address, or the address of a folder, and searches it right away. **Delete repository** removes a repository and keeps the lists added from it.

| Suggested repository | Content |
| --- | --- |
| [OnlineM3U/publicdomainm3u](https://github.com/OnlineM3U/publicdomainm3u) | Public domain movies and TV shows hosted by the Internet Archive, with posters and genres. |

The repository is maintained by a third party. Searches use the public GitHub API, which allows about 30 searches per hour from one network.

## Movies menu

When Kodi's movie library is empty, selecting **Movies** in Kodi's main menu opens Easy Movie instead of the empty video sources. Closing Easy Movie returns to the main menu. When the library has movies, Kodi's own movie screens open as usual.

Turn off **Open Easy Movie from the Movies menu** in the settings to keep Kodi's behavior in every case. This works with the Estuary skin, whose Movies entry Easy Movie recognizes.

## Settings

| Setting | Default | Purpose |
| --- | --- | --- |
| Open Easy Movie from the Movies menu | On | Open Easy Movie when **Movies** is selected in Kodi's main menu and the movie library is empty. |
| Offer to remove movies that fail to play | On | Show the removal dialog after a failed playback. |
| Check the movie before playing | Off | Test each stream before opening it. Adds a short delay to every movie. |
| Update lists every (hours) | 12 | Web lists are downloaded again after this interval. The saved copy is used when the provider is offline. |
| Check timeout (seconds) | 8 | Advanced. Time to wait for each stream during a check. |
| Movies checked at the same time | 10 | Advanced. Parallel requests during **Check movies**. |

## Supported M3U features

- `#EXTINF` duration, names with `tvg-logo`, `tvg-name` and `group-title`, including several genres separated by semicolons.
- `#EXTGRP` groups.
- `#EXTVLCOPT` user agent, referrer, origin and cookie options, sent as HTTP headers.
- `#KODIPROP` properties, such as `inputstream.adaptive` settings.
- HTTP, HTTPS and the other protocols Kodi plays. Checks only test HTTP and HTTPS streams.

## Data and privacy

Easy Movie stores its data in Kodi's add-on data folder, `userdata/addon_data/script.m3u.movies`, separate from Easy Channel.

| File | Content |
| --- | --- |
| `lists.json` | Added lists, with their names and addresses. |
| `cache/` | Saved copies of the lists. |
| `removed.json` | Removed movies. |
| `favorites.json` | Favorite movies. |
| `repositories.json` | GitHub repositories, once the suggested one is changed. |

Easy Movie connects only to the addresses of your lists, streams and posters, and to `api.github.com` and `raw.githubusercontent.com` when you search a repository. It sends no usage data.

## Known limitations

- A check confirms that a stream server answers, not that the movie plays. Movies that pass a check can still fail, and are then offered for removal after playback.
- Playback does not resume where a movie was stopped.
- Kodi's own dialogs, such as confirmations, selection lists and the keyboard, use the style of the current skin.

## Disclaimer

Easy Movie does not provide any content. It plays the lists you add, and you are responsible for using only lists you are allowed to watch. The suggested repository lists public domain movies and is maintained by a third party, not by this project.

## Development

Easy Movie shares its design and most of its code with Easy Channel. Each add-on keeps its own copy, as the repository conventions ask for self-contained add-ons. `m3u.py`, `probe.py`, `github.py`, `storage.py` and `watcher.py` are the same modules, with the defaults and the `#EXTINF` duration that movies need.

| Path | Purpose |
| --- | --- |
| `default.py` | Opens the main window. |
| `service.py` | Background service for the Movies menu. |
| `resources/lib/gui.py` | Catalog, movie details, list manager and repository manager. |
| `resources/lib/watcher.py` | Playback and failure detection. |
| `resources/lib/m3u.py` | M3U parsing and writing. |
| `resources/lib/probe.py` | Stream checks. |
| `resources/lib/github.py` | GitHub repository search. |
| `resources/lib/storage.py` | Lists, cache, favorites and removed movies. |
| `resources/lib/movies_menu.py` | Movies menu service. |
| `resources/skins/default/` | Window layouts and textures. |

Toolbar tools are declared in `TOOLS` in `resources/lib/gui.py`.

The window layouts are generated by `tools/generate_m3u_movies_skin.py` in the repository root, which reuses the palette, toolbar, genres and managers of `tools/generate_m3u_channels_skin.py`. A palette change in the Easy Channel generator applies to both add-ons after running both scripts.

The icon, fanart, header symbol and poster placeholder are drawn by `tools/generate_easy_movie_art.py`, with the colors and shapes of Easy Channel's artwork. It needs Pillow and the [Inter](https://rsms.me/inter/) font, released under the SIL Open Font License. Pass the folder that holds `Inter-Bold.ttf` and `Inter-Medium.ttf` as its argument.

## License

MIT. See [LICENSE](LICENSE).
