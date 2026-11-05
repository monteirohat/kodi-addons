import sys

from resources.lib import gui


# RunScript(script.monteiro.addons,repository.id) opens on that repository.
gui.run(sys.argv[1] if len(sys.argv) > 1 else None)
