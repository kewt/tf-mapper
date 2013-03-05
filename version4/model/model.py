
import di, view
import math, uuid
from entity import *
from PyQt4 import QtCore, QtGui


__author__ = 'thornag'

class Map:
    __rooms={}
    __levels={}
    def levels(self):
        return self.__levels

    def registerRoom(self, room):
        self.__rooms[room.getId()] = room

    def registerLevel(self, level):
        self.__levels[level.getMapIndex()] = level


class Direction:
    N=1
    NE=2
    E=4
    SE=8
    S=16
    SW=32
    W=64
    NW=128
    U=256
    D=512

class CoordinatesHelper:
    __config = di.ComponentRequest('Config')

    def getExitPointFromPoint(self, QPointF, direction):
        QPoint = QtCore.QPointF(QPointF.x(), QPointF.y())

        objectSize = self.__config.getSize()
        midPoint = self.__config.getMidPoint()

        if direction == Direction.N:
            newPosition = QPoint + QtCore.QPointF(midPoint, 0)
        if direction == Direction.NE:
            newPosition = QPoint + QtCore.QPointF(objectSize, 0)
        if direction == Direction.E:
            newPosition = QPoint + QtCore.QPointF(objectSize, midPoint)
        if direction == Direction.SE:
            newPosition = QPoint + QtCore.QPointF(objectSize, objectSize)
        if direction == Direction.S:
            newPosition = QPoint + QtCore.QPointF(midPoint, objectSize)
        if direction == Direction.SW:
            newPosition = QPoint + QtCore.QPointF(0, objectSize)
        if direction == Direction.W:
            newPosition = QPoint + QtCore.QPointF(0, midPoint)
        if direction == Direction.NW:
            newPosition = QPoint + QtCore.QPointF(0, 0)

        return newPosition

    def getExitPoint(self, exitDescription):
        room, direction = exitDescription

        return self.getExitPointFromPoint(room.getView().pos(), direction)



    def snapToGrid(self, QPoint):
        x = (QPoint.x() / self.__config.getSize()) * self.__config.getSize()
        y = QPoint.y() / self.__config.getSize() * self.__config.getSize()
        if QPoint.x() % self.__config.getSize() > self.__config.getMidPoint():
            x += self.__config.getSize()
        if QPoint.y() % self.__config.getSize() > self.__config.getMidPoint():
            y += self.__config.getSize()

        return QtCore.QPoint(x, y)

    def centerFrom(self, QPoint):
        return QtCore.QPoint(QPoint.x()-(self.__config.getSize()/2), QPoint.y()-(self.__config.getSize()/2))

    def movePointInDirection(self, QPoint, direction):

        moveBy = self.__config.getSize()

        if direction == Direction.N:
            newPosition = QPoint + QtCore.QPointF(0, -1 * moveBy)
        if direction == Direction.NE:
            newPosition = QPoint + QtCore.QPointF(moveBy, -1 * moveBy)
        if direction == Direction.E:
            newPosition = QPoint + QtCore.QPointF(moveBy, 0)
        if direction == Direction.SE:
            newPosition = QPoint + QtCore.QPointF(moveBy, 1 * moveBy)
        if direction == Direction.S:
            newPosition = QPoint + QtCore.QPointF(0, moveBy)
        if direction == Direction.SW:
            newPosition = QPoint + QtCore.QPointF(-1 * moveBy, moveBy)
        if direction == Direction.W:
            newPosition = QPoint + QtCore.QPointF(-1 * moveBy, 0)
        if direction == Direction.NW:
            newPosition = QPoint + QtCore.QPointF(-1 * moveBy, -1 * moveBy)

        return newPosition

    def getSelectionAreaFromPoint(self, QPointF):
        return QtCore.QRectF(QPointF.x()+self.__config.getExitLength(), QPointF.y()+self.__config.getExitLength(), self.__config.getEdgeLength(), self.__config.getEdgeLength())

class Config(object):
    __exitLength=10
    __edgeLength=21
    def getSize(self):
        return self.__edgeLength + (2 * self.__exitLength)

    def getExitLength(self):
        return self.__exitLength

    def getEdgeLength(self):
        return self.__edgeLength

    def getMidPoint(self):
        return math.ceil(self.getSize()/float(2))

class RoomFactory:
    __config = di.ComponentRequest('Config')
    __helper = di.ComponentRequest('CoordinatesHelper')
    __map = di.ComponentRequest('Map')

    def createInDirection(self, direction, QPoint, QGraphicsScene):
        return self.createAt(self.__helper.movePointInDirection(QPoint, direction), QGraphicsScene)

    def createAt(self, QPoint, QGraphicsScene):
        room = self.spawnRoom()
        QGraphicsScene.addItem(room.getView())
        room.setPosition(QPoint)
        boundingRect = QGraphicsScene.itemsBoundingRect()
        boundingRect.adjust(-50,-50,50,50)
        QGraphicsScene.setSceneRect(boundingRect)
        room.setLevel(QGraphicsScene.getModel())
        return room

    def spawnRoom(self):
        room = Room()
        room.setId(uuid.uuid1())
        viewRoom = view.Room()
        room.setView(viewRoom)
        self.__map.registerRoom(room)
        return room

    def spawnLink(self, linkLess=False):
        link = Link()
        if(linkLess): return link
        viewLink = view.Link()
        link.setView(viewLink)
        return link

    def linkRoomsBetweenLevels(self, leftRoom, leftExit, rightRoom, rightExit):
        return self.linkRooms(leftRoom, leftExit, rightRoom, rightExit)


    def linkRooms(self, leftRoom, leftExit, rightRoom, rightExit, QGraphicsScene=None):
        #need to validate first
        if(leftRoom.hasLinkAt(leftExit) and not leftRoom.linkAt(leftExit).pointsAt(rightRoom)):
            raise Exception('Left room already links somewhere through given exit')

        if(rightRoom.hasLinkAt(rightExit) and not rightRoom.linkAt(rightExit).pointsAt(leftRoom)):
            raise Exception('Left room already links somewhere through given exit')

        #good to link
        link = self.spawnLink(QGraphicsScene is None)
        link.setLeft(leftRoom, leftExit)
        link.setRight(rightRoom, rightExit)
        leftRoom.addLink(leftExit, link)
        rightRoom.addLink(rightExit, link)

        if QGraphicsScene is None: return

        link.getView().redraw()
        QGraphicsScene.addItem(link.getView())

    def spawnLevel(self, mapIndex):
        level = Level(mapIndex)
        level.setId(uuid.uuid1())
        viewLevel = view.uiMapLevel()
        viewLevel.setBackgroundBrush(QtGui.QColor(217, 217, 217))
        level.setView(viewLevel)
        self.__map.registerLevel(level)
        return level


class Registry:
    currentlyVisitedRoom=None
    roomShadow=None
    def __init__(self):
        self.__rooms=[]


