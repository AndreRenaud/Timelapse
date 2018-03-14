#!/usr/bin/env python3

# The app should have the following:
# A list of images on the left hand side
#   (with + & - buttons to add/remove them, and ability to move them up/down the order)
# A two-image view on the rhs which shows the currently selected image, and the one following it
# A button to auto find correlation points, which uses cv2.DescriptorMatcher_create
# Ability to add/remove correlation points on images
# Ability to zoom in/out on the images
# A button to find the minimal rectangle that all images share after warping
# A button to apply the warp

from PyQt5.QtWidgets import (QWidget, QHBoxLayout, QFrame,
    QSplitter, QStyleFactory, QApplication, QLabel, QScrollArea, QMainWindow, QFileDialog)
from PyQt5 import QtCore
from PyQt5.QtCore import Qt
from PyQt5.QtCore import QRect
from PyQt5.QtGui import (QPixmap, QPainter, QBrush, QColor, QPen, QImage)
import cv2
import json
import numpy as np
import sys
import signal
from correlator_ui import Ui_MainWindow

class DragScroll(QScrollArea):
    def __init__(self, parent):
        super(DragScroll, self).__init__(parent)
        self.last_pos=(-1, -1)

    def mousePressEvent(self, event):
        print("Resetting last pos press")
        self.last_pos = (-1, -1)

    def mouseReleaseEvent(self, event):
        print("Resetting last pos")
        self.last_pos = (-1, -1)

    def mouseMoveEvent(self, event):
        if event.buttons() != Qt.LeftButton:
            return
        if self.last_pos != (-1, -1):
            xoff = self.last_pos[0] - event.x()
            yoff = self.last_pos[1] - event.y()
            self.moveScrollBars(xoff, yoff)
        self.last_pos = (event.x(), event.y())

    def moveScrollBars(self, xoff, yoff):
        h = self.horizontalScrollBar()
        h.setSliderPosition(h.sliderPosition() + xoff)
        v = self.verticalScrollBar()
        v.setSliderPosition(v.sliderPosition() + yoff)

class ImageLabel(QLabel):
    def __init__(self, parent):
        super(ImageLabel, self).__init__(parent)
        self.orig_pixmap = None
        self.scaleSetting = 0
        self.setScaledContents(True)
        self.points=[]
        self.selectedPoint = -1
        self.peer = None
        self.dragging = -1

    def setPixmap(self, pixmap):
        self.orig_pixmap = QPixmap(pixmap)
        super(ImageLabel, self).setPixmap(pixmap)
        self.setScaledContents(True)

    def getDistinctColor(self, index):
        colors = [(230, 25, 75), (60, 180, 75), (255, 225, 25),
                  (0, 130, 200), (245, 130, 48), (145, 30, 180),
                  (70, 240, 240), (240, 50, 230), (210, 245, 60),
                  (250, 190, 190), (0, 128, 128), (230, 190, 255),
                  (170, 110, 40), (255, 250, 200), (128, 0, 0),
                  (170, 255, 195), (128, 128, 0), (255, 215, 180),
                  (0, 0, 128), (128, 128, 128), (255, 255, 255),
                  (0, 0, 0)]
        if index < len(colors):
            c = colors[index]
            return QColor(c[0], c[1], c[2])
        return QColor((index * 120) % 255, (index * 873) % 255, (index * 375) % 255)

    def paintEvent(self, event):
        painter = QPainter()
        painter.begin(self)
        scale = 1.1**self.scaleSetting
        orig_size = self.pixmap().size()
        size = self.pixmap().size() * scale
        target = QRect(0, 0, size.width(), size.height())
        source = QRect(0, 0, orig_size.width(), orig_size.height())
        painter.drawImage(target, self.pixmap().toImage(), source)

        color = QColor()
        pen = QPen()
        pen.setWidth(5)

        for i in range(len(self.points)):
            p = self.points[i]
            if i == self.selectedPoint:
                c = QColor(255, 255, 255)
            else:
                c = self.getDistinctColor(i)
            pen.setColor(c)
            painter.setPen(pen)
            x = p[0] * scale
            y = p[1] * scale
            radius = 10 * scale
            r = QRect(x - radius, y - radius, 2 * radius, 2 * radius)
            painter.drawEllipse(r)
        painter.end()

    def mouseReleaseEvent(self, event):
        self.dragging = -1
        # We need to pass this up so the scrolling can work properly
        event.ignore()

    def mouseMoveEvent(self, event):
        if self.dragging != -1:
            scale = 1.1**self.scaleSetting
            x = event.x() / scale
            y = event.y() / scale
            self.points[self.dragging] = (x, y)
            self.repaint()
        else:
            event.ignore()

    def scaleImage(self, factor):
        self.scaleSetting += factor
        self.scaleSetting = max(min(self.scaleSetting, 20), -20)
        scale = 1.1**self.scaleSetting
        print("Rescaled to", self.scaleSetting, scale)
        size = self.pixmap().size() * scale
        self.resize(size)

    def wheelEvent(self, event):
        if event.angleDelta().y() > 0:
            self.scaleImage(1)
        if event.angleDelta().y() < 0:
            self.scaleImage(-1)
            #u = self.orig_pixmap.scaledToHeight(self.pixmap().height() / 1.1)
            #self.setPixmap(QPixmap(u))

        #print(event)
        #print(event.x(), event.y())
        #print(event.pixelDelta())
        #print(event.angleDelta())

    def findPointAt(self, x, y):
        for i in range(len(self.points)):
            p = self.points[i]
            radius = 10
            r = QRect(p[0] - radius, p[1] - radius, 2* radius, 2 * radius)
            if r.contains(x, y):
                return i
        return -1

    def setPeer(self, peer):
        self.peer = peer

    def setSelected(self, index, propogate = True):
        if index != -1:
            print("Selecting", index)
        self.selectedPoint = index
        if self.peer != None and propogate:
            self.peer.setSelected(index, False)
        self.repaint()

    def clearPoints(self):
        self.points = []
        self.setSelected(-1)

    def addPoint(self, x, y):
        self.points.append([float(x), float(y)])
        print("Added point",x,y, len(self.points))
        self.setSelected(-1)

    def removePoint(self, index):
        self.points.pop(index)
        self.setSelected(-1)

    def mouseDoubleClickEvent(self, event):
        if event.button() != Qt.LeftButton:
            return
        print("double click", event)
        scale = 1.1**self.scaleSetting
        x = event.x() / scale
        y = event.y() / scale
        self.addPoint(x, y)
        self.peer.addPoint(x, y)

    def mousePressEvent(self, event):
        scale = 1.1**self.scaleSetting
        x = event.x() / scale
        y = event.y() / scale
        i = self.findPointAt(x, y)
        #print("Point at", event.x(), event.y(), "scaled",x,y,"is",i)
        if i >= 0:
            p = self.points[i]
            #print("Contains", p)
            if event.buttons() == Qt.RightButton:
                #print("Removing", x, y, p)
                self.removePoint(i)
                self.peer.removePoint(i)
                self.repaint()
            if event.buttons() == Qt.LeftButton:
                self.setSelected(i)
                self.dragging = i
        if i < 0 and event.buttons() == Qt.LeftButton:
            self.setSelected(-1)

class CorrelationApp(QMainWindow, Ui_MainWindow):
    def __init__(self):
        super().__init__()

        self.initUI()

    def initUI(self):
        self.setupUi(self)

        self.left = ImageLabel(self)
        self.left.setFrameShape(QFrame.StyledPanel)
        self.scrollLeft.setWidget(self.left)
        self.scrollLeft.setWidgetResizable(True)

        self.right = ImageLabel(self)
        self.right.setFrameShape(QFrame.StyledPanel)
        self.scrollRight.setWidget(self.right)
        self.scrollRight.setWidgetResizable(True)

        self.left.setPeer(self.right)
        self.right.setPeer(self.left)

        self.autoCorrelateButton.clicked.connect(self.autoCorrelate)
        self.warpImagesButton.clicked.connect(self.warpImages)
        self.action_Save_Project.triggered.connect(self.saveProject)
        self.action_Load_Project.triggered.connect(self.loadProject)

    def saveProject(self):
        fname,wildcard = QFileDialog.getSaveFileName(self, 'Save Project')
        print('fname',fname)
        if fname == "":
            return
        with open(fname, 'w') as outfile:
            json.dump({'left': self.left.points, 'right': self.right.points}, outfile)

    def loadProject(self):
        fname,wildcard = QFileDialog.getOpenFileName(self, 'Load Project')
        print('fname',fname)
        if fname == "":
            return
        with open(fname) as infile:
            data = json.load(infile)
            self.right.points = data['right']
            self.left.points = data['left']
            self.right.repaint()
            self.left.repaint()

    def setImages(self, image1, image2):
        p1 = QPixmap(image1)
        p2 = QPixmap(image2)
        self.left.setPixmap(p1)
        self.right.setPixmap(p2)

    def getPoints(self, im1, im2, max_points):
        # Convert images to grayscale
        im1Gray = cv2.cvtColor(im1, cv2.COLOR_BGR2GRAY)
        im2Gray = cv2.cvtColor(im2, cv2.COLOR_BGR2GRAY)

        # Detect ORB features and compute descriptors.
        orb = cv2.ORB_create(max_points * 5)
        keypoints1, descriptors1 = orb.detectAndCompute(im1Gray, None)
        keypoints2, descriptors2 = orb.detectAndCompute(im2Gray, None)

        # Match features.
        matcher = cv2.DescriptorMatcher_create(cv2.DESCRIPTOR_MATCHER_BRUTEFORCE_HAMMING)
        matches = matcher.match(descriptors1, descriptors2, None)

        # Sort matches by score
        matches.sort(key=lambda x: x.distance, reverse=False)

        # Limit matches to the best 'max_points'
        matches = matches[:min(len(matches), max_points)]

        # Extract location of good matches
        points1 = np.zeros((len(matches), 2), dtype=np.float32)
        points2 = np.zeros((len(matches), 2), dtype=np.float32)

        for i, match in enumerate(matches):
            points1[i, :] = keypoints1[match.queryIdx].pt
            points2[i, :] = keypoints2[match.trainIdx].pt

        return (points1, points2)

    def pixmapToMat(self, pixmap):
        '''Convert a QImage into a opencv Mat'''
        img = pixmap.toImage()
        img = img.convertToFormat(QImage.Format_RGB32)
        ptr = img.bits()
        ptr.setsize(img.byteCount())
        return np.array(ptr).reshape(img.height(), int(img.bytesPerLine() / 4), 4)

    def warpImages(self):
        mat1 = self.pixmapToMat(self.left.pixmap())
        mat2 = self.pixmapToMat(self.right.pixmap())

        p1 = np.array(self.left.points, dtype=np.float32)
        p2 = np.array(self.right.points, dtype=np.float32)

        # Find homography
        h, mask = cv2.findHomography(p1, p2, cv2.RANSAC)

        # Use homography
        height, width, channels = mat2.shape
        warped = cv2.warpPerspective(mat1, h, (width, height))

        print("Warped & saved to warped.jpg")
        cv2.imwrite("warped.jpg", warped)


    def autoCorrelate(self):
        '''Try and find the correlation points automatically'''
        self.left.clearPoints()
        self.right.clearPoints()
        mat1 = self.pixmapToMat(self.left.pixmap())
        mat2 = self.pixmapToMat(self.right.pixmap())
        (p1, p2) = self.getPoints(mat1, mat2, 10)
        #print("autocorrelate",p1, p2)
        for p in p1:
            print(p)
            self.left.addPoint(p[0], p[1])
        for p in p2:
            self.right.addPoint(p[0], p[1])

if __name__ == '__main__':
    signal.signal(signal.SIGINT, signal.SIG_DFL)

    app = QApplication(sys.argv)
    corr = CorrelationApp()
    corr.setImages('images/IMG_20171026_161128.jpg', 'images/IMG_20171019_170326.jpg')
    corr.show()
    sys.exit(app.exec_())
