"""Build the GitHub Pages site of the Kodi repository, for installing it by URL.

Kodi browses a web source through the links of its pages, and lists a link only when its text is the same as its
address. Every folder gets an index.html with such links, and the site root gets a copy of the repository ZIP, so
Install from zip file finds it right after the source is added.

    python3 tools/build_pages.py --output _site
"""

import argparse
import html
import os
import re
import shutil

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPOSITORY = os.path.join(ROOT, "repository")
REPOSITORY_ADDON = os.path.join(ROOT, "repository.monteiromedia", "addon.xml")
GITHUB = "https://github.com/monteirohat/kodi-addons"
PAGES = "https://monteirohat.github.io/kodi-addons/"


def repository_zip():
    with open(REPOSITORY_ADDON, encoding="utf-8") as source:
        version = re.search(r'<addon[^>]*\sversion="([^"]+)"', source.read()).group(1)
    name = "repository.monteiromedia-%s.zip" % version
    return name, os.path.join(REPOSITORY, "repository.monteiromedia", name)


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


def home(zip_name):
    return """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Monteiro Kodi repository</title>
<style>
  :root {{ color-scheme: dark; }}
  body {{ margin: 0; background: #0e0f11; color: #f4f4f5; font: 17px/1.6 system-ui, -apple-system, "Segoe UI", sans-serif; }}
  main {{ max-width: 760px; margin: 0 auto; padding: 48px 16px; }}
  h1 {{ font-size: 32px; margin: 0 0 8px; }}
  p.lead {{ color: #9c9ea6; margin: 0 0 32px; }}
  section {{ background: #17181b; border-radius: 16px; padding: 24px; margin-bottom: 24px; }}
  h2 {{ font-size: 20px; margin: 0 0 12px; }}
  ol {{ padding-left: 22px; margin: 0; }}
  li {{ margin: 6px 0; }}
  code {{ background: #222328; border-radius: 6px; padding: 2px 8px; overflow-wrap: anywhere; }}
  a {{ color: #3b8bff; }}
  .zip {{ display: inline-block; margin-top: 16px; font-weight: 600; overflow-wrap: anywhere; }}
</style>
</head>
<body>
<main>
<h1>Monteiro Kodi repository</h1>
<p class="lead">Easy Channel, Easy Movie and HDMI Switcher for Kodi, LibreELEC and Raspberry Pi.</p>
<section>
<h2>Install in Kodi</h2>
<ol>
<li>Open <b>Settings &gt; System &gt; Add-ons</b> and turn on <b>Unknown sources</b>.</li>
<li>Open <b>Settings &gt; File manager &gt; Add source</b>, enter <code>{pages}</code> and name it <b>Monteiro</b>.</li>
<li>Open <b>Settings &gt; Add-ons &gt; Install from zip file &gt; Monteiro</b> and select <b>{zip}</b>.</li>
<li>Open <b>Install from repository &gt; Monteiro</b> and install the add-ons you want.</li>
</ol>
<div class="zip">{zip_link}</div>
</section>
<section>
<h2>Add-ons</h2>
<p>Read the guides, report problems and see the source on <a href="{github}">GitHub</a>.</p>
</section>
</main>
</body>
</html>
""".format(pages=PAGES, zip=html.escape(zip_name), zip_link=link(zip_name), github=GITHUB)


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
