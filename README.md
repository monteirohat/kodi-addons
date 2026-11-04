<p align="center">
  <img src="repository.monteiromedia/resources/icon.png" alt="Monteiro" width="140">
</p>

<h1 align="center">Monteiro</h1>

<p align="center">
  Practical, open-source Kodi add-ons for LibreELEC and Raspberry Pi.<br>
  Watch M3U channels and movies the easy way, and control your media center from the couch.
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Kodi-21%20Omega-17B2E7" alt="Kodi 21 Omega">
  <img src="https://img.shields.io/badge/LibreELEC-12.2-3B8BFF" alt="LibreELEC 12.2">
  <img src="https://img.shields.io/badge/license-MIT-22272E" alt="MIT license">
</p>

<p align="center">
  <a href="#add-ons">Add-ons</a> ·
  <a href="#installation">Installation</a> ·
  <a href="#for-maintainers">For maintainers</a>
</p>

## Add-ons

<table>
  <tr>
    <td align="center" width="33%">
      <a href="script.m3u.channels/README.md"><img src="script.m3u.channels/resources/icon.png" alt="Easy Channel" width="120"></a>
      <h3>Easy Channel</h3>
      Live TV from M3U lists in a TV box style screen that keeps only the channels that work.
      <br><br>
      <a href="#easy-channel">Overview</a> · <a href="script.m3u.channels/README.md">Guide</a>
    </td>
    <td align="center" width="33%">
      <a href="script.m3u.movies/README.md"><img src="script.m3u.movies/resources/icon.png" alt="Easy Movie" width="120"></a>
      <h3>Easy Movie</h3>
      The movies and series of your M3U lists as a poster catalog, with seasons and Continue watching.
      <br><br>
      <a href="#easy-movie">Overview</a> · <a href="script.m3u.movies/README.md">Guide</a>
    </td>
    <td align="center" width="33%">
      <a href="script.hdmi.switcher/README.md"><img src="script.hdmi.switcher/resources/hdmi-switcher-icon.png" alt="HDMI Switcher" width="120"></a>
      <h3>HDMI Switcher</h3>
      Choose the active HDMI display of a Raspberry Pi 4 directly from Kodi.
      <br><br>
      <a href="#hdmi-switcher">Overview</a> · <a href="script.hdmi.switcher/README.md">Guide</a>
    </td>
  </tr>
</table>

### Easy Channel

<img src="script.m3u.channels/resources/icon.png" alt="Easy Channel" width="72" align="left">

**Add an M3U list in a few steps, browse channels by group, and remove the ones that stop working as soon as they fail.** No playlist or EPG configuration is needed.

<br clear="left">

- Groups on the left, channels in the middle, and details of the focused channel on the right.
- Lists from a web address, a file, or the M3U files of a GitHub repository, with suggested repositories of free, public channels.
- When a channel does not open, Easy Channel offers to remove it, and **Check channels** tests a whole group at once.
- A **Favorites** group at the top, search across all lists, and export of a clean M3U file.
- Selecting **TV** in Kodi's main menu opens Easy Channel.

![Easy Channel](script.m3u.channels/resources/screenshots/screenshot-01.jpg)

Install from **Monteiro > Video add-ons > Easy Channel**. Read the [Easy Channel guide](script.m3u.channels/README.md) for every feature and setting.

### Easy Movie

<img src="script.m3u.movies/resources/icon.png" alt="Easy Movie" width="72" align="left">

**Turn the movies and series of your M3U lists into a poster catalog.** Open a movie to see its details, or a series to pick a season and continue where you stopped.

<br clear="left">

- Genres on the left and six posters per row, with title and running time.
- Episodes grouped into series automatically, with seasons, episodes, watched marks and a **Continue** button.
- A **Continue watching** group, and resume of movies and episodes where you stopped.
- Playback controls in the style of streaming apps, with 10 second skips, subtitles and audio tracks, and subtitles from OpenSubtitles turned on automatically in your language.
- Lists from a web address, a file, or GitHub, with a suggested repository of public domain movies.
- The same list manager, checks, favorites and failure detection as Easy Channel, in the same design.
- Folders with your own videos, on the SD card, USB drives or network shares, with posters and details from Cinemeta.
- A catalog of the movies and series of Cinemeta, with **My list**, and Stremio addons added by their address, whose sources go to a torrent download manager or play at once.
- With an empty library, selecting **Movies** or **TV shows** in Kodi's main menu opens Easy Movie.

![Easy Movie](script.m3u.movies/resources/screenshots/screenshot-01.jpg)

Install from **Monteiro > Video add-ons > Easy Movie**. Read the [Easy Movie guide](script.m3u.movies/README.md) for every feature and setting.

### HDMI Switcher

<img src="script.hdmi.switcher/resources/hdmi-switcher-icon.png" alt="HDMI Switcher" width="72" align="left">

**Switch between a small HDMI display and an external monitor without touching the command line.** Pick a display, and Kodi restarts on it.

<br clear="left">

- Two display cards that show which display is active and which ones are connected, in the same dark design as Easy Channel and Easy Movie.
- Built for LibreELEC on Raspberry Pi 4, mapping the small display to `HDMI-A-1` and the external monitor to `HDMI-A-2`.
- Keeps your existing advanced settings and backs up the configuration file before the first change.
- Remembers the chosen display for future starts.

![HDMI Switcher](script.hdmi.switcher/resources/screenshots/screenshot-01.jpg)

HDMI Switcher needs a [one-time setup](script.hdmi.switcher/README.md#one-time-setup) that removes previous HDMI boot overrides. Install from **Monteiro > Program add-ons > HDMI Switcher**, and read the [HDMI Switcher guide](script.hdmi.switcher/README.md) for details.

> [!NOTE]
> Easy Channel and Easy Movie do not provide any content. They play the M3U lists you add, and you are responsible for using only lists you are allowed to watch. The suggested GitHub repositories collect free, public channels and public domain movies, and are maintained by third parties.

## Installation

Register the **Monteiro** repository in Kodi once, and every add-on and update installs from it.

1. Download [repository.monteiromedia-1.0.5.zip](repository/repository.monteiromedia/repository.monteiromedia-1.0.5.zip) and copy it to a USB drive or a folder your Kodi device can reach.
2. In Kodi, enable **Settings > System > Add-ons > Unknown sources**, then use **Add-ons > Install from zip file** to install the ZIP.
3. Open **Add-ons > Install from repository > Monteiro** and install the add-ons you want.

### Register the repository in Kodi

1. On GitHub, open this repository's **Code** tab and select the branch where **Publish Kodi repository** completed successfully.
2. Open **repository > repository.monteiromedia** and select **repository.monteiromedia-1.0.5.zip**. You can also open the [repository installation ZIP](repository/repository.monteiromedia/repository.monteiromedia-1.0.5.zip) directly from this README.
3. On the file page, click **Download raw file** to download the ZIP. The full path from the repository root is `repository/repository.monteiromedia/repository.monteiromedia-1.0.5.zip`.
4. Copy the downloaded ZIP to a USB drive or a folder accessible from your Kodi device.
5. In Kodi, enable **Settings > System > Add-ons > Unknown sources**.
6. Open **Add-ons > Install from zip file**, browse to the location used in step 4, and select **repository.monteiromedia-1.0.5.zip**. Wait for the **Monteiro** repository installation notification. Registering the repository is a one-time step.
7. Open **Add-ons > Install from repository > Monteiro** and choose an add-on. HDMI Switcher is under **Program add-ons**, and Easy Channel and Easy Movie are under **Video add-ons**.
8. Select **Install** and wait for installation to finish.

Further add-ons and updates are installed through **Monteiro**. Enable automatic updates for the add-on if desired. If an update is not visible yet, open the repository context menu and select **Check for updates**.

## For maintainers

### Available packages

| Add-on | ID | Purpose |
| --- | --- | --- |
| [Easy Channel](script.m3u.channels/README.md) | `script.m3u.channels` | Add M3U lists in one step and remove channels that do not work. |
| [Easy Movie](script.m3u.movies/README.md) | `script.m3u.movies` | Browse the movies of M3U lists and video folders as a poster catalog, explore the Cinemeta catalog with Stremio addons, and download torrents. |
| [HDMI Switcher](script.hdmi.switcher/README.md) | `script.hdmi.switcher` | Select the active HDMI display and restart Kodi. |
| Monteiro | `repository.monteiromedia` | Register this repository in Kodi for installation and updates. |

### Publish on GitHub

1. Upload the contents of this folder to a public GitHub repository using the `main` or `master` branch, including `.github`, `.gitignore`, and the generated `repository` directory.
2. Open **Actions** and wait for **Publish Kodi repository** to complete. The workflow generates package URLs from the actual GitHub owner, repository name, and branch.
3. If the workflow reports a permissions error, enable **Read and write permissions** under **Settings > Actions > General > Workflow permissions**. Branch protection must allow the workflow to push its generated commit.
4. In GitHub, open the **Code** tab and download the generated `repository/repository.monteiromedia/repository.monteiromedia-1.0.5.zip` after the workflow succeeds. The ZIP is committed to the repository; it is listed under **Code**, rather than as an Actions artifact.

The initial generated files use `monteirohat/kodi-addons` and the `main` branch. The first workflow run adjusts these values to the actual repository location before installation. GitHub Pages is optional; Kodi downloads files directly from GitHub Raw.

### Publish an add-on update

1. Modify its source code and increment its version in `addon.xml`.
2. Commit and push to `main` or `master`.
3. The workflow packages the add-ons, updates `addons.xml` and its checksum, and commits the generated files.
4. Kodi detects the updated catalog and offers the new version according to its update settings.

Add another self-contained top-level directory with its own `addon.xml` to publish another add-on. The folder name must match the add-on ID. The builder discovers these folders automatically and retains older installation packages.

### Repository identity

The name shown in Kodi is **Monteiro**. The technical ID remains `repository.monteiromedia` so existing installations can receive this rename through a normal repository update. Version 1.0.3 added repository artwork and detailed metadata, version 1.0.4 added Easy Channel to its description, and version 1.0.5 adds Easy Movie. HDMI Switcher keeps its `script.hdmi.switcher` ID, and version 1.1.0 brings its display picker and icon in line with the other add-ons.

### Repository layout

| Path | Purpose |
| --- | --- |
| `script.m3u.channels/` | Easy Channel source and documentation. |
| `script.m3u.movies/` | Easy Movie source and documentation. |
| `script.hdmi.switcher/` | HDMI Switcher source and documentation. |
| `repository.monteiromedia/` | Repository registration add-on. |
| `repository/addons.xml` | Generated Kodi add-on catalog. |
| `repository/addons.xml.md5` | Catalog change indicator used by Kodi. |
| `repository/<addon-id>/` | Versioned installation ZIPs, SHA-256 files, and published artwork. |
| `tools/build_repository.py` | Catalog and package generator using Python's standard library. |
| `tools/generate_m3u_channels_skin.py` | Generator of the Easy Channel window layouts and of the theme shared with Easy Movie. |
| `tools/generate_m3u_movies_skin.py` | Generator of the Easy Movie window layouts. |
| `tools/generate_easy_channel_art.py` | Generator of the Easy Channel icon, fanart, and header symbol. |
| `tools/generate_easy_movie_art.py` | Generator of the Easy Movie icon, fanart, header symbol, and poster placeholder. |
| `tools/generate_hdmi_switcher_skin.py` | Generator of the HDMI Switcher window layout. |
| `tools/generate_hdmi_switcher_art.py` | Generator of the HDMI Switcher icon, fanart, header symbol, and display icon. |
| `.github/workflows/publish-repository.yml` | Build and publish workflow. |

Package hash headers are disabled in the Kodi repository definition because GitHub Raw does not provide Kodi's `content-sha256` headers. SHA-256 sidecars are provided for manual verification. Downloads use HTTPS.

### Build locally

From the repository root, run

```sh
python3 tools/build_repository.py --base-url https://raw.githubusercontent.com/monteirohat/kodi-addons/main/repository
```

Replace the owner, repository name, and branch when building for another location. Commit the generated `repository` directory and the updated registration manifest. The GitHub workflow performs this step automatically on each push.

### Artwork

Every add-on declares an opaque 512 by 512 PNG icon and a 1280 by 720 JPEG fanart in its `addon.xml`. The builder publishes them at their catalog paths so Kodi can display them before installation. If old artwork remains after an update, restart Kodi.

The repository icon is an M monogram with a subtle play-shaped cutout, and its fanart shows quiet angular ribbons. Both use a navy, cyan, and blue palette and were created with OpenAI image generation.

The add-on icons share one identity: blue rounded displays with white symbols on a dark background, matching the add-on interfaces. Easy Channel shows a TV with a playlist, Easy Movie a clapperboard, and HDMI Switcher two displays with switching arrows. Their icons and fanart are drawn by scripts in `tools`, as described in the [Easy Channel](script.m3u.channels/README.md#development), [Easy Movie](script.m3u.movies/README.md#development) and [HDMI Switcher](script.hdmi.switcher/README.md#artwork-and-layout) READMEs.

### Development conventions

- Use English for identifiers, comments, documentation, filenames, and interface text.
- Keep each add-on self-contained and match its directory name to its ID.
- Increment `addon.xml` versions before publishing changed packages.
- Preserve existing user settings when making configuration changes.
- Increase the repository add-on version when changing its public URLs or metadata.

### Validation

Local checks cover metadata, package structure, checksums, deterministic builds, and the previously tested HDMI configuration logic. The user confirmed installation and HDMI display switching on the target Raspberry Pi with HDMI Switcher 1.0.4. Version 1.1.0 was tested on the device up to the switch confirmation, as described in its [README](script.hdmi.switcher/README.md#validation).

Easy Channel was tested on LibreELEC 12.2.1 with Kodi 21.3 on a Raspberry Pi 4 by driving the interface with remote control commands and screenshots. The tests covered adding lists from a file and from GitHub, browsing groups, favorites, removing and restoring channels, failure detection for missing streams and unreachable servers, group checks, the list and repository managers, and the TV menu. Adding a repository by typing its name was only tested outside Kodi.

Easy Movie was tested on the same device with the public domain list from GitHub. The tests covered the first-use list manager, adding lists from GitHub, the poster catalog and its navigation, movie details, playback, favorites, removal after a failed playback, genre checks, and the Movies menu. Later versions were tested with a video folder on a USB drive (posters from Cinemeta, renaming), torrent downloads of a Creative Commons film (pause, removal, upload limit), the Cinemeta catalog (categories, search, pages, My list, titles found in the lists), adding and removing Stremio addons, and the sources panel, including downloading one file of a pack and the warning for a full folder. The playback controls were tested with a movie from a USB hard drive: showing and hiding, 10 second skips, pause, choosing subtitle and audio tracks, and OpenSubtitles subtitles, turned on automatically and picked in the panel. Playing a direct link from an addon was not tested.

## License

MIT. See [LICENSE](LICENSE).
