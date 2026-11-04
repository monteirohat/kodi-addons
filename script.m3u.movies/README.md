![Easy Movie](resources/fanart.jpg)

# Easy Movie

Easy Movie is a Kodi add-on that shows the movies and series of your M3U lists as a poster catalog. Add a list in a few steps, browse movies by genre with the remote, open a movie to see its details, and remove movies that no longer work as soon as they fail. It is the movie companion of [Easy Channel](../script.m3u.channels/README.md), with the same design, list manager and tools.

## Features

- Poster catalog with genres on the left and six posters per row, showing title and running time.
- Episodes such as `Show S01E02`, `Show 1x02` or `Show T01 E02` are grouped into one series card, with seasons, episodes and a **Continue** button for the next episode.
- Watched movies and episodes get a check mark, movies and episodes stopped midway resume where you stopped, and a **Continue watching** group lists what is in progress.
- Movie details with a large poster, genre, running time and source list, and **Play**, **Favorite** and **Remove movie** buttons.
- Add lists from a web address, a file on the device or network, or the M3U files of a GitHub repository. No playlist configuration is required.
- Download torrents from magnet links or `.torrent` files into a folder you choose, with a download list that shows progress, speed and time left.
- Add folders with your own video files, on the SD card, a USB drive or a network share. Posters and details come from Cinemeta, and files can be renamed or deleted from the catalog.
- When a movie fails to open, or stops right after starting, Easy Movie offers to remove it.
- **Check movies** tests a whole genre at once and removes the movies that do not respond.
- **Favorites** genre at the top, kept across list updates.
- Search across all lists, restore removed movies, and export a clean M3U file for other apps.
- With an empty library, selecting **Movies** or **TV shows** in Kodi's main menu opens Easy Movie, on the movies or on the series.
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

### Series

Episodes are recognized by their name and grouped into series. The text before the episode code is the series name, so `Breaking Bad S01E02 - Cat's in the Bag` becomes episode 2 of season 1 of **Breaking Bad**, titled *Cat's in the Bag*. When a name is only `S01E01`, the `group-title` is used as the series name. Episodes of the same series from different lists are shown together.

| Recognized codes | Example |
| --- | --- |
| `SxxEyy` | `Show S01E02`, `Show s1e2`, `Show S01 E02` |
| `TxxEyy` | `Show T01E02`, `Show T1 E2` |
| `NxNN` | `Show 1x02` |
| Words | `Show Temporada 1 Episódio 2`, `Show Season 1 Episode 2` |
| Season and episode with a bar | `T01\|EP02`, `01\|EP02`, `3\|EP02 Title`, `T01\|02` |

Some lists keep the series name in a `pltv-subgroup` attribute and name episodes only with a code, as in `pltv-subgroup="30 Rock",T01|EP01`. Easy Movie then uses `pltv-subgroup` as the series name, which also replaces abbreviations such as `BBAT T1|EP01`. With `pltv-subgroup`, names made only of an episode number, as `EP001`, become episodes of season 1, and `T03|ESPECIAL` becomes a special of season 3. For movies, the same attribute usually holds the genre, so it is added to the movie genres.

The same stream in several lists is shown once. Episodes with the same code but different streams are all kept, in the order of the list, because some lists give several episodes the same number.

Opening a series shows its poster, seasons and episodes. **Continue** plays the next episode: the one stopped midway, or the first unwatched episode after the last one watched. Select a season and an episode to play any other episode. **Remove series** removes all its episodes.

### Progress and Continue watching

Easy Movie remembers how far each movie and episode was watched. Playing past 90% marks it as watched, shown with a check mark. A movie or episode stopped after the first minute offers **Resume** or **Play from the beginning** the next time.

The groups start with **Continue watching**, with movies stopped midway and series with episodes left, most recent first, followed by **Favorites**, **All movies** and **Series**. Easy Movie opens on **Continue watching** when it has items.

### Toolbar

The toolbar above the genres shows the name of the focused tool.

