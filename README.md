![Monteiro repository icon](repository.monteiromedia/resources/icon.png)

# Monteiro

Monteiro is a collection of practical, open-source Kodi add-ons for LibreELEC and Raspberry Pi. It provides a single place to install and update utilities that simplify your media-center setup. The collection currently includes HDMI Switcher, which lets you choose the active HDMI display directly from Kodi, and Easy Channel, which plays M3U lists in a TV box style screen and keeps only the channels that work. New tools and updates are published through this repository.


## Available add-ons

| Add-on | ID | Purpose |
| --- | --- | --- |
| [HDMI Switcher](script.hdmi.switcher/README.md) | `script.hdmi.switcher` | Select the active HDMI display and restart Kodi. |
| [Easy Channel](script.m3u.channels/README.md) | `script.m3u.channels` | Add M3U lists in one step and remove channels that do not work. |
| Monteiro | `repository.monteiromedia` | Register this repository in Kodi for installation and updates. |

Easy Channel does not provide any content. It plays the M3U lists its users add, and users are responsible for using only lists they are allowed to watch.

## Artwork

Every add-on declares an opaque 512 by 512 PNG icon and a 1280 by 720 JPEG fanart in its `addon.xml`. The builder publishes them at their catalog paths so Kodi can display them before installation. If old artwork remains after an update, restart Kodi.

The repository icon is an M monogram with a subtle play-shaped cutout, and its fanart shows quiet angular ribbons. HDMI Switcher's icon shows two monitors linked by switching arrows. Both use a navy, cyan, and blue palette and were created with OpenAI image generation.

Easy Channel's icon shows a blue TV screen with a white playlist symbol on a dark background, matching its interface. Its icon, fanart, and screenshots are generated from the add-on itself, as described in its [README](script.m3u.channels/README.md#development).

## Repository identity

The name shown in Kodi is **Monteiro**. The technical ID remains `repository.monteiromedia` so existing installations can receive this rename through a normal repository update. Version 1.0.3 added repository artwork and detailed metadata, and version 1.0.4 adds Easy Channel to its description. HDMI Switcher keeps its `script.hdmi.switcher` ID and uses version 1.0.4 for its dedicated display-switching icon.

## Publish on GitHub

1. Upload the contents of this folder to a public GitHub repository using the `main` or `master` branch, including `.github`, `.gitignore`, and the generated `repository` directory.
2. Open **Actions** and wait for **Publish Kodi repository** to complete. The workflow generates package URLs from the actual GitHub owner, repository name, and branch.
3. If the workflow reports a permissions error, enable **Read and write permissions** under **Settings > Actions > General > Workflow permissions**. Branch protection must allow the workflow to push its generated commit.
4. In GitHub, open the **Code** tab and download the generated `repository/repository.monteiromedia/repository.monteiromedia-1.0.4.zip` after the workflow succeeds. The ZIP is committed to the repository; it is listed under **Code**, rather than as an Actions artifact.

The initial generated files use `monteirohat/kodi-addons` and the `main` branch. The first workflow run adjusts these values to the actual repository location before installation. GitHub Pages is optional; Kodi downloads files directly from GitHub Raw.

## Register the repository in Kodi

1. On GitHub, open this repository's **Code** tab and select the branch where **Publish Kodi repository** completed successfully.
2. Open **repository > repository.monteiromedia** and select **repository.monteiromedia-1.0.4.zip**. You can also open the [repository installation ZIP](repository/repository.monteiromedia/repository.monteiromedia-1.0.4.zip) directly from this README.
3. On the file page, click **Download raw file** to download the ZIP. The full path from the repository root is `repository/repository.monteiromedia/repository.monteiromedia-1.0.4.zip`.
4. Copy the downloaded ZIP to a USB drive or a folder accessible from your Kodi device.
5. In Kodi, enable **Settings > System > Add-ons > Unknown sources**.
6. Open **Add-ons > Install from zip file**, browse to the location used in step 4, and select **repository.monteiromedia-1.0.4.zip**. Wait for the **Monteiro** repository installation notification. Registering the repository is a one-time step.
7. Open **Add-ons > Install from repository > Monteiro** and choose an add-on. HDMI Switcher is under **Program add-ons**, and Easy Channel is under **Video add-ons**.
8. Select **Install** and wait for installation to finish.

