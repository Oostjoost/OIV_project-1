from qgis.PyQt.QtGui import QCursor, QColor
from qgis.PyQt.QtCore import Qt, QPoint
from qgis.core import *
from qgis.gui import *
from qgis._gui import QgsRubberBand
from math import pow

class SnapPointTool(QgsMapTool):
    def __init__(self, canvas):
        self.canvas = canvas
        QgsMapTool.__init__(self, canvas)
        self.layer           = None
        self.snapping        = False
        self.onGeometryAdded = None
        self.snapPt          = None
        self.startRotate     = False
        self.tempRubberBand  = None   
        self.vertexmarker    = None        
        self.snapLayer       = []
        self.setCursor(Qt.CrossCursor)

    def canvasReleaseEvent(self, event):
        clickedPt = None
        drawPoint = None
        snapAngle = None
        if event.button() == Qt.LeftButton:
            #als er gesnapt wordt -> bereken rotatie op basis van geklikt punt en snappunt
            if self.snapPt != None:
                mapPt,clickedPt = self.transformCoordinates(event.pos())
                drawPoint = self.toLayerCoordinates(self.layer, self.snapPt)
                snapAngle = clickedPt.azimuth(drawPoint)
                self.stopPointTool()
            #als er niets gesnapt wordt maar geroteerd bereken de rotatie op basis van de 2 punten in temprubberband
            elif self.startRotate:
                mapPt,clickedPt = self.transformCoordinates(event.pos())
                tempGeometry = self.tempRubberBand.asGeometry().asPolyline()
                drawPoint = self.toLayerCoordinates(self.layer, tempGeometry[0])
                snapAngle = drawPoint.azimuth(clickedPt)
                self.tempRubberBand.hide()
                self.stopPointTool()
            else:
            #als aan beide bovenstaande voorwaarden niet wordt voldaan wordt het pictogram gewoon geplaatst en is de hoek 0
                mapPt,drawPoint = self.transformCoordinates(event.pos())
            self.onGeometryAdded(drawPoint, snapAngle)
            self.snapPt = None
        #als de rechtermuisknop wordt gebruikt (1e keer) start het roteren
        if event.button() == Qt.RightButton:
            if not self.startRotate:
                self.start_to_rotate(event)
    
    #reset everything
    def stopPointTool(self):
        if self.tempRubberBand:
            self.canvas.scene().removeItem(self.tempRubberBand)
            self.tempRubberBand = None
        if self.vertexmarker:
            self.canvas.scene().removeItem(self.vertexmarker)
            self.vertexmarker = None
        self.startRotate = False
        self.canvas.refresh()

    #indien roteren -> init temprubberband
    def start_to_rotate(self, event):
        mapPt,layerPt = self.transformCoordinates(event.pos())
        color = QColor("black")
        color.setAlphaF(0.78)
        self.tempRubberBand = QgsRubberBand(self.canvas, QgsWkbTypes.LineGeometry)
        self.tempRubberBand.setWidth(4)
        self.tempRubberBand.setColor(color)
        self.tempRubberBand.setLineStyle(Qt.DotLine)
        self.tempRubberBand.show()
        self.tempRubberBand.addPoint(mapPt) 
        self.startRotate = True
    
    def canvasMoveEvent(self, event):
        mapPt,layerPt = self.transformCoordinates(event.pos())
        #indien er niet geroteerd wordt kan er worden gesnapt op vooraf gedfinieerde lagen
        if not self.startRotate:
            if self.snapping == True:
                self.snapPt = self.snap_to_point(event.pos(), layerPt)
                if self.vertexmarker != None:
                    self.vertexmarker.hide()
                if self.snapPt != None:
                    self.vertexmarker.setCenter(self.snapPt)
                    self.vertexmarker.show()
        else:
        #indien geroteerd wordt - teken de rubberband
            self.tempRubberBand.movePoint(mapPt)
            
    def snap_to_point(self, pos, layerPt):
        snapPoints  = []
        distance    = []
        snapPoint   = None
        val         = 0
        idx         = None
        if self.vertexmarker == None:
            self.vertexmarker    = QgsVertexMarker(self.canvas)
            self.vertexmarker.setColor(QColor(255, 0, 255))
            self.vertexmarker.setIconSize(5)
            self.vertexmarker.setIconType(QgsVertexMarker.ICON_X) # or ICON_CROSS, ICON_X
            self.vertexmarker.setPenWidth(5)
            self.vertexmarker.show()
        #berken snap toleratie en extent (rechthoek waarbinnen gesnapt kan worden)
        tolerance = pow(self.calcTolerance(pos),2)
        extent = self.calcExtent(layerPt, tolerance)
        #haal features op waarop gesnapt kan worden
        request = QgsFeatureRequest()
        request.setFilterRect(extent)
        request.setFlags(QgsFeatureRequest.ExactIntersect)
        for ilayer in self.snapLayer:
            try:
                index = None
                nearestId = None
                ifeature = None
                tuple = None
                #bereken voor elke snap laag de dichtsbijzinde feature
                index = QgsSpatialIndex(ilayer.getFeatures(request))
                nearestId = index.nearestNeighbor(layerPt, 2)[0]
                ifeature = next(ilayer.getFeatures(QgsFeatureRequest(nearestId)))
                #bereken per feature het dichtsbijzijnde lijn segment
                tuple = ifeature.geometry().closestSegmentWithContext(layerPt)
                #als de afstand tot het lijnsegment kleiner is als de tolerantie voeg toe als snappunt
                if tuple[0] != None and tuple[0] < tolerance:
                    distance.append(tuple[0])
                    snapPoints.append(tuple[1])
                else:
                    distance.append(tolerance + 1)
                    snapPoints.append('')             
            except:
                None
        #bereken het dichtsbijzijnde snappunt voor alle snap lagen
        if len(distance) > 0:
            val, idx = min((val, idx) for (idx, val) in enumerate(distance))
        if val <= tolerance and val != 0:
            snapPoint = self.toMapCoordinates(ilayer, snapPoints[idx])
        if snapPoint != None:
            return snapPoint
        else:
            return None
            
    #bereken snap extent
    def calcExtent(self, layerPt, tolerance):
        extent = QgsRectangle(layerPt.x() - tolerance,
                                  layerPt.y() - tolerance,
                                  layerPt.x() + tolerance,
                                  layerPt.y() + tolerance)
        return extent
                                  
    #bereken de tolerantie
    def calcTolerance(self, pos):
        pt1 = QPoint(pos.x(), pos.y())
        pt2 = QPoint(pos.x() + 20, pos.y())
        mapPt1,layerPt1 = self.transformCoordinates(pt1)
        mapPt2,layerPt2 = self.transformCoordinates(pt2)
        tolerance = layerPt2.x() - layerPt1.x()
        return tolerance
    
    #transormeer de coordinaten naar canvas en laag punten
    def transformCoordinates(self, canvasPt):
        return (self.toMapCoordinates(canvasPt),
                self.toLayerCoordinates(self.layer, canvasPt))