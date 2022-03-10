import enaml
from enaml.qt.qt_application import QtApplication


def main_mmn():
    with enaml.imports():
        from ncrar_biosemi.main_gui import MMNLauncher

    app = QtApplication()
    view = MMNLauncher()
    view.show()
    app.start()
    app.stop()
