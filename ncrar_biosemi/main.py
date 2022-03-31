import enaml
from enaml.qt.qt_application import QtApplication


def main_nback():
    with enaml.imports():
        from ncrar_biosemi.main_gui import NBackLauncher

    app = QtApplication()
    view = NBackLauncher()
    view.show()
    app.start()
    app.stop()
