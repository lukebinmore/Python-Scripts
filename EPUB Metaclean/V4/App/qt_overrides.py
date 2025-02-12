from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtWebEngineWidgets import *
from PyQt5.QtGui import *
from globals import Globals as G


class BaseWidget:
    def __init__(self, parent=None, name=None, hor_policy=None, ver_policy=None, warn=False):
        if not isinstance(self, QWidget):
            raise TypeError("BaseWidget must be used with QWidget subclasses")

        if name:
            self.setObjectName(name)

        self.hor_policy = hor_policy if hor_policy is not None else G.PREFERRED
        self.ver_policy = ver_policy if ver_policy is not None else G.PREFERRED
        self.setSizePolicy(self.hor_policy, self.ver_policy)

        self.warn(warn)
        self.setContentsMargins(0, 0, 0, 0)

        if isinstance(parent, Container):
            parent.add(self)

    def warn(self, warn):
        self.setProperty("theme", "warn" if warn else None)

    def hide(self):
        self.setVisible(False)

    def show(self):
        self.setVisible(True)

    def delete(self):
        self.setParent(None)
        self.deleteLater()

    def applyBorderRadius(self):
        radius = int(G.STYLE_VARIABLES["border_radius"].replace("px", ""))
        path = QPainterPath()
        rect = QRectF(self.rect())
        path.addRoundedRect(rect, radius, radius)
        mask = QBitmap(self.size())
        mask.fill(Qt.white)
        painter = QPainter(mask)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setBrush(Qt.black)
        painter.drawPath(path)
        painter.end()
        self.setMask(mask)


class Container(QFrame, BaseWidget):
    def __init__(self, parent=None, name=None, vertical=True, hor_policy=None, ver_policy=None):
        QFrame.__init__(self, parent)
        BaseWidget.__init__(self, parent, name, hor_policy, ver_policy)

        self.layout = QVBoxLayout(self) if vertical else QHBoxLayout(self)
        self.setLayout(self.layout)
        self.setMargins(0, 0, 0, 0)

    def add(self, widget, *args, **kwargs):
        self.layout.addWidget(widget, *args, **kwargs)

    def setSpacing(self, spacing=0):
        self.layout.setSpacing(spacing)

    def setMargins(self, left=None, top=None, right=None, bottom=None):
        curr_margins = self.getContentsMargins()
        left = left if left is not None else curr_margins[0]
        top = top if top is not None else curr_margins[1]
        right = right if right is not None else curr_margins[2]
        bottom = bottom if bottom is not None else curr_margins[3]
        self.layout.setContentsMargins(left, top, right, bottom)

    def clear(self):
        for child in self.findChildren(QWidget):
            child.setParent(None)
            child.deleteLater()


class Label(QLabel, BaseWidget):
    def __init__(self, parent=None, name=None, text=None, hor_policy=None, ver_policy=None, warn=False):
        QLabel.__init__(self, text, parent)
        BaseWidget.__init__(self, parent, name, hor_policy, ver_policy, warn)
        self.setWordWrap(True)


class ImageLabel(QLabel, BaseWidget):
    def __init__(self, parent=None, name=None, hor_policy=None, ver_policy=None, warn=False):
        QLabel.__init__(self, parent)
        BaseWidget.__init__(self, parent, name, hor_policy, ver_policy, warn)
        self.setWordWrap(True)
        self.setAlignment(Qt.AlignCenter)
        self.setScaledContents(False)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.updateImageSize()

    def setImage(self, image=None):
        if image is not None:
            byte_array = QByteArray(image)
            pixmap = QPixmap()
            pixmap.loadFromData(byte_array)
            self.image_original = pixmap
            self.updateImageSize()
            return True
        else:
            return False

    def updateImageSize(self):
        if self.isVisible() and hasattr(self, "image_original"):
            self.setPixmap(self.image_original.scaled(self.size(), Qt.KeepAspectRatio))


class PushButton(QPushButton, BaseWidget):
    def __init__(self, parent=None, name=None, text=None, hor_policy=None, ver_policy=None, warn=False):
        QPushButton.__init__(self, text, parent)
        BaseWidget.__init__(self, parent, name, hor_policy, ver_policy, warn)

    def click(self, slot):
        try:
            self.clicked.disconnect()
        except TypeError:
            pass

        self.clicked.connect(slot)


