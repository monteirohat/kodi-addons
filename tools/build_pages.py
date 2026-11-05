"""Build the GitHub Pages site of the Kodi repository, for installing it by URL.

The home page shows how to install the repository first, then the add-ons with their pictures. Kodi browses a web
source through the links of its pages, and lists a link only when its text is the same as its address. The home
page has one such link, to a copy of the repository ZIP at the site root, so Install from zip file finds it right
after the source is added. Every folder of the repository also gets an index.html with such links.

    python3 tools/build_pages.py --output _site
"""

import argparse
import html
import os
import re
import shutil
from string import Template

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPOSITORY = os.path.join(ROOT, "repository")
REPOSITORY_ADDON = os.path.join(ROOT, "repository.monteiromedia", "addon.xml")
GITHUB = "https://github.com/monteirohat/kodi-addons"
PAGES = "https://monteirohat.github.io/kodi-addons/"
# Pictures of the home page, copied from the repository to the assets folder of the site.
ASSETS = {
    "monteiro.png": "repository.monteiromedia/resources/icon.png",
    "fanart.jpg": "repository.monteiromedia/resources/fanart.jpg",
    "easy-channel.png": "script.m3u.channels/resources/icon.png",
    "easy-movie.png": "script.m3u.movies/resources/icon.png",
    "hdmi-switcher.png": "script.hdmi.switcher/resources/hdmi-switcher-icon.png",
    "easy-files.png": "script.easy.files/resources/icon.png",
    "easy-files.jpg": "script.easy.files/resources/screenshots/screenshot-01.jpg",
    "easy-picture.png": "script.easy.picture/resources/icon.png",
    "easy-picture.jpg": "script.easy.picture/resources/screenshots/screenshot-01.jpg",
    "monteiro-skin.png": "skin.monteiro/resources/icon.png",
    "monteiro-skin.jpg": ".github/assets/monteiro-skin.jpg",
    "easy-channel.gif": ".github/assets/easy-channel.gif",
    "easy-movie.gif": ".github/assets/easy-movie.gif",
    "easy-channel-buttons.jpg": "script.m3u.channels/resources/screenshots/screenshot-02.jpg",
    "easy-movie-catalog.jpg": "script.m3u.movies/resources/screenshots/screenshot-04.jpg",
    "easy-movie-series.jpg": "script.m3u.movies/resources/screenshots/screenshot-06.jpg",
    "hdmi-switcher.jpg": "script.hdmi.switcher/resources/screenshots/screenshot-01.jpg",
}


def repository_zip():
    with open(REPOSITORY_ADDON, encoding="utf-8") as source:
        version = re.search(r'<addon[^>]*\sversion="([^"]+)"', source.read()).group(1)
    name = "repository.monteiromedia-%s.zip" % version
    return name, os.path.join(REPOSITORY, "repository.monteiromedia", name)


def versions():
    """Versions of the add-ons in the catalog, by id."""
    with open(os.path.join(REPOSITORY, "addons.xml"), encoding="utf-8") as source:
        return dict(re.findall(r'<addon\s+id="([^"]+)"[^>]*?\sversion="([^"]+)"', source.read()))


def link(name):
    """A link whose text is its address, which Kodi lists."""
    quoted = html.escape(name, quote=True)
    return '<a href="%s">%s</a>' % (quoted, quoted)


def listing(folder, title):
    """A plain index of a folder, as a web server lists it."""
    names = sorted(os.listdir(folder))
    entries = [name + "/" if os.path.isdir(os.path.join(folder, name)) else name for name in names if name != "index.html"]
    rows = "\n".join("<li>%s</li>" % link(entry) for entry in entries)
    return """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>%s</title>
</head>
<body>
<h1>%s</h1>
<ul>
<li><a href="../">Parent folder</a></li>
%s
</ul>
</body>
</html>
""" % (html.escape(title), html.escape(title), rows)


HOME = Template("""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Monteiro Kodi Add-ons</title>
<meta name="description" content="Easy Channel, Easy Movie and HDMI Switcher: open-source Kodi add-ons for LibreELEC and Raspberry Pi. Install the repository by URL.">
<meta property="og:title" content="Monteiro Kodi Add-ons">
<meta property="og:description" content="Open-source Kodi add-ons for LibreELEC and Raspberry Pi. Install the repository by URL.">
<meta property="og:image" content="${pages}assets/fanart.jpg">
<link rel="icon" href="assets/monteiro.png">
<style>
  :root {
    color-scheme: dark;
    --bg: #0e0f11; --surface: #17181b; --raised: #222328; --line: #2c2d33;
    --text: #f4f4f5; --text2: #9c9ea6; --text3: #62656d; --accent: #3b8bff; --cyan: #00e5ff;
  }
  * { box-sizing: border-box; }
  body { margin: 0; background: var(--bg); color: var(--text); font: 17px/1.6 system-ui, -apple-system, "Segoe UI", Roboto, sans-serif; }
  img { max-width: 100%; height: auto; display: block; }
  a { color: var(--accent); text-decoration: none; }
  a:hover { text-decoration: underline; }
  .wrap { max-width: 1120px; margin: 0 auto; padding: 0 16px; }
  header.top { position: sticky; top: 0; z-index: 2; background: rgba(14, 15, 17, .88); backdrop-filter: blur(10px); border-bottom: 1px solid var(--line); }
  header.top .wrap { display: flex; align-items: center; gap: 12px; height: 64px; }
  header.top img { width: 36px; height: 36px; border-radius: 9px; }
  header.top b { font-size: 19px; }
  header.top nav { margin-left: auto; display: flex; gap: 20px; font-size: 15px; }
  header.top nav a { color: var(--text2); }
  .hero { background: linear-gradient(180deg, rgba(14, 15, 17, .35), var(--bg) 92%), url("assets/fanart.jpg") center / cover; }
  .hero .wrap { display: grid; grid-template-columns: 1fr 1fr; gap: 48px; align-items: center; padding-top: 72px; padding-bottom: 72px; }
  h1 { font-size: 46px; line-height: 1.1; margin: 0 0 16px; letter-spacing: -.02em; }
  .lead { color: var(--text2); font-size: 19px; margin: 0 0 28px; }
  .install { background: var(--surface); border: 1px solid var(--line); border-radius: 20px; padding: 24px; }
  .install h2 { font-size: 20px; margin: 0 0 16px; }
  .url { display: flex; gap: 8px; margin: 0 0 18px; }
  .url code { flex: 1; min-width: 0; background: var(--bg); border: 1px solid var(--line); border-radius: 12px; padding: 12px 14px; font-size: 15px; overflow-x: auto; white-space: nowrap; color: var(--cyan); }
  button { font: inherit; font-size: 15px; font-weight: 600; border: 0; border-radius: 12px; padding: 0 18px; background: var(--accent); color: #fff; cursor: pointer; }
  ol.steps { margin: 0; padding: 0; list-style: none; counter-reset: step; }
  ol.steps li { counter-increment: step; position: relative; padding: 0 0 12px 40px; color: var(--text2); }
  ol.steps li::before { content: counter(step); position: absolute; left: 0; top: 0; width: 26px; height: 26px; border-radius: 50%; background: var(--raised); color: var(--text); font-size: 14px; font-weight: 700; display: grid; place-items: center; }
  ol.steps b { color: var(--text); font-weight: 600; }
  .zip { margin-top: 6px; padding-top: 16px; border-top: 1px solid var(--line); font-size: 15px; color: var(--text2); overflow-wrap: anywhere; }
  .shot { border-radius: 16px; border: 1px solid var(--line); box-shadow: 0 24px 60px rgba(0, 0, 0, .5); }
  section { padding: 72px 0; }
  section.alt { background: #121316; }
  .eyebrow { color: var(--accent); font-weight: 700; font-size: 14px; letter-spacing: .08em; text-transform: uppercase; margin: 0 0 8px; }
  h2.title { font-size: 34px; line-height: 1.2; margin: 0 0 12px; letter-spacing: -.01em; }
  .cards { display: grid; grid-template-columns: repeat(2, 1fr); gap: 20px; margin-top: 32px; }
  .card { background: var(--surface); border: 1px solid var(--line); border-radius: 20px; padding: 24px; color: var(--text); }
  .card:hover { border-color: var(--accent); text-decoration: none; }
  .card img { width: 72px; height: 72px; border-radius: 18px; margin-bottom: 16px; }
  .card h3 { margin: 0 0 6px; font-size: 20px; }
  .card p { margin: 0; color: var(--text2); font-size: 15px; }
  .card .version { color: var(--text3); font-size: 13px; margin-top: 12px; }
  .addon { display: grid; grid-template-columns: 5fr 7fr; gap: 48px; align-items: center; }
  .addon.flip { grid-template-columns: 7fr 5fr; }
  .addon.flip .media { order: -1; }
  .addon .name { display: flex; align-items: center; gap: 14px; margin-bottom: 12px; }
  .addon .name img { width: 56px; height: 56px; border-radius: 14px; }
  .addon .name h2 { margin: 0; font-size: 32px; }
  .addon p { color: var(--text2); margin: 0 0 16px; }
  .addon ul { margin: 0 0 20px; padding-left: 20px; color: var(--text2); }
  .addon li { margin: 6px 0; }
  .addon li b { color: var(--text); font-weight: 600; }
  /* Grid items may shrink below their content, so the address and pictures never widen the page. */
  .hero .wrap > *, .addon > *, .cards > *, .gallery > * { min-width: 0; }
  .gallery { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-top: 12px; }
  .gallery img { border-radius: 12px; border: 1px solid var(--line); }
  .more { font-weight: 600; }
  .note { background: var(--surface); border-left: 4px solid var(--accent); border-radius: 12px; padding: 16px 20px; color: var(--text2); font-size: 15px; }
  footer { border-top: 1px solid var(--line); padding: 32px 0 48px; color: var(--text3); font-size: 14px; }
  footer .wrap { display: flex; flex-wrap: wrap; gap: 8px 24px; justify-content: space-between; }
  @media (max-width: 860px) {
    .hero .wrap, .addon, .addon.flip, .cards { grid-template-columns: 1fr; }
    .addon.flip .media { order: 0; }
    .hero .wrap { padding-top: 40px; padding-bottom: 40px; gap: 32px; }
    h1 { font-size: 34px; }
    h2.title, .addon .name h2 { font-size: 26px; }
    section { padding: 48px 0; }
    header.top nav { gap: 14px; }
  }
  @media (max-width: 420px) { header.top nav a.hide-small { display: none; } .url { flex-direction: column; } .url code { white-space: normal; overflow-wrap: anywhere; } .url button { padding: 10px; } }
</style>
</head>
<body>
<header class="top">
  <div class="wrap">
    <img src="assets/monteiro.png" alt="">
    <b>Monteiro</b>
    <nav>
      <a href="#install">Install</a>
      <a href="#addons">Add-ons</a>
      <a href="${github}">GitHub</a>
    </nav>
  </div>
</header>

<div class="hero" id="install">
  <div class="wrap">
    <div>
      <h1>Kodi add-ons for the living room</h1>
      <p class="lead">Live TV and movies from your M3U lists, your photos and files, a skin made for them, and the right HDMI display, on LibreELEC and Raspberry Pi. Install the repository once, from its address, and every add-on and update comes from it.</p>
      <div class="install">
        <h2>Install in Kodi</h2>
        <div class="url"><code id="address">${pages}</code><button type="button" id="copy">Copy</button></div>
        <ol class="steps">
          <li>Open <b>Settings &gt; System &gt; Add-ons</b> and turn on <b>Unknown sources</b>.</li>
          <li>Open <b>Settings &gt; File manager &gt; Add source</b>, select <b>&lt;None&gt;</b>, enter the address above and name the source <b>Monteiro</b>.</li>
          <li>Open <b>Settings &gt; Add-ons &gt; Install from zip file &gt; Monteiro</b> and select <b>${zip}</b>.</li>
          <li>Open <b>Install from repository &gt; Monteiro</b> and install the add-ons you want.</li>
        </ol>
        <div class="zip">No internet on the Kodi device? Download ${zip_link}, copy it to a USB drive and use <b>Install from zip file</b>.</div>
      </div>
    </div>
    <img class="shot" src="assets/easy-channel.gif" alt="Easy Channel: switching groups, a channel that does not respond, and the offer to remove it" width="960" height="540">
  </div>
</div>

<section id="addons">
  <div class="wrap">
    <p class="eyebrow">Add-ons</p>
    <h2 class="title">Five add-ons and a skin, one design</h2>
    <p class="lead">Made for the remote control, with the same dark interface, in English and Brazilian Portuguese.</p>
    <div class="cards">
      <a class="card" href="#easy-channel"><img src="assets/easy-channel.png" alt=""><h3>Easy Channel</h3><p>Live TV from M3U lists in a TV box style screen that keeps only the channels that work.</p><div class="version">Version ${channel_version} &middot; Video add-ons</div></a>
      <a class="card" href="#easy-movie"><img src="assets/easy-movie.png" alt=""><h3>Easy Movie</h3><p>Movies and series as a poster catalog, with Cinemeta, Stremio addons, downloads and subtitles.</p><div class="version">Version ${movie_version} &middot; Video add-ons</div></a>
      <a class="card" href="#hdmi-switcher"><img src="assets/hdmi-switcher.png" alt=""><h3>HDMI Switcher</h3><p>Pick the active HDMI display of a Raspberry Pi 4 from the couch.</p><div class="version">Version ${hdmi_version} &middot; Program add-ons</div></a>
      <a class="card" href="#easy-files"><img src="assets/easy-files.png" alt=""><h3>Easy Files</h3><p>A file manager for the remote: copy, move, rename and delete with one long press.</p><div class="version">Version ${files_version} &middot; Program add-ons</div></a>
      <a class="card" href="#easy-picture"><img src="assets/easy-picture.png" alt=""><h3>Easy Picture</h3><p>Your photos in a gallery, by album, and each one in full screen with one press of OK.</p><div class="version">Version ${picture_version} &middot; Picture add-ons</div></a>
      <a class="card" href="#monteiro-skin"><img src="assets/monteiro-skin.png" alt=""><h3>Monteiro skin</h3><p>A home screen and menus in the same design, with every Easy add-on one press away.</p><div class="version">Version ${skin_version} &middot; Look and feel &gt; Skin</div></a>
    </div>
  </div>
</section>

<section class="alt" id="easy-channel">
  <div class="wrap addon">
    <div>
      <div class="name"><img src="assets/easy-channel.png" alt=""><h2>Easy Channel</h2></div>
      <p>Add an M3U list in a few steps, browse channels by group, and remove the ones that stop working as soon as they fail. No playlist or EPG configuration is needed.</p>
      <ul>
        <li>Groups on the left, channels in the middle, and details of the focused channel on the right.</li>
        <li>Lists from a web address, a file, or GitHub, with suggested repositories of free, public channels.</li>
        <li><b>Check channels</b> tests a whole group at once, and a channel that does not answer can be removed in one step.</li>
        <li>Full screen playback with a channel bar, Up and Down to zap, and <b>Favorites</b>.</li>
      </ul>
      <a class="more" href="${github}/blob/main/script.m3u.channels/README.md">Read the Easy Channel guide &rarr;</a>
    </div>
    <div class="media">
      <img class="shot" src="assets/easy-channel-buttons.jpg" alt="Easy Channel: favorite and remove buttons of a channel" width="1280" height="720" loading="lazy">
    </div>
  </div>
</section>

<section id="easy-movie">
  <div class="wrap addon flip">
    <div>
      <div class="name"><img src="assets/easy-movie.png" alt=""><h2>Easy Movie</h2></div>
      <p>The movies and series of your M3U lists and video folders, as a poster catalog. Open a movie to see its details, or a series to pick a season and continue where you stopped.</p>
      <ul>
        <li>Genres on the left, posters on the right, <b>Continue watching</b> and watched marks.</li>
        <li>The <b>Cinemeta</b> catalog of Stremio, with <b>My list</b>, and Stremio addons added by their address.</li>
        <li>Torrent downloads into a folder you choose, and your own video folders with posters and details.</li>
        <li>Streaming style playback controls, and subtitles from <b>OpenSubtitles</b> turned on in your language.</li>
      </ul>
      <a class="more" href="${github}/blob/main/script.m3u.movies/README.md">Read the Easy Movie guide &rarr;</a>
    </div>
    <div class="media">
      <img class="shot" src="assets/easy-movie.gif" alt="Easy Movie: genres, posters, movie details and the Cinemeta catalog" width="960" height="540" loading="lazy">
      <div class="gallery">
        <img src="assets/easy-movie-catalog.jpg" alt="Easy Movie: the Cinemeta catalog" width="1280" height="720" loading="lazy">
        <img src="assets/easy-movie-series.jpg" alt="Easy Movie: a series with seasons and episodes" width="1280" height="720" loading="lazy">
      </div>
    </div>
  </div>
</section>

<section class="alt" id="hdmi-switcher">
  <div class="wrap addon">
    <div>
      <div class="name"><img src="assets/hdmi-switcher.png" alt=""><h2>HDMI Switcher</h2></div>
      <p>Switch between a small HDMI display and an external monitor without touching the command line. Pick a display, and Kodi restarts on it.</p>
      <ul>
        <li>Two display cards show which display is active and which ones are connected.</li>
        <li>Built for LibreELEC on Raspberry Pi 4.</li>
        <li>Keeps your advanced settings and backs up the configuration before the first change.</li>
      </ul>
      <a class="more" href="${github}/blob/main/script.hdmi.switcher/README.md">Read the HDMI Switcher guide &rarr;</a>
    </div>
    <div class="media">
      <img class="shot" src="assets/hdmi-switcher.jpg" alt="HDMI Switcher: the display cards" width="1280" height="720" loading="lazy">
    </div>
  </div>
</section>

<section id="easy-files">
  <div class="wrap addon flip">
    <div>
      <div class="name"><img src="assets/easy-files.png" alt=""><h2>Easy Files</h2></div>
      <p>A file manager made for the remote control. Places on the left, the folder on the right, and every option one long press away.</p>
      <ul>
        <li>Your home folder, USB drives, network shares and the folders of Kodi, with the free space of each drive.</li>
        <li>Hold <b>OK</b> on a file or folder to open, rename, copy, move or delete it, or see its details.</li>
        <li>Copies show their progress and can be cancelled.</li>
      </ul>
      <a class="more" href="${github}/blob/main/script.easy.files/README.md">Read the Easy Files guide &rarr;</a>
    </div>
    <div class="media">
      <img class="shot" src="assets/easy-files.jpg" alt="Easy Files: places and the files of a folder" width="1280" height="720" loading="lazy">
    </div>
  </div>
</section>

<section id="easy-picture">
  <div class="wrap addon">
    <div>
      <div class="name"><img src="assets/easy-picture.png" alt=""><h2>Easy Picture</h2></div>
      <p>Your photos on the TV, in a gallery. Albums on the left, the pictures of the album on the right, and each picture in full screen with one press of OK.</p>
      <ul>
        <li>All pictures and your favorites first, then one album for each folder of photos.</li>
        <li>Left and Right move through the pictures in full screen.</li>
        <li>Hold <b>OK</b> on a picture to mark it as favorite, rotate or flip it, or see its date, size, resolution and folder.</li>
      </ul>
      <a class="more" href="${github}/blob/main/script.easy.picture/README.md">Read the Easy Picture guide &rarr;</a>
    </div>
    <div class="media">
      <img class="shot" src="assets/easy-picture.jpg" alt="Easy Picture: albums and the gallery of an album" width="1280" height="720" loading="lazy">
    </div>
  </div>
</section>

<section id="monteiro-skin">
  <div class="wrap addon flip">
    <div>
      <div class="name"><img src="assets/monteiro-skin.png" alt=""><h2>Monteiro skin</h2></div>
      <p>A Kodi skin in the design of the add-ons. Its home screen opens the Easy add-ons directly, and its settings, menus, keyboard and player bars share their dark look and steel blue focus.</p>
      <ul>
        <li><b>TV</b>, <b>Movies</b> and <b>Series</b> open Easy Channel and Easy Movie, <b>Pictures</b> opens Easy Picture, and <b>Files</b> opens Easy Files.</li>
        <li><b>Add-ons</b> opens the installed add-ons, with a toolbar for search, repositories and updates. <b>Repositories</b> lists the add-ons of each repository with their categories.</li>
        <li>Buttons for the Wi-Fi settings of LibreELEC, the settings of Kodi and the power menu.</li>
      </ul>
      <a class="more" href="${github}/blob/main/skin.monteiro/README.md">Read the skin guide &rarr;</a>
    </div>
    <div class="media">
      <img class="shot" src="assets/monteiro-skin.jpg" alt="Monteiro skin: the home screen" width="1280" height="720" loading="lazy">
    </div>
  </div>
</section>

<section class="alt">
  <div class="wrap">
    <p class="note">Easy Channel and Easy Movie do not provide any content. They play the lists and addons you add, and you are responsible for using only content you are allowed to watch.</p>
    <p class="lead" style="margin-top: 24px">Questions or ideas? Open an <a href="${github}/issues/new/choose">issue</a> or join the <a href="${github}/discussions">discussions</a>. Leia em <a href="${github}/blob/main/README.pt-BR.md">português</a>.</p>
  </div>
</section>

<footer>
  <div class="wrap">
    <span>Monteiro Kodi Add-ons &middot; MIT license</span>
    <a href="${github}">Source on GitHub</a>
  </div>
</footer>

<script>
  document.getElementById("copy").addEventListener("click", function () {
    var button = this;
    navigator.clipboard.writeText(document.getElementById("address").textContent).then(function () {
      button.textContent = "Copied";
      setTimeout(function () { button.textContent = "Copy"; }, 2000);
    });
  });
</script>
</body>
</html>
""")


def home(zip_name):
    found = versions()
    return HOME.substitute(pages=PAGES, github=GITHUB, zip=html.escape(zip_name), zip_link=link(zip_name),
                           channel_version=found.get("script.m3u.channels", ""), movie_version=found.get("script.m3u.movies", ""),
                           hdmi_version=found.get("script.hdmi.switcher", ""), files_version=found.get("script.easy.files", "1.0.0"),
                           picture_version=found.get("script.easy.picture", "1.0.0"), skin_version=found.get("skin.monteiro", ""))


def build(output):
    if os.path.isdir(output):
        shutil.rmtree(output)
    shutil.copytree(REPOSITORY, output)
    zip_name, zip_path = repository_zip()
    shutil.copy2(zip_path, os.path.join(output, zip_name))
    for folder, _, _ in os.walk(output):
        if folder != output:
            title = "Index of /" + os.path.relpath(folder, output) + "/"
            with open(os.path.join(folder, "index.html"), "w", encoding="utf-8") as page:
                page.write(listing(folder, title))
    # The pictures of the home page are added after the listings, as Kodi does not need to browse them.
    assets = os.path.join(output, "assets")
    os.makedirs(assets)
    for name, source in ASSETS.items():
        shutil.copy2(os.path.join(ROOT, source), os.path.join(assets, name))
    with open(os.path.join(output, "index.html"), "w", encoding="utf-8") as page:
        page.write(home(zip_name))
    # Serve the files as they are, without the Jekyll build of GitHub Pages.
    open(os.path.join(output, ".nojekyll"), "w").close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default=os.path.join(ROOT, "_site"), help="Folder to write the site to")
    build(parser.parse_args().output)


if __name__ == "__main__":
    main()
