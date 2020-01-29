from qgis.PyQt.QtGui import QCursor, QColor
from qgis.PyQt.QtCore import Qt, QPoint
from qgis.core import *
from qgis.gui import *
from .utils import *
from qgis._gui import QgsRubberBand

class MovePointTool(QgsMapToolIdentify):
    def __init__(self, canvas, layer):
        QgsMapToolIdentify.__init__(self, canvas)
        self.canvas         = canvas
        self.setCursor(Qt.CrossCursor)
        self.layer          = layer
        self.dragging       = False
        self.fields         = None
        self.onMoved        = None
        self.point          = None
        self.startRotate    = False
        self.tempRubberBand = None 
        self.vertexMarker   = None

    def canvasPressEvent(self, event):
        #op welke feature wordt er geklikt
        found_features = self.identify(event.x(), event.y(), self.TopDownStopAtFirst, self.VectorLayer)
        #check type van de laag, het werkt alleen voor point layers
        type_check = check_layer_type(found_features[0].mLayer)
        self.idlayer = found_features[0].mLayer
        feature  = found_features[0].mFeature
        self.fid = feature.id()
        #indien de linkesmuisnop wordt geklikt, het betreft een point layer en er is een feature gevonden -> verslepen
        if event.button() == Qt.LeftButton:
            if (len(found_features) > 0 and type_check == "Point"):
                self.dragging = True
                #init drag point
                self.vertexmarker = QgsVertexMarker(self.canvas)
                self.vertexmarker.setColor(QColor(0, 0, 255))
                self.vertexmarker.setIconSize(5)
                self.vertexmarker.setIconType(QgsVertexMarker.ICON_X)
                self.vertexmarker.setPenWidth(3)
                self.vertexmarker.show()
            #anders doe niets
            else:
                self.dragging = False
                self.fid  = None
        #indien de rechtermuisknop wordt geklikt -> roteren
        if event.button() == Qt.RightButton:
            if (len(found_features) > 0 and type_check == "Point"):
                if not self.startRotate:
                    self.start_to_rotate(event)
            else:
                self.startRotate = False
                self.fid = None
         
    def start_to_rotate(self, event):
        mapPt,layerPt = self.transformCoordinates(event.pos())
        #init tempRubberband indicating rotation
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
        #als verslepen -> verplaats de indicatieve marker
        if self.dragging:
            mapPt, layerPt = self.transformCoordinates(event.pos())
            self.point = layerPt
            self.vertexmarker.setCenter(mapPt)
        #als roteren -> teken de tempRubberband als lijn
        if self.startRotate:
            mapPt, layerPt = self.transformCoordinates(event.pos())
            self.tempRubberBand.movePoint(mapPt)
    
    #transformeer muis lokatie naar canvas punt en laag punt 
    def transformCoordinates(self, canvasPt):
        return (self.toMapCoordinates(canvasPt),
                self.toLayerCoordinates(self.layer, canvasPt))

    def canvasReleaseEvent(self, event):
        #als verslepen -> pas de geometry van de betreffende feature aan
        if self.dragging:
            self.vertexmarker.hide()
            geom = QgsGeometry.fromPointXY(self.point)
            self.idlayer.dataProvider().changeGeometryValues({self.fid : geom})
            self.idlayer.commitChanges()
            self.idlayer.triggerRepaint()
            self.stop_moveTool()
        #als roteren -> pas de rotatie van de betreffende feature aan op basis van de loodrechte lijn tussen muisklik en bestaand punt
        if self.startRotate:
            self.tempRubberBand.hide()
            mapPt,clickedPt = self.transformCoordinates(event.pos())
            tempGeometry = self.tempRubberBand.asGeometry().asPolyline()
            drawPoint = self.toLayerCoordinates(self.layer, tempGeometry[0])
            field = self.idlayer.fields().indexOf("rotatie")
            rotation = drawPoint.azimuth(clickedPt)
            attrs = {field : rotation}
            self.idlayer.dataProvider().changeAttributeValues({self.fid : attrs})
            self.idlayer.commitChanges()
            self.idlayer.triggerRepaint()
            self.stop_moveTool()
        
    #reset rubberbands
    def stop_moveTool(self):
        if self.tempRubberBand != None:
            self.canvas.scene().removeItem(self.tempRubberBand)
            self.tempRubberBand = None
        if self.vertexMarker != None:
            self.canvas.scene().removeItem(self.vertexMarker)
            self.vertexMarker = None
        self.fid  = None
        self.startRotate = False
        self.dragging = False
        self.onMoved()
        self.canvas.refresh()