class ProgressBar(QProgressBar, BaseWidget):
    def __init__(self, parent=None, name=None, hor_policy=None, ver_policy=None):
        QProgressBar.__init__(self, parent)
        BaseWidget.__init__(self, parent, name, hor_policy, ver_policy)
        self.setTextVisible(True)
        self.setAlignment(Qt.AlignCenter)
        self.setValue(0)

    def config(self, value=None, range=None, text=None):
        if value is not None:
            self.setValue(value)

        if range is not None:
            self.setRange(0, range)

        if text is not None:
            self.setFormat(f"{text}: %p%")

    def updateProgress(self, value, total):
        if total > 0:
            self.setValue(int((value / total) * 100))


class WebEnginePage(QWebEnginePage):
    def __init__(self, parent=None, intercept_callback=None):
        super().__init__(parent)
        self.intercept_callback = intercept_callback

    def acceptNavigationRequest(self, url, _type, is_main_frame):
        if self.intercept_callback is not None:
            return self.intercept_callback(url)

        return True


class WebEngineView(QWebEngineView, BaseWidget):
    def __init__(self, parent=None, name=None, hor_policy=None, ver_policy=None):
        QWebEngineView.__init__(self, parent)
        BaseWidget.__init__(self, parent, name, hor_policy, ver_policy)

        self.context_menu_enabled = False
        self.image_select_callback = None

        self.web_page = WebEnginePage(self)
        self.setPage(self.web_page)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.applyBorderRadius()

    def setInterceptor(self, interceptor):
        self.web_page.intercept_callback = interceptor

    def contextMenuEvent(self, event):
        if not self.context_menu_enabled:
            return

        menu = QMenu()
        hit_test = self.web_page.contextMenuData()

        if hit_test.mediaType() == QWebEngineContextMenuData.MediaTypeImage:
            image_url = hit_test.mediaUrl().toString()

            if image_url.lower().endswith((".jpg", ".jpeg", ".png")):
                select_action = QAction("Select", menu)
                select_action.triggered.connect(handleImage)
                menu.addAction(select_action)

                def handleImage():
                    clipboard = QApplication.clipboard()
                    clipboard.clear()
                    self.triggerPageAction(QWebEnginePage.CopyImageToClipboard)
                    QTimer.singleShot(100, waitForClipboardContent)

                def waitForClipboardContent(attempts=10):
                    clipboard = QApplication.clipboard()

                    if not clipboard.image().isNull():
                        processImage()
                    elif attempts > 0:
                        QTimer.singleShot(50, lambda: waitForClipboardContent(attempts - 1))

                def processImage():
                    clipboard = QApplication.clipboard()
                    qimage = clipboard.image()
                    buffer = QBuffer()
                    buffer.open(QIODevice.WriteOnly)
                    qimage.save(buffer, "JPEG")
                    buffer.close()
                    image = buffer.data()

                    if not image.isNull() and self.image_select_callback:
                        self.image_select_callback(image)

                menu.popup(event.globalPos())

    def setContextCall(self, callback=None):
        self.context_menu_enabled = True if callback is not None else False
        self.image_select_callback = callback

    def setUrl(self, url):
        url = QUrl(url)
        super().setUrl(url)

    def clearHistory(self):
        self.history().clear()

    def createWindow(self, _type):
        if self.page().intercept_callback is None:
            return self

        temp_view = QWebEngineView()

        def handle_new_url(url):
            print("Intercepted _blank URL:", url.toString())
            self.setUrl(url)
            temp_view.deleteLater()

        temp_view.page().urlChanged.connect(handle_new_url)

        return temp_view

    def downloadReq(self, slot):
        try:
            self.page().profile().downloadRequested.disconnect()
        except TypeError:
            pass

        self.page().profile().downloadRequested.connect(slot)

    def loaded(self, slot):
        self.loadedDone()
        self.loadFinished.connect(slot)

    def loadedDone(self):
        try:
            self.loadFinished.disconnect()
        except TypeError:
            pass


"""
import sys

v = G
app = QApplication(sys.argv)
ui = QMainWindow()
base = Container()
ui.setCentralWidget(base)

c1a = Container(base, vertical=False)
c1b = ScrollContainer(base)
c1c = Container(base, vertical=False)

b1a = PushButton(c1a, text="test 1")
b1b = PushButton(c1a, text="Test 2")

b2a = PushButton(c1b, text="test 1")
b2b = PushButton(c1b, text="Test 2")

b3a = PushButton(c1c, text="test 1")
b3b = PushButton(c1c, text="Test 2")

ui.show()

sys.exit(app.exec())
"""
