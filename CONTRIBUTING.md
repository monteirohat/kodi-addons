# Contributing

Thank you for helping improve the Monteiro add-ons. This guide covers reporting problems, changing an add-on, and building and publishing the Kodi repository.

## Reporting problems and ideas

- Use the [bug report](https://github.com/monteirohat/kodi-addons/issues/new?template=bug_report.yml) form for something that does not work. Include the add-on version, your Kodi and LibreELEC versions, and the steps that lead to the problem.
- Use the [suggestion](https://github.com/monteirohat/kodi-addons/issues/new?template=feature_request.yml) form for new features.
- Ask questions and share tips in [Discussions](https://github.com/monteirohat/kodi-addons/discussions).
- Do not paste list addresses, user names or passwords. Many M3U and addon addresses contain credentials.

To share a Kodi log, enable **Settings > System > Logging > Enable debug logging**, reproduce the problem, and upload `kodi.log` with the **Kodi Logfile Uploader** add-on. Paste the link it shows in the report.

## Pull requests

1. Keep each change focused on one add-on or one tool.
2. Follow the [development conventions](#development-conventions) below.
3. Increment the add-on version in its `addon.xml` and describe the change in its `<news>`.
4. Describe how you tested the change, and on which device.

## Available packages

| Add-on | ID | Purpose |
| --- | --- | --- |
| [Easy Channel](script.m3u.channels/README.md) | `script.m3u.channels` | Add M3U lists in one step and remove channels that do not work. |
| [Easy Movie](script.m3u.movies/README.md) | `script.m3u.movies` | Browse the movies of M3U lists and video folders as a poster catalog, explore the Cinemeta catalog with Stremio addons, and download torrents. |
| [HDMI Switcher](script.hdmi.switcher/README.md) | `script.hdmi.switcher` | Select the active HDMI display and restart Kodi. |
| [Easy Files](script.easy.files/README.md) | `script.easy.files` | Browse drives and folders, and copy, move, rename and delete files. |
| [Easy Picture](script.easy.picture/README.md) | `script.easy.picture` | Show the photos of your folders in a gallery, by album, and each one in full screen. |
| Monteiro | `repository.monteiromedia` | Register this repository in Kodi for installation and updates. |

## Publish on GitHub

1. Upload the contents of this folder to a public GitHub repository using the `main` or `master` branch, including `.github`, `.gitignore`, and the generated `repository` directory.
2. Open **Actions** and wait for **Publish Kodi repository** to complete. The workflow generates package URLs from the actual GitHub owner, repository name, and branch.
3. If the workflow reports a permissions error, enable **Read and write permissions** under **Settings > Actions > General > Workflow permissions**. Branch protection must allow the workflow to push its generated commit.
4. In GitHub, open the **Code** tab and download the generated `repository/repository.monteiromedia/repository.monteiromedia-1.0.5.zip` after the workflow succeeds. The ZIP is committed to the repository; it is listed under **Code**, rather than as an Actions artifact.

The initial generated files use `monteirohat/kodi-addons` and the `main` branch. The first workflow run adjusts these values to the actual repository location before installation. Kodi downloads the catalog and packages from GitHub Raw.

The workflow also publishes the installation site on GitHub Pages, at `https://monteirohat.github.io/kodi-addons/`, for installing by URL. Set **Settings > Pages > Source** to **GitHub Actions** once. `tools/build_pages.py` builds the site from the `repository` directory: an index page in every folder with links that Kodi lists, and a copy of the repository ZIP at the root.

## Publish an add-on update

1. Modify its source code and increment its version in `addon.xml`.
2. Commit and push to `main` or `master`.
3. The workflow packages the add-ons, updates `addons.xml` and its checksum, and commits the generated files.
4. Kodi detects the updated catalog and offers the new version according to its update settings.

Add another self-contained top-level directory with its own `addon.xml` to publish another add-on. The folder name must match the add-on ID. The builder discovers these folders automatically and retains older installation packages.

## Repository identity

The name shown in Kodi is **Monteiro**. The technical ID remains `repository.monteiromedia` so existing installations can receive this rename through a normal repository update. Version 1.0.3 added repository artwork and detailed metadata, version 1.0.4 added Easy Channel to its description, and version 1.0.5 adds Easy Movie. HDMI Switcher keeps its `script.hdmi.switcher` ID, and version 1.1.0 brings its display picker and icon in line with the other add-ons.

## Repository layout

| Path | Purpose |
| --- | --- |
| `script.m3u.channels/` | Easy Channel source and documentation. |
| `script.m3u.movies/` | Easy Movie source and documentation. |
| `script.hdmi.switcher/` | HDMI Switcher source and documentation. |
| `script.easy.files/` | Easy Files source and documentation. |
| `script.easy.picture/` | Easy Picture source and documentation. |
| `repository.monteiromedia/` | Repository registration add-on. |
| `repository/addons.xml` | Generated Kodi add-on catalog. |
| `repository/addons.xml.md5` | Catalog change indicator used by Kodi. |
| `repository/<addon-id>/` | Versioned installation ZIPs, SHA-256 files, and published artwork. |
| `tools/build_repository.py` | Catalog and package generator using Python's standard library. |
| `tools/build_pages.py` | Generator of the GitHub Pages installation site from the `repository` directory. |
| `skin.monteiro/` | Monteiro skin, generated by `tools/generate_monteiro_skin.py`. |
| `tools/generate_social_preview.py` | Generator of `.github/social-preview.png`, the image shown when the repository link is shared. |
| `tools/generate_m3u_channels_skin.py` | Generator of the Easy Channel window layouts and of the theme shared with Easy Movie. |
| `tools/generate_m3u_movies_skin.py` | Generator of the Easy Movie window layouts. |
| `tools/generate_easy_channel_art.py` | Generator of the Easy Channel icon, fanart, and header symbol. |
| `tools/generate_easy_movie_art.py` | Generator of the Easy Movie icon, fanart, header symbol, and poster placeholder. |
| `tools/generate_easy_files_skin.py` | Generator of the Easy Files window layouts. |
| `tools/generate_easy_files_art.py` | Generator of the Easy Files icon, fanart, header symbol and file icons. |
| `tools/generate_easy_picture_skin.py` | Generator of the Easy Picture window layouts. |
| `tools/generate_easy_picture_art.py` | Generator of the Easy Picture icon, fanart, header symbol and toolbar icons. |
| `tools/generate_hdmi_switcher_skin.py` | Generator of the HDMI Switcher window layout. |
| `tools/generate_hdmi_switcher_art.py` | Generator of the HDMI Switcher icon, fanart, header symbol, and display icon. |
| `.github/workflows/publish-repository.yml` | Build and publish workflow, including the GitHub Pages site. |
| `.github/ISSUE_TEMPLATE/` | Forms for bug reports and suggestions. |

Package hash headers are disabled in the Kodi repository definition because GitHub Raw does not provide Kodi's `content-sha256` headers. SHA-256 sidecars are provided for manual verification. Downloads use HTTPS.

## Build locally

From the repository root, run

```sh
python3 tools/build_repository.py --base-url https://raw.githubusercontent.com/monteirohat/kodi-addons/main/repository
```

Replace the owner, repository name, and branch when building for another location. Commit the generated `repository` directory and the updated registration manifest. The GitHub workflow performs this step automatically on each push.

## Artwork

Every add-on declares an opaque 512 by 512 PNG icon and a 1280 by 720 JPEG fanart in its `addon.xml`. The builder publishes them at their catalog paths so Kodi can display them before installation. If old artwork remains after an update, restart Kodi.

The repository icon is an M monogram with a subtle play-shaped cutout, and its fanart shows quiet angular ribbons. Both use a navy, cyan, and blue palette and were created with OpenAI image generation.

The add-on icons share one identity: blue rounded displays with white symbols on a dark background, matching the add-on interfaces. Easy Channel shows a TV with a playlist, Easy Movie a clapperboard, and HDMI Switcher two displays with switching arrows. Their icons and fanart are drawn by scripts in `tools`, as described in the [Easy Channel](script.m3u.channels/README.md#development), [Easy Movie](script.m3u.movies/README.md#development) and [HDMI Switcher](script.hdmi.switcher/README.md#artwork-and-layout) READMEs.

## Social preview

`.github/social-preview.png` is the 1280 by 640 image that GitHub shows when the repository link is shared. It shows the icons of the three add-ons over the repository fanart. After changing an icon, run `python3 tools/generate_social_preview.py path/to/inter/extras/ttf` and upload the new image in **Settings > General > Social preview**.

## Monteiro skin

`skin.monteiro` is written from scratch and released under the MIT license, so anyone can use, change and sell it. Its windows are generated by `tools/generate_monteiro_skin.py`, with the palette of the add-ons. Run it with the folder that holds `NotoSans-Regular.ttf`, `NotoSans-Bold.ttf` and `OFL.txt` from the [Noto project](https://github.com/notofonts/latin-greek-cyrillic).

Do not copy files or parts of files from Estuary or other skins, including images. Estuary is licensed under the GPL and CC BY-SA, and a copy would bring those licenses into the skin. Reading another skin to learn which window files, control ids and behaviors Kodi expects is fine; then write your own version.

## Development conventions

- Use English for identifiers, comments, documentation, filenames, and interface text.
- Keep each add-on self-contained and match its directory name to its ID.
- Increment `addon.xml` versions before publishing changed packages.
- Preserve existing user settings when making configuration changes.
- Increase the repository add-on version when changing its public URLs or metadata.

## Validation

Local checks cover metadata, package structure, checksums, deterministic builds, and the previously tested HDMI configuration logic. The user confirmed installation and HDMI display switching on the target Raspberry Pi with HDMI Switcher 1.0.4. Version 1.1.0 was tested on the device up to the switch confirmation, as described in its [README](script.hdmi.switcher/README.md#validation).

Easy Channel was tested on LibreELEC 12.2.1 with Kodi 21.3 on a Raspberry Pi 4 by driving the interface with remote control commands and screenshots. The tests covered adding lists from a file and from GitHub, browsing groups, favorites, removing and restoring channels, failure detection for missing streams and unreachable servers, group checks, the list and repository managers, and the TV menu. Adding a repository by typing its name was only tested outside Kodi.

Easy Movie was tested on the same device with the public domain list from GitHub. The tests covered the first-use list manager, adding lists from GitHub, the poster catalog and its navigation, movie details, playback, favorites, removal after a failed playback, genre checks, and the Movies menu. Later versions were tested with a video folder on a USB drive (posters from Cinemeta, renaming), torrent downloads of a Creative Commons film (pause, removal, upload limit), the Cinemeta catalog (categories, search, pages, My list, titles found in the lists), adding and removing Stremio addons, and the sources panel, including downloading one file of a pack and the warning for a full folder. The playback controls were tested with a movie from a USB hard drive: showing and hiding, 10 second skips, pause, choosing subtitle and audio tracks, and OpenSubtitles subtitles, turned on automatically and picked in the panel. Playing a direct link from an addon was not tested.
