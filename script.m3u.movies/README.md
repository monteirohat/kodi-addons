![Easy Movie](resources/fanart.jpg)

# Easy Movie

Easy Movie is a Kodi add-on that shows the movies and series of your M3U lists as a poster catalog. Add a list in a few steps, browse movies by genre with the remote, open a movie to see its details, and remove movies that no longer work as soon as they fail. It is the movie companion of [Easy Channel](../script.m3u.channels/README.md), with the same design, list manager and tools.

## Features

- Poster catalog with genres on the left and six posters per row, showing title and running time.
- Episodes such as `Show S01E02`, `Show 1x02` or `Show T01 E02` are grouped into one series card, with seasons, episodes and a **Continue** button for the next episode.
- Watched movies and episodes get a check mark, movies and episodes stopped midway resume where you stopped, and a **Continue watching** group lists what is in progress.
- Movie details with a large poster, genre, running time and source list, and **Play**, **Favorite** and **Remove movie** buttons.
- Add lists from a web address, a file on the device or network, or the M3U files of a GitHub repository. No playlist configuration is required.
- Browse the movies and series of Cinemeta, the catalog of Stremio, by popularity, release year and genre, search it, and keep titles in **My list**. Titles that are also in your lists can be played from there.
- Add Stremio addons by their address, as in Stremio. Their catalogs join the catalog, and their sources open in a side panel: a torrent goes to Downloads, and a direct link plays at once.
- Download torrents from magnet links, `.torrent` files or the catalog into a folder you choose, with a download list that shows progress, speed, time left and the free space of the folder.
- Add folders with your own video files, on the SD card, a USB drive or a network share. Posters and details come from Cinemeta, and files can be renamed or deleted from the catalog.
- Playback controls in the style of streaming apps: play and pause between back and forward 10 seconds, and the subtitle and audio tracks in a side panel.
- When a movie fails to open, or stops right after starting, Easy Movie offers to remove it.
- **Check movies** tests a whole genre at once and removes the movies that do not respond.
- **Favorites** genre at the top, kept across list updates.
- Search across all lists, restore removed movies, and export a clean M3U file for other apps.
- With an empty library, selecting **Movies** or **TV shows** in Kodi's main menu opens Easy Movie, on the movies or on the series.
- Interface in English and Brazilian Portuguese.

## Screenshots

| Your lists | Movie details | GitHub repositories |
| --- | --- | --- |
| ![Your lists](resources/screenshots/screenshot-01.jpg) | ![Movie details](resources/screenshots/screenshot-02.jpg) | ![GitHub repositories](resources/screenshots/screenshot-03.jpg) |

| Catalog | Catalog movie | Catalog series | Addons |
| --- | --- | --- | --- |
| ![Catalog](resources/screenshots/screenshot-04.jpg) | ![Catalog movie](resources/screenshots/screenshot-05.jpg) | ![Catalog series](resources/screenshots/screenshot-06.jpg) | ![Addons](resources/screenshots/screenshot-07.jpg) |

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

The groups start with **Continue watching**, with movies stopped midway and series with episodes left, most recent first, followed by **Favorites**, **All movies** and **Series**. **All movies** and the genres show the newest movies first, such as a finished download. Movies that arrived together keep the order of their lists. Easy Movie opens on **Continue watching** when it has items.

### Playback controls

Movies and episodes play with the controls of Easy Movie, in the style of streaming apps. They show the title, a time bar, **Subtitles** and **Audio** on the sides, and play and pause between back and forward 10 seconds. The controls hide after 5 seconds without a key, and stay while the movie is paused.

| Key | Controls hidden | Controls shown |
| --- | --- | --- |
| **OK**, **Up**, **Down**, **Info** or **Menu** | Show the controls. | Use the highlighted button. |
| **Left / Right** | Go back or forward 10 seconds, showing the time bar. Presses add up, so three presses skip 30 seconds. | Move between the buttons. |
| **Back** | Stop the movie. Its progress is kept. | Hide the controls. |
| **Play / Pause**, **Stop**, volume | Work as usual in Kodi. | Work as usual in Kodi. |

**Subtitles** lists the subtitles of the video and subtitle files next to it, such as `Movie.pt-BR.srt`, with **Off** first. **Audio** lists the audio tracks, such as the Portuguese and English tracks of a dual audio release. The current track has a check mark. Select a track with **OK**, or close the panel with **Back**.

