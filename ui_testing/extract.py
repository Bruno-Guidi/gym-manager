import sys

from PyQt5.QtWidgets import QApplication

from ui.accounting.operations import ExtractUI

if __name__ == "__main__":
    app = QApplication(sys.argv)

    window = ExtractUI()
    window.show()

    app.exec()