Further add-ons and updates are installed through **Monteiro**. Enable automatic updates for the add-on if desired. If an update is not visible yet, open the repository context menu and select **Check for updates**.

## Publish an add-on update

1. Modify its source code and increment its version in `addon.xml`.
2. Commit and push to `main` or `master`.
3. The workflow packages the add-ons, updates `addons.xml` and its checksum, and commits the generated files.
4. Kodi detects the updated catalog and offers the new version according to its update settings.

Add another self-contained top-level directory with its own `addon.xml` to publish another add-on. The folder name must match the add-on ID. The builder discovers these folders automatically and retains older installation packages.

## Repository layout

| Path | Purpose |
| --- | --- |
| `script.hdmi.switcher/` | HDMI Switcher source and documentation. |
| `script.m3u.channels/` | Easy Channel source and documentation. |
| `repository.monteiromedia/` | Repository registration add-on. |
| `repository/addons.xml` | Generated Kodi add-on catalog. |
| `repository/addons.xml.md5` | Catalog change indicator used by Kodi. |
| `repository/<addon-id>/` | Versioned installation ZIPs, SHA-256 files, and published artwork. |
| `tools/build_repository.py` | Catalog and package generator using Python's standard library. |
| `tools/generate_m3u_channels_skin.py` | Generator of the Easy Channel window layouts and theme. |
| `tools/generate_easy_channel_art.py` | Generator of the Easy Channel icon, fanart, and header symbol. |
| `.github/workflows/publish-repository.yml` | Build and publish workflow. |

Package hash headers are disabled in the Kodi repository definition because GitHub Raw does not provide Kodi's `content-sha256` headers. SHA-256 sidecars are provided for manual verification. Downloads use HTTPS.

## Build locally

From the repository root, run

```sh
python3 tools/build_repository.py --base-url https://raw.githubusercontent.com/monteirohat/kodi-addons/main/repository
```

Replace the owner, repository name, and branch when building for another location. Commit the generated `repository` directory and the updated registration manifest. The GitHub workflow performs this step automatically on each push.

## HDMI Switcher setup

The target environment is LibreELEC 12.2.1 on Raspberry Pi 4 with Kodi 21 and Python 3. The menu maps the small display to `HDMI-A-1` and the external monitor to `HDMI-A-2`.

Complete the [one-time setup](script.hdmi.switcher/README.md#one-time-setup) to remove previously configured HDMI boot overrides. The add-on then updates the active profile's `advancedsettings.xml` and restarts Kodi when changing displays. One display is active at a time.

## Development conventions

- Use English for identifiers, comments, documentation, filenames, and interface text.
- Keep each add-on self-contained and match its directory name to its ID.
- Increment `addon.xml` versions before publishing changed packages.
- Preserve existing user settings when making configuration changes.
- Increase the repository add-on version when changing its public URLs or metadata.

## Validation

Local checks cover metadata, package structure, checksums, deterministic builds, and the previously tested HDMI configuration logic. The user confirmed installation and HDMI display switching on the target Raspberry Pi.

Easy Channel was tested on LibreELEC 12.2.1 with Kodi 21.3 on a Raspberry Pi 4 by driving the interface with remote control commands and screenshots. The tests covered adding lists from a file and from GitHub, browsing groups, favorites, removing and restoring channels, failure detection for missing streams and unreachable servers, group checks, the list and repository managers, and the TV menu. Adding a repository by typing its name was only tested outside Kodi.

## License

MIT. See [LICENSE](LICENSE).