class Navigator:
    __map=di.ComponentRequest('Map')
    __config=di.ComponentRequest('Config')
    __registry=di.ComponentRequest('Registry')
    __roomFactory=di.ComponentRequest('RoomFactory')
    __coordinatesHelper=di.ComponentRequest('CoordinatesHelper')
    __enableCreation=False
    __enableAutoPlacement=True

    def switchLevel(self, newLevel):
        levels = self.__map.levels()
        if newLevel in levels:
            self.__registry.currentLevel.getView().views()[0].setScene(levels[newLevel].getView())

    def goLevelDown(self):
        return self.switchLevel(self.__registry.currentLevel.getMapIndex() - 1)

    def goLevelUp(self):
        return self.switchLevel(self.__registry.currentLevel.getMapIndex() + 1)

    def removeRoom(self):
        currentScene = self.__registry.currentLevel.getView()
        items = currentScene.selectedItems()
        for item in items:
            print 'deleting'
            item.getModel().delete()


    def enableCreation(self, enable):
        self.__enableCreation = bool(enable)

    def enableAutoPlacement(self, enable):
        self.__enableAutoPlacement = bool(enable)

    def goUp(self):
        print 'goUp'
        return self.goFromActive(Direction.U, Direction.D)

    def goDown(self):
        print 'goDown'
        return self.goFromActive(Direction.D, Direction.U)

    def goNorth(self):
        return self.goFromActive(Direction.N, Direction.S)

    def goNorthEast(self):
        return self.goFromActive(Direction.NE, Direction.SW)

    def goEast(self):
        return self.goFromActive(Direction.E, Direction.W)

    def goSouthEast(self):
        return self.goFromActive(Direction.SE, Direction.NW)

    def goSouth(self):
        return self.goFromActive(Direction.S, Direction.N)

    def goSouthWest(self):
        return self.goFromActive(Direction.SW, Direction.NE)

    def goWest(self):
        return self.goFromActive(Direction.W, Direction.E)

    def goNorthWest(self):
        return self.goFromActive(Direction.NW, Direction.SE)

    def goFromActive(self, fromExit, toExit):
        if self.__registry.currentlyVisitedRoom is None:
            return QtGui.QMessageBox.question(self.__registry.mainWindow, 'Alert', 'There is no active room selected', QtGui.QMessageBox.Ok)

        currentRoom = self.__registry.currentlyVisitedRoom

        return self.go(currentRoom, fromExit, toExit)

    def dropRoomFromShadow(self):
        if self.__registry.currentlyVisitedRoom is None:
            self.__registry.roomShadow.stopProcess()
            return QtGui.QMessageBox.question(self.__registry.mainWindow, 'Alert', 'There is no active room selected', QtGui.QMessageBox.Ok)

        currentRoom = self.__registry.currentlyVisitedRoom
        fromExit = self.__registry.roomShadow.exitBy()
        toExit = self.__registry.roomShadow.entryBy()
        dropAtPoint = self.__registry.roomShadow.pos()

        if currentRoom.getView().pos() == dropAtPoint:
            self.__registry.roomShadow.stopProcess()
            return

        destinationRoom=None

        #collision check at new point
        for item in currentRoom.getView().scene().items(self.__coordinatesHelper.getSelectionAreaFromPoint(dropAtPoint)):
            if isinstance(item, view.Room):
                destinationRoom = item
                break

        if destinationRoom is not None:
            if(destinationRoom.getModel().hasExit(toExit)):
                self.__registry.roomShadow.stopProcess()
                return QtGui.QMessageBox.question(self.__registry.mainWindow, 'Alert', 'There is already an exit at entry direction from destination room', QtGui.QMessageBox.Ok)

            destinationRoom.getModel().addExit(toExit)
            self.markVisitedRoom(destinationRoom.getModel())
            newRoom = destinationRoom.getModel()
        else:
            newRoom = self.__roomFactory.createAt(dropAtPoint, currentRoom.getView().scene())
            newRoom.addExit(toExit)
            self.markVisitedRoom(newRoom)

        currentRoom.addExit(fromExit)
        self.__roomFactory.linkRooms(currentRoom, fromExit, newRoom, toExit, currentRoom.getView().scene())

    def go(self, currentRoom, fromExit, toExit):

        """
        To refactor this horros
        Think about a proper navigator that can accept any object type and move it on the grid using coordinatesHelper
         this class should not be responsible for any room creation / collision check
        """
        if currentRoom.hasExit(fromExit) and (not self.__enableCreation or self.__enableAutoPlacement):
            """
            @todo: This has to be changed when exit links are operational to use links rather than positions
            """

            exitLink = currentRoom.linkAt(fromExit)
            print exitLink
            destinationRoom = exitLink.getDestinationFor(currentRoom)
            self.markVisitedRoom(destinationRoom)
            if fromExit == Direction.U: self.goLevelUp()
            elif fromExit == Direction.D: self.goLevelDown()

        elif (self.__enableCreation):

            if fromExit in [Direction.U, Direction.D] or toExit in [Direction.D, Direction.U]:
                print 'creating multilevel room'
                #what happens when changing level?
                #if create mode check for collision and if no create ate the same coordinates but on different scene
                otherLevelIndex = self.__registry.currentLevel.getMapIndex()
                otherLevelIndex += 1 if fromExit == Direction.U else -1
                levels = self.__map.levels()
                otherLevel = levels[otherLevelIndex] if otherLevelIndex in levels else self.__roomFactory.spawnLevel(otherLevelIndex)

                destinationRoom = otherLevel.getView().itemAt(currentRoom.getView().pos())

                if destinationRoom is not None:
                    newRoom = destinationRoom.getModel()
                else:
                    newRoom = self.__roomFactory.createAt(currentRoom.getView().pos(), otherLevel.getView())

                currentRoom.addExit(fromExit)
                newRoom.addExit(toExit)

                self.markVisitedRoom(newRoom)

                if fromExit == Direction.U: self.goLevelUp()
                else: self.goLevelDown()

                self.__roomFactory.linkRoomsBetweenLevels(currentRoom, fromExit, newRoom, toExit)

                return

            """
            if auto placement is enabled, we will simply place a room on the map, but if it is disabled
            we need to use something like a mask model that can be moved around the map and placed by
            hitting the keypad5 key, this should allow for custom linkage between rooms
            """

            destinationRoom=None
            destinationPoint = self.__coordinatesHelper.movePointInDirection(currentRoom.getView().pos(), fromExit)
            for item in currentRoom.getView().scene().items(self.__coordinatesHelper.getSelectionAreaFromPoint(destinationPoint)):
                if isinstance(item, view.Room):
                    destinationRoom = item
                    break

            if not self.__enableAutoPlacement:
                roomShadow = self.__registry.roomShadow
                shadowLink = self.__registry.shadowLink
                if not roomShadow.inProcess():
                    if currentRoom.getView().scene() is not roomShadow.scene():
                        currentRoom.getView().scene().addItem(roomShadow)
                        currentRoom.getView().scene().addItem(shadowLink)
                    if destinationRoom is not None:
                        pass
                    else:
                        newPosition = self.__coordinatesHelper.movePointInDirection(currentRoom.getView().pos(), fromExit)
                        roomShadow.setPos(newPosition)

                    roomShadow.setVisible(True)
                    shadowLink.setVisible(True)
                    roomShadow.setInProcess(True)
                    roomShadow.setExitBy(fromExit)
                    roomShadow.setEntryBy(toExit)
                    shadowLink.redraw()
                else:
                    newPosition = self.__coordinatesHelper.movePointInDirection(roomShadow.pos(), fromExit)
                    roomShadow.setPos(newPosition)
                    roomShadow.setEntryBy(toExit)
                    shadowLink.redraw()
            else:

                currentRoom.addExit(fromExit)

                if destinationRoom is not None:
                    destinationRoom.getModel().addExit(toExit)
                    self.markVisitedRoom(destinationRoom.getModel())
                    newRoom = destinationRoom.getModel()
                else:
                    newRoom = self.__roomFactory.createInDirection(fromExit, currentRoom.getView().pos(), currentRoom.getView().scene())
                    newRoom.addExit(toExit)
                    self.markVisitedRoom(newRoom)

                self.__roomFactory.linkRooms(currentRoom, fromExit, newRoom, toExit, currentRoom.getView().scene())
                """
                @todo: Need to refactor this so navigator doesnt create set active
                """

    def markVisitedRoom(self, roomModel):
        if self.__registry.currentlyVisitedRoom is not None:
            self.__registry.currentlyVisitedRoom.setCurrentlyVisited(False)
            self.__registry.currentlyVisitedRoom.getView().update()

        self.__registry.currentlyVisitedRoom = roomModel

        roomModel.setCurrentlyVisited(True)
        roomModel.getView().clearFocus()

        if len(roomModel.getView().scene().views()):
            roomModel.getView().scene().views()[0].centerOn(roomModel.getView())

        for item in roomModel.getView().scene().selectedItems():
            item.setSelected(False)

        roomModel.getView().update()






