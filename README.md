<p align="center">
  <img src="repository.monteiromedia/resources/icon.png" alt="Monteiro" width="140">
</p>

<h1 align="center">Monteiro</h1>

<p align="center">
  Practical, open-source Kodi add-ons for LibreELEC and Raspberry Pi.<br>
  Watch M3U channels and movies the easy way, and control your media center from the couch.
</p>

<p align="center">
  <b>English</b> · <a href="README.pt-BR.md">Português (Brasil)</a>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Kodi-21%20Omega-17B2E7" alt="Kodi 21 Omega">
  <img src="https://img.shields.io/badge/LibreELEC-12.2-3B8BFF" alt="LibreELEC 12.2">
  <img src="https://img.shields.io/badge/license-MIT-22272E" alt="MIT license">
  <a href="https://github.com/monteirohat/kodi-addons/releases"><img src="https://img.shields.io/github/downloads/monteirohat/kodi-addons/total?label=downloads&color=3B8BFF" alt="Release downloads"></a>
  <a href="https://github.com/monteirohat/kodi-addons/stargazers"><img src="https://img.shields.io/github/stars/monteirohat/kodi-addons?color=FFC53D" alt="GitHub stars"></a>
</p>

<p align="center">
  <img src=".github/assets/easy-channel.gif" alt="Easy Channel: browsing groups, a channel that does not respond, and the offer to remove it" width="860"><br>
  <sub>Easy Channel: switch groups, open a channel that does not respond, and remove it in one step, with <b>Check the channel before playing</b> on.</sub>
</p>

<p align="center">
  <a href="#installation">Installation</a> ·
  <a href="#add-ons">Add-ons</a> ·
  <a href="#help-and-feedback">Help and feedback</a> ·
  <a href="CONTRIBUTING.md">Contributing</a>
</p>

## Installation

Register the **Monteiro** repository in Kodi once, from its web address, and every add-on and update installs from it.

1. In Kodi, open **Settings > System > Add-ons** and turn on **Unknown sources**.
2. Open **Settings > File manager > Add source**, select **&lt;None&gt;**, enter `https://monteirohat.github.io/kodi-addons/`, name the source **Monteiro**, and select **OK**.
3. Open **Settings > Add-ons > Install from zip file > Monteiro** and select **repository.monteiromedia-1.0.5.zip**. Wait for the **Monteiro** repository installation notification.
4. Open **Install from repository > Monteiro** and install the add-ons you want. Easy Channel and Easy Movie are under **Video add-ons**, and HDMI Switcher is under **Program add-ons**.

Updates arrive through the repository. If one is not visible yet, open the context menu of **Monteiro** and select **Check for updates**. Without internet access on the Kodi device, download the ZIP from the [latest release](https://github.com/monteirohat/kodi-addons/releases/latest), copy it to a USB drive and use **Install from zip file**.

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
- Hold **OK** on a group to rename it or delete it.
- Selecting **TV** in Kodi's main menu opens Easy Channel.

![Easy Channel](script.m3u.channels/resources/screenshots/screenshot-01.jpg)

Read the [Easy Channel guide](script.m3u.channels/README.md) for every feature and setting.

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

<img src=".github/assets/easy-movie.gif" alt="Easy Movie: genres, posters, movie details and the Cinemeta catalog" width="860">

Read the [Easy Movie guide](script.m3u.movies/README.md) for every feature and setting.

### HDMI Switcher

<img src="script.hdmi.switcher/resources/hdmi-switcher-icon.png" alt="HDMI Switcher" width="72" align="left">

**Switch between a small HDMI display and an external monitor without touching the command line.** Pick a display, and Kodi restarts on it.

<br clear="left">

- Two display cards that show which display is active and which ones are connected, in the same dark design as Easy Channel and Easy Movie.
- Built for LibreELEC on Raspberry Pi 4, mapping the small display to `HDMI-A-1` and the external monitor to `HDMI-A-2`.
- Keeps your existing advanced settings and backs up the configuration file before the first change.
- Remembers the chosen display for future starts.

![HDMI Switcher](script.hdmi.switcher/resources/screenshots/screenshot-01.jpg)

HDMI Switcher needs a [one-time setup](script.hdmi.switcher/README.md#one-time-setup) that removes previous HDMI boot overrides. Read the [HDMI Switcher guide](script.hdmi.switcher/README.md) for details.

> [!NOTE]
> Easy Channel and Easy Movie do not provide any content. They play the M3U lists you add, and you are responsible for using only lists you are allowed to watch. The suggested GitHub repositories collect free, public channels and public domain movies, and are maintained by third parties.

## Help and feedback

- Found a problem? Open a [bug report](https://github.com/monteirohat/kodi-addons/issues/new?template=bug_report.yml).
- Have an idea? Open a [suggestion](https://github.com/monteirohat/kodi-addons/issues/new?template=feature_request.yml).
- Questions, tips and lists that work well belong in [Discussions](https://github.com/monteirohat/kodi-addons/discussions).

To build the repository, publish updates or change an add-on, read [CONTRIBUTING.md](CONTRIBUTING.md).

## License

MIT. See [LICENSE](LICENSE).