| Icon | Tool |
| --- | --- |
| Gear | **Manage lists** opens the list manager. |
| Magnifier | **Search movies** by title across all lists. |
| Check mark | **Check movies** tests every movie of the shown genre. The tool shows the genre name. Movies that do not respond can be removed all at once or one by one. |
| Trash can | **Removed movies** lists what you removed. Select movies to restore them. |
| Download arrow | **Downloads** opens the torrent download manager. See [Downloads](#downloads). |

### Movies that do not work

Before playing, Easy Movie checks that the stream answers, with a **Connecting** dialog that can be cancelled. The details window stays open meanwhile, so another episode can be picked right away. Kodi itself waits for an unresponsive server on its interface thread, which froze the screen for half a minute, so streams that do not answer are reported before Kodi tries them. A stream that answers is checked in about two seconds, and most open without the dialog appearing. A stream that does not answer is reported within 8 seconds, the **Check timeout** setting, with **Remove**, **Cancel** or **Play anyway**.


When a movie fails to open, stops before it starts, or ends within a minute of starting, Easy Movie asks whether to **Remove** it, **Keep** it, or **Try again**. Kodi stops waiting for an unreachable server after 8 seconds, and a movie still opening after 15 seconds is checked, so a dead link is reported in about 20 seconds. Stopping a movie after it started is never treated as a failure.

The original M3U is never changed. Removed movies are recorded by stream address and hidden from every list, so a removal keeps working when a web list is downloaded again. Restore a movie from **Removed movies** if it works again later. **Export clean M3U** in the list manager saves a list without its removed movies.

Genres are taken from `group-title`. Movies without a genre, or with a placeholder such as `Undefined`, are listed together under **Other** at the end of the genres. Posters come from `tvg-logo`. Movies without a poster show a clapperboard.

## Video folders

Select **Add list** > **Folder with videos** to add a folder with your own video files, such as `/storage/videos`, a USB drive under `/var/media`, or a network share such as `smb://`. The folder becomes a list like the others, and **Update list** reads it again after you add or remove files.

- Each first level subfolder becomes a genre, such as `Movies` or `Cartoons`.
- File names are cleaned for display: `O.Senhor.dos.Aneis.2001.1080p.BluRay.mkv` appears as **O Senhor dos Aneis (2001)**.
- Episodes are recognized by their codes, such as `Show.S01E02.mkv`, and take the name of their series from their folder. A folder where most files start with a number, such as `Pica Pau/196 - Adeus As Aulas.mp4`, is a series whose episodes are those numbers. Folders named `Season 2` or `Temporada 2` give the season.
- A poster is taken from an image next to the video with the same name, from `poster.jpg`, `folder.jpg` or `cover.jpg` in the folder of a series or of a movie alone in its folder, or else from Cinemeta. Without any, Kodi shows a frame of the video.
- Subtitles with the same name as the video, such as `Movie.srt` or `Movie.pt-BR.srt`, are loaded by Kodi.
- Files of macOS (`._*` and `.DS_Store`) and sample videos are ignored.
- While the drive of a folder is disconnected, its videos are hidden. Their progress and favorites are kept for when it comes back.

### Cinemeta details

Easy Movie looks up each movie and series of a folder on [Cinemeta](https://v3-cinemeta.strem.io), the metadata service of Stremio, and shows its poster, year, IMDb rating, genres, running time and description. Titles in Portuguese are found, and descriptions are in English. Lookups run in the background the first time a video appears, and the results are saved.

When a video gets the wrong details, open its menu (**Menu** or **C**) and select **Choose info**. Edit the search if needed, then pick the right result or **No info**.

### Renaming and deleting files

The menu of a video of a folder also offers:

| Option | What it does |
| --- | --- |
| **Rename file** | Renames the video and the files with its name next to it, such as subtitles and posters. Progress and favorites follow the new name. |
| **Delete file** / **Delete series files** | Deletes the video, or all episodes of a series, with the files that have their names, after a confirmation. |
| **Remove movie** / **Remove series** | Hides the video from the catalog without deleting it. **Removed movies** in the toolbar restores it. |

Renaming and deleting need a drive that can be written. A drive formatted as NTFS that was not removed safely may be mounted read only. Easy Movie then reports that the files could not be changed.

## Downloads

The download icon at the end of the toolbar opens **Downloads**, a torrent download manager.

- **Add magnet link** asks for a magnet link or the web address of a `.torrent` file. Typing a long link with the remote is impractical, so paste it from a phone with a remote app such as Kore or Yatse while the keyboard is open.
- **Add .torrent file** picks a `.torrent` file, for example one copied to a USB drive.
- **Change folder** chooses where downloads are saved. On LibreELEC, a folder on the SD card asks for confirmation first, since downloads write a lot and wear cards out. Use a USB drive or hard disk instead.
- The list shows each download with its progress, state, speed, connections, size and time left, and updates every two seconds. The header shows the total download and upload speeds.
- Select a download, or press **Menu**, to **Pause** or **Resume** it, **Remove from the list**, or **Remove and delete files**.

Downloads keep going after the screen is closed, while Kodi runs. When Kodi starts, unfinished downloads resume. Add the download folder as a video folder to see what you downloaded in the catalog.

Torrent downloads also upload to other people while they run. The upload speed is limited in the settings. You are responsible for what you download.

### Torrent engine

Easy Movie downloads with [Torrest](https://github.com/i96751414/torrest-cpp) 0.0.8, a torrent engine built on libtorrent with a REST API, released under the MIT license. Its executables for Linux (arm64, armv7, x64, x86), Android (arm64, arm, x64, x86), Windows (x64, x86) and macOS (x64, which Apple silicon Macs run with Rosetta) are in `resources/bin`, with its license and their SHA-256 checksums. Easy Movie copies the one of the device into its data folder, starts it as a separate process on port 61235 when **Downloads** opens or when Kodi starts with unfinished downloads, and stops it when Kodi quits. A failure of the engine does not stop Kodi.

## Managing lists

The list manager opens over the catalog, and the genres behind it are reloaded after every change.

- **Add list** adds a list from a web address or a file, or a folder with videos, and suggests a name.
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

## Movies and TV shows menus

When Kodi's movie library is empty, selecting **Movies** in Kodi's main menu opens Easy Movie instead of the empty video sources. When the TV show library is empty, **TV shows** opens Easy Movie on the **Series** group. Closing Easy Movie returns to the main menu. When a library has content, Kodi's own screens open as usual.

Turn off **Open Easy Movie from the Movies menu** or **Open Easy Movie from the TV shows menu** in the settings to keep Kodi's behavior. This works with the Estuary skin, whose Movies and TV shows entries Easy Movie recognizes.

## Settings

| Setting | Default | Purpose |
| --- | --- | --- |
| Open Easy Movie from the Movies menu | On | Open Easy Movie when **Movies** is selected in Kodi's main menu and the movie library is empty. |
| Open Easy Movie from the TV shows menu | On | Open Easy Movie on the series when **TV shows** is selected and the TV show library is empty. |
| Offer to remove movies that fail to play | On | Show the removal dialog after a failed playback. |
| Look up posters and details of folder videos on Cinemeta | On | Fetch posters and details of the movies and series of video folders. |
| Download folder | Not set | Folder for torrent downloads. **Downloads** asks for it the first time. |
| Upload limit (KB/s, 0 for no limit) | 200 | Maximum upload speed of torrent downloads. |
| Resume downloads when Kodi starts | On | Start the torrent engine with Kodi when there are unfinished downloads. |
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
| `favorites.json` | Favorite movies and series. |
| `progress.json` | Playback position and watched state of movies and episodes. |
| `metadata.json` | Cinemeta details of the movies and series of video folders. |
| `torrest/` | The torrent engine, its settings, log and saved downloads. |
| `repositories.json` | GitHub repositories, once the suggested one is changed. |

Easy Movie connects only to the addresses of your lists, streams and posters, to `api.github.com` and `raw.githubusercontent.com` when you search a repository, to `v3-cinemeta.strem.io` to look up the videos of folders, sending their titles, and, for torrent downloads, to the trackers and peers of the torrents you add. The lookups can be turned off in the settings. It sends no usage data.

## Known limitations

- A check confirms that a stream server answers, not that the movie plays. Movies that pass a check can still fail, and are then offered for removal after playback.
- Series are recognized by episode codes in the names. Episodes without a code are shown as movies.
- Kodi's own dialogs, such as confirmations, selection lists and the keyboard, use the style of the current skin.

## Disclaimer

Easy Movie does not provide any content. It plays the lists you add, and you are responsible for using only lists you are allowed to watch. The suggested repository lists public domain movies and is maintained by a third party, not by this project.

## Development

Easy Movie shares its design and most of its code with Easy Channel. Each add-on keeps its own copy, as the repository conventions ask for self-contained add-ons. `m3u.py`, `probe.py`, `github.py` and `storage.py` are the same modules, with the defaults and the `#EXTINF` duration that movies need. `watcher.py` also records progress, and `series.py` is specific to Easy Movie. `series.py`, `folders.py`, `cinemeta.py` and `torrents.py` do not import Kodi modules and can be tested with a regular Python 3 interpreter.

| Path | Purpose |
| --- | --- |
| `default.py` | Opens the main window. |
| `service.py` | Background service for the Movies and TV shows menus. |
| `resources/lib/gui.py` | Catalog, movie and series details, list manager and repository manager. |
| `resources/lib/series.py` | Episode recognition and grouping into series. |
| `resources/lib/folders.py` | Video folders: finds the videos and describes them as an M3U list. |
| `resources/lib/cinemeta.py` | Cinemeta search and details. |
| `resources/lib/torrents.py` | Torrent engine: starts Torrest and uses its API. |
| `resources/bin/` | Torrest executables for each platform, with their license and checksums. |
| `resources/lib/watcher.py` | Playback, progress and failure detection. |
| `resources/lib/m3u.py` | M3U parsing and writing. |
| `resources/lib/probe.py` | Stream checks. |
| `resources/lib/github.py` | GitHub repository search. |
| `resources/lib/storage.py` | Lists, cache, favorites and removed movies. |
| `resources/lib/movies_menu.py` | Movies and TV shows menu service. |
| `resources/skins/default/` | Window layouts and textures. |

Toolbar tools are declared in `TOOLS` in `resources/lib/gui.py`.

The window layouts are generated by `tools/generate_m3u_movies_skin.py` in the repository root, which reuses the palette, toolbar, genres and managers of `tools/generate_m3u_channels_skin.py`. A palette change in the Easy Channel generator applies to both add-ons after running both scripts.

The icon, fanart, header symbol and poster placeholder are drawn by `tools/generate_easy_movie_art.py`, with the colors and shapes of Easy Channel's artwork. It needs Pillow and the [Inter](https://rsms.me/inter/) font, released under the SIL Open Font License. Pass the folder that holds `Inter-Bold.ttf` and `Inter-Medium.ttf` as its argument.

## License

MIT. See [LICENSE](LICENSE).