Turn off **Easy Movie player controls** in the settings to use the controls of the Kodi skin instead.

### Toolbar

The toolbar above the genres shows the name of the focused tool.

| Icon | Tool |
| --- | --- |
| Gear | **Manage lists** opens the list manager. |
| Magnifier | **Search movies** by title across all lists. |
| List | **Catalog** opens the Cinemeta catalog. See [Catalog](#catalog). |
| Check mark | **Check movies** tests every movie of the shown genre. The tool shows the genre name. Movies that do not respond can be removed all at once or one by one. |
| Download arrow | **Downloads** opens the torrent download manager. See [Downloads](#downloads). |

### Movies that do not work

Before playing, Easy Movie checks that the stream answers, with a **Connecting** dialog that can be cancelled. The details window stays open meanwhile, so another episode can be picked right away. Kodi itself waits for an unresponsive server on its interface thread, which froze the screen for half a minute, so streams that do not answer are reported before Kodi tries them. A stream that answers is checked in about two seconds, and most open without the dialog appearing. A stream that does not answer is reported within 8 seconds, the **Check timeout** setting, with **Remove**, **Cancel** or **Play anyway**.


When a movie fails to open, stops before it starts, or ends within a minute of starting, Easy Movie asks whether to **Remove** it, **Keep** it, or **Try again**. Kodi stops waiting for an unreachable server after 8 seconds, and a movie still opening after 15 seconds is checked, so a dead link is reported in about 20 seconds. Stopping a movie after it started is never treated as a failure.

The original M3U is never changed. Removed movies are recorded by stream address and hidden from every list, so a removal keeps working when a web list is downloaded again. Restore a movie from **Removed movies** in the list manager if it works again later. **Export clean M3U** in the list manager saves a list without its removed movies.

Genres are taken from `group-title`. Movies without a genre, or with a placeholder such as `Undefined`, are listed together under **Other** at the end of the genres. Posters come from `tvg-logo`. Movies without a poster show a clapperboard.

## Video folders

Select **Add list** > **Folder with videos** to add a folder with your own video files, such as `/storage/videos`, a USB drive under `/var/media`, or a network share such as `smb://`. The folder becomes a list like the others. A folder on this device, such as a USB drive, is read again each time Easy Movie opens and when the Catalog or Downloads closes, so new videos and finished downloads show at once. A network share is read again with the web lists, or with **Update list** after you add or remove files.

- Each first level subfolder with more than one movie or series becomes a genre, such as `Movies` or `Cartoons`. The folder of a single movie or series, as a torrent download makes, is not a genre.
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
| **Remove movie** / **Remove series** | Hides the video from the catalog without deleting it. **Removed movies** in the list manager restores it. |

Renaming and deleting need a drive that can be written. A drive formatted as NTFS that was not removed safely may be mounted read only. Easy Movie then reports that the files could not be changed.

## Catalog

The list icon in the toolbar opens **Catalog**, the movies and series of [Cinemeta](https://v3-cinemeta.strem.io), the metadata service of Stremio. It has the layout of the main screen, with **Movies** and **Series** tabs above the categories and the puzzle piece button of [Addons](#addons) next to them.

| Category | Content |
| --- | --- |
| **My list** | Titles you saved, with their count. |
| **Search** | Asks for a title and shows the matches. |
| **Popular** | The most watched titles right now. |
| **Featured** | Titles picked by Cinemeta. |
| **New in** the current year | Titles released this year. |
| Catalogs of addons | The catalogs of the addons you added, after the ones of Cinemeta. The header shows the addon name. |
| Genres | Popular titles of each genre, from Action to Western. Series also have Reality show, Talk show and Game show. |

| Key | On the tabs and the addons button | On the categories | On a poster |
| --- | --- | --- | --- |
| **Left / Right** | Switch between **Movies** and **Series**, and reach the addons button. Right on the addons button moves to the posters. | Right moves to the posters. | Move between posters. Left in the first column returns to the categories. |
| **Up / Down** | Down moves to the categories. | Move between categories. The posters follow the highlighted one. | Move between rows. Up on the first row moves to the tabs. |
| **OK** | Open **Addons** from its button. | Move to the posters, or ask for a title on **Search**. | Open the details. |
| **Menu** | | | Add to or remove from **My list**. |
| **Back** | Close the catalog. | Close the catalog. | Return to the categories. |

Pages have about 50 titles, and the next page loads when the selection nears the last row. Loaded categories are kept while the catalog is open, so returning to one is instant.

Select a poster to open its details: poster, year, IMDb rating, genres, running time, director, cast and description. A series also shows its seasons and episodes with their air dates, and the description below the poster follows the highlighted episode. **Add to My list** saves the title, which then shows a star, and **Menu** on a poster does the same without opening it.

When the title is also in your lists, found by the Cinemeta details of a video folder or by name and year, the details show **In your lists** with the list name and a **Play** button, which opens the movie or series from your lists. Descriptions are in English.

### Sources

When an addon that gives sources is installed, movie details have a **Sources** button, and selecting an episode of a series does the same for that episode. A panel slides in from the right with the sources of every addon, asked at the same time and listed as they answer, in the order the addons were added.

Each source shows its file or release name, and whether it is a **Torrent** or a **Direct link**, with its quality, audio languages, size, seeds and addon when the addon gives them. Addons mark languages with flags, shown as language codes, as in `EN RU` or `PT-BR`.

- **Torrent**: goes to [Downloads](#downloads), into the download folder. When it is a pack of a whole season or collection, only the chosen file is downloaded. Easy Movie waits for the torrent details, then stops the other files.
- **Direct link**: plays at once, with the request headers the addon asks for.

**Left** or **Back** closes the panel. When the download folder has less free space than the torrent needs, Easy Movie names the folder, its free space and the size of the torrent, and offers **Change folder**.

### Addons

The puzzle piece button next to the tabs opens **Addons**, the Stremio addons the catalog uses. A Stremio addon is a web address that describes itself in a `manifest.json` file and answers with catalogs, details, sources or subtitles.

- **Cinemeta** is built in and always listed first.
- **Add addon** asks for the address of an addon. Paste its `manifest.json` address, the address without `manifest.json`, or a `stremio://` install link. Typing an address with the remote is slow, so paste it from a phone with [Kore](https://kodi.wiki/view/Kore) or Yatse while the keyboard is open.
- Each addon shows its logo, version, what it gives (catalogs, details, sources, subtitles), for which types, and its server.
- Select an addon to **Update addon**, which reads its manifest again, or **Remove addon**.
- An addon that must be configured first, such as one that asks for a language or an account, shows the address of its configuration page. Configure it there on a phone or computer, and add the address it gives.

The catalogs of an addon that can be shown without a search or a genre appear in the categories: catalogs of movies in **Movies**, and catalogs of series and anime in **Series**. Their titles open with the details of the addon when it gives them, or of Cinemeta. The sources of addons are listed in [Sources](#sources).

## Downloads

The download icon at the end of the toolbar opens **Downloads**, a torrent download manager.

- **Add magnet link** asks for a magnet link or the web address of a `.torrent` file. Typing a long link with the remote is impractical, so paste it from a phone with a remote app such as Kore or Yatse while the keyboard is open.
- **Add .torrent file** picks a `.torrent` file, for example one copied to a USB drive.
- **Change folder** chooses where downloads are saved. On LibreELEC, a folder on the SD card asks for confirmation first, since downloads write a lot and wear cards out. Use a USB drive or hard disk instead.
- The list shows each download with its progress, state, speed, connections, size and time left, and updates every two seconds. The header shows the total download and upload speeds, and the folder line its free space.
- The engine pauses downloads when the folder is full. They then show **No space left in the folder** instead of paused, and resume after space is freed and they are resumed.
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
- **Removed movies** lists what you removed. Select movies to restore them.
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
| Easy Movie player controls | On | Show the controls of Easy Movie over movies and episodes. Off uses the controls of the Kodi skin. |
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
| `added.json` | When each movie first appeared in the lists, for showing the newest first. |
| `metadata.json` | Cinemeta details of the movies and series of video folders. |
| `watchlist.json` | Titles saved to **My list** in the catalog. |
| `addons.json` | Stremio addons added in the catalog, with their addresses and manifests. |
| `torrest/` | The torrent engine, its settings, log and saved downloads. |
| `repositories.json` | GitHub repositories, once the suggested one is changed. |

Easy Movie connects only to the addresses of your lists, streams and posters, to `api.github.com` and `raw.githubusercontent.com` when you search a repository, to `v3-cinemeta.strem.io` and `cinemeta-catalogs.strem.io` to look up the videos of folders, sending their titles, and to show the catalog and its searches, to the addresses of the Stremio addons you add, and, for torrent downloads, to the trackers and peers of the torrents you add. The lookups can be turned off in the settings. It sends no usage data.

## Known limitations

- A check confirms that a stream server answers, not that the movie plays. Movies that pass a check can still fail, and are then offered for removal after playback.
- Series are recognized by episode codes in the names. Episodes without a code are shown as movies.
- Kodi's own dialogs, such as confirmations, selection lists and the keyboard, use the style of the current skin.
- The catalog shows catalogs of movies, series and anime. Catalogs of live TV and catalogs that need a search or a genre are left out. Addon searches are not used yet: **Search** searches Cinemeta.
- Direct links from addons play without saving progress, and their titles are not marked as watched. They also play with the controls of the Kodi skin.
- While a movie is paused, the Kodi skin also shows its own time bar at the top of the screen. Subtitles are drawn behind the playback controls while these are shown.
- Downloading only one file of a pack needs Easy Movie to stay open until the torrent details arrive, usually a few seconds. When it is closed before, the whole pack downloads. Remove it in **Downloads** and choose the source again.

## Disclaimer

Easy Movie does not provide any content. It plays the lists you add, and you are responsible for using only lists you are allowed to watch. The suggested repository lists public domain movies and is maintained by a third party, not by this project.

The catalog comes with Cinemeta only, which gives posters and details, not videos. Easy Movie includes no addon with sources. The Stremio addons you add, and what you download or play from them, are your choice and your responsibility.

## Development

Easy Movie shares its design and most of its code with Easy Channel. Each add-on keeps its own copy, as the repository conventions ask for self-contained add-ons. `m3u.py`, `probe.py`, `github.py` and `storage.py` are the same modules, with the defaults and the `#EXTINF` duration that movies need. `watcher.py` also records progress, and `series.py` is specific to Easy Movie. `series.py`, `folders.py`, `cinemeta.py`, `stremio.py` and `torrents.py` do not import Kodi modules and can be tested with a regular Python 3 interpreter.

| Path | Purpose |
| --- | --- |
| `default.py` | Opens the main window. |
| `service.py` | Background service for the Movies and TV shows menus. |
| `resources/lib/gui.py` | Main window, movie and series details, Cinemeta catalog, downloads, list manager and repository manager. |
| `resources/lib/series.py` | Episode recognition and grouping into series. |
| `resources/lib/folders.py` | Video folders: finds the videos and describes them as an M3U list. |
| `resources/lib/cinemeta.py` | Cinemeta catalogs, search, details and episodes. |
| `resources/lib/stremio.py` | Stremio addons: manifests, catalogs, details and sources. |
| `resources/lib/torrents.py` | Torrent engine: starts Torrest and uses its API. |
| `resources/bin/` | Torrest executables for each platform, with their license and checksums. |
| `resources/lib/watcher.py` | Playback, progress and failure detection. |
| `resources/lib/controls.py` | Playback controls over the video, with the subtitle and audio tracks. |
| `resources/lib/m3u.py` | M3U parsing and writing. |
| `resources/lib/probe.py` | Stream checks. |
| `resources/lib/github.py` | GitHub repository search. |
| `resources/lib/storage.py` | Lists, cache, favorites, removed movies, progress, Cinemeta details, My list and addons. |
| `resources/lib/movies_menu.py` | Movies and TV shows menu service. |
| `resources/skins/default/` | Window layouts and textures. |

Toolbar tools are declared in `TOOLS` in `resources/lib/gui.py`.

The window layouts are generated by `tools/generate_m3u_movies_skin.py` in the repository root, which reuses the palette, toolbar, genres and managers of `tools/generate_m3u_channels_skin.py`. A palette change in the Easy Channel generator applies to both add-ons after running both scripts.

The icon, fanart, header symbol and poster placeholder are drawn by `tools/generate_easy_movie_art.py`, with the colors and shapes of Easy Channel's artwork. It needs Pillow and the [Inter](https://rsms.me/inter/) font, released under the SIL Open Font License. Pass the folder that holds `Inter-Bold.ttf` and `Inter-Medium.ttf` as its argument.

## License

MIT. See [LICENSE](LICENSE).
