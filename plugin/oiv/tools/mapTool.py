"""Tool to draw lines and polygons on the map canvas"""

from math import cos, sin, radians

from qgis.PyQt.QtGui import QColor
from qgis.PyQt.QtCore import Qt, QPoint
from qgis.core import QgsDistanceArea, QgsFeatureRequest, QgsSpatialIndex, QgsPoint, QgsPointXY, QgsRectangle, QgsWkbTypes, QgsCircle, QgsGeometry
from qgis.gui import QgsVertexMarker, QgsMapTool, QgsRubberBand

class CaptureTool(QgsMapTool):
    """QgsMapTool to draw lines and polygons on the map canvas"""
    CAPTURE_LINE = 1
    CAPTURE_POLYGON = 2

    def __init__(self, canvas):
        QgsMapTool.__init__(self, canvas)
        self.canvas = canvas
        self.layer = None
        self.captureMode = None
        self.onGeometryAdded = None
        self.rubberBand = None
        self.tempRubberBand = None
        self.perpRubberBand = None
        self.perpRubberBand2 = None
        self.roundRubberBand = None
        self.capturedPoints = []
        self.capturing = False
        self.snapPt = None
        self.snapFeature = []
        self.vertexmarker = None
        self.snapLayer = []
        self.parent = None
        self.shiftPressed = False
        self.setCursor(Qt.CrossCursor)

    def canvasReleaseEvent(self, event):
        """#actie gekoppeld aan the mouse release event"""
        #als the perpendicular rubberbands bestaan reset zodat ze opnieuw kunnen worden getekend
        if self.perpRubberBand is not None:
            self.perpRubberBand.reset()
        if self.perpRubberBand2 is not None:
            self.perpRubberBand2.reset()
        #als er met de linker muis geklikt wordt en er wordt nog niet getekend -> start het tekenen
        #anders voeg het aangeklikte punt toe aan de verzameling
        if event.button() == Qt.LeftButton:
            if not self.capturing:
                self.startCapturing()
            if not self.shiftPressed:
                self.addVertex(event.pos())
            else:
                self.drawParallel(event.pos())
        #indien het de rechter muisknop is -> stop het tekenen en vertaal de punten tot een geometrie
        elif event.button() == Qt.RightButton:
            self.getCapturedGeometry()
            self.stopCapturing()

    def canvasMoveEvent(self, event):
        """acties gekoppeld aan het bewegen van de muis"""
        #converteer de muislocatie naar laag en scherm coordinaten
        mapPt, layerPt = self.transformCoordinates(event.pos())
        #kijk of er mogelijk gesnapt kan worden
        self.snapPt = self.snap_to_point(event.pos(), layerPt)
        if self.capturing:
            self.tempRubberBand.movePoint(mapPt)
        #pas de "gestippelde" rubberband aan aan de muispositie
        if self.captureMode == CaptureTool.CAPTURE_LINE and self.tempRubberBand != None and self.capturing:
            try:
                distance = QgsDistanceArea()
                m = distance.measureLine(self.tempRubberBand.getPoint(0, 0), mapPt)
                self.parent.lengte.setText(str(round(m, 2)) + ' meter')
                self.parent.oppervlakte.setText('n.v.t.')
            except: # pylint: disable=bare-except
                pass
        if self.captureMode == CaptureTool.CAPTURE_POLYGON and len(self.capturedPoints) >= 1 and self.capturing:
            distance = QgsDistanceArea()
            tempBandSize = self.tempRubberBand.numberOfVertices()
            m = distance.measureLine(self.tempRubberBand.getPoint(0, tempBandSize - 2), mapPt)
            self.parent.lengte.setText(str(round(m,2)) + ' meter')
            try:
                polygon = self.rubberBand.asGeometry().asPolygon()[0]
                temppolygon = self.tempRubberBand.asGeometry().asPolygon()[0]
                area = QgsDistanceArea()
                a = area.measurePolygon(polygon)
                b = area.measurePolygon(temppolygon)
                self.parent.oppervlakte.setText(str(round(a + b,2)) + ' vierkante-meter')
            except: # pylint: disable=bare-except
                pass
        #laat standaard het snappunt niet zien tenzij er gesnapt kan worden
        self.vertexmarker.hide()
        if self.snapPt is not None:
            self.vertexmarker.setCenter(self.snapPt)
            self.vertexmarker.show()

    def snap_to_point(self, pos, layerPt):
        """check of er gesnapt kan worden"""
        snapPoints = []
        distance = []
        self.snapFeature.clear()
        snapPoint = None
        val = None
        idx = None
        #initialiseer the vertexmarker (virtueel snappunt)
        if self.vertexmarker is None:
            self.vertexmarker = QgsVertexMarker(self.canvas)
            self.vertexmarker.setColor(QColor(255, 0, 255))
            self.vertexmarker.setIconSize(8)
            self.vertexmarker.setIconType(QgsVertexMarker.ICON_X) # or ICON_CROSS, ICON_X
            self.vertexmarker.setPenWidth(5)
            self.vertexmarker.show()
        #creeer lijst met alle mogelijke snappunten
        self.snapFeature = []
        #max snap tolerantie
        tolerance = pow(self.calcTolerance(pos),2)
        #bereken snap "vierkant" rondom muis lokatie
        extent = self.calcExtent(layerPt, tolerance)
        #vraag mogelijke features op binnen het extent
        request = QgsFeatureRequest()
        request.setFilterRect(extent)
        request.setFlags(QgsFeatureRequest.ExactIntersect)
        #bereken voor alle mogelijke snap lagen:
        for ilayer in self.snapLayer:
            index = None
            igeometry = None
            ifeature = None
            polygon = []
            closestSegm = None
            distSquared = None
            vertexCoord = None
            vertex = None
            prevVertex = None
            #bereken een spatial index
            if type(ilayer) != QgsRubberBand:
                try:
                    index = QgsSpatialIndex(ilayer.getFeatures(request))
                    if index is not None:
                        #bereken de dichtsbijzijnde feature per snaplaag
                        nearestId = index.nearestNeighbor(layerPt, 1)[0]
                        ifeature = next(ilayer.getFeatures(QgsFeatureRequest(nearestId)))
                        igeometry = ifeature.geometry()
                        #return dichtsbijzijnde lijnsegment van de features geometrie
                        closestSegm = igeometry.closestSegmentWithContext(layerPt)
                        #return dichtsbijzijnde punt van de features geometrie
                        vertexCoord, vertex, prevVertex, dummy, distSquared = igeometry.closestVertex(layerPt)
                except: # pylint: disable=bare-except
                    pass
            #snappen op bestaande "rubberband" lagen moet ook mogelijk zijn
            elif type(ilayer) == QgsRubberBand:
                #converyt rubberband geometry to QgsGeometry
                igeometry = ilayer.asGeometry()
                if igeometry is not None:
                    closestSegm = igeometry.closestSegmentWithContext(layerPt)
                    vertexCoord, vertex, prevVertex, dummy, distSquared = igeometry.closestVertex(layerPt)
            #als er een mogelijk snappunt is gevonden en deze valt binnen de tolerantie:
            #kijk eerst naar hoekpunt en dan pas naar lijnsegment(variabele -> tuple) (de voorkeur heeft snappen op hoekpunten)
            if distSquared is not None and distSquared <= tolerance and igeometry is not None and igeometry.isNull() is not False:
                if type(ilayer) == QgsRubberBand:
                    polygon = igeometry.asPolyline()
                elif ilayer.wkbType() == QgsWkbTypes.MultiLineString:
                    polygon = igeometry.asMultiPolyline()[0]
                elif ilayer.wkbType() == 1003 or ilayer.wkbType() == 6:
                    polygon = igeometry.asMultiPolygon()[0][0]
                else:
                    polygon = igeometry.asPolygon()[0]
                #voeg dit punt toe aan de mogelijke snappunten
                if polygon != [] and vertexCoord != QgsPointXY(0,0):
                    distance.append(distSquared)
                    snapPoints.append([vertexCoord, vertex, prevVertex, polygon])
            elif closestSegm is not None and closestSegm[1] != QgsPointXY(0, 0):
                if closestSegm[0] <= tolerance:
                    distance.append(closestSegm[0])
                    snapPoints.append([closestSegm[1], None, None, None])
            else:
                #Als het snappunt niet binnen de tolerantie valt, voeg dan een grote integer toe als snap afstand
                distance.append(tolerance + 9999)
                snapPoints.append([None, None, None, None])

        #als er mogelijke snappunten zijn:
        if distance is not None:
            #bereken de korste afstand met zijn id -> dit wordt het snappunt
            val, idx = min((val, idx) for (idx, val) in enumerate(distance))

        #construct the point to return as snappoint
        if val is not None:
            if val <= tolerance:
                #if type(ilayer) == QgsRubberBand:
                #    snapPoint = snapPoints[idx][0]
                #else:
                transformLayer = self.snapLayer[0]
                snapPoint = self.toMapCoordinates(transformLayer, snapPoints[idx][0])
                #sla zowel de feature als het punt op...de feature is nodig voor de perpendicular rubberbands
                if snapPoints[idx][1] is not None:
                    self.snapFeature.extend((snapPoints[idx][1], snapPoints[idx][2], snapPoints[idx][3]))
                else:
                    self.snapFeature.extend((None, None, None))
        return snapPoint

    def calcExtent(self, layerPt, tolerance):
        """bereken snap extent"""
        extent = QgsRectangle(layerPt.x() - tolerance,
                              layerPt.y() - tolerance,
                              layerPt.x() + tolerance,
                              layerPt.y() + tolerance)
        return extent

    def calcTolerance(self, pos):
        """calculate the tolerance of snapping"""
        pt1 = QPoint(pos.x(), pos.y())
        pt2 = QPoint(pos.x() + 10, pos.y())
        dummy, layerPt1 = self.transformCoordinates(pt1)
        dummy, layerPt2 = self.transformCoordinates(pt2)
        tolerance = layerPt2.x() - layerPt1.x()
        return tolerance

    #indien de gebruiker op backspace of delete klikt verwijder het laatst geregistreerde punt
    #indien de gebruiker op enter drukt betekent hetzelfde als de rechtermuisknop
    def keyPressEvent(self, event):
        """handel keypress events"""
        if event.key() == Qt.Key_Backspace or \
           event.key() == Qt.Key_Delete:
            self.removeLastVertex()
            event.ignore()
        if event.key() == Qt.Key_Return or event.key() == Qt.Key_Enter:
            self.getCapturedGeometry()
            self.stopCapturing()
        if event.key() == Qt.Key_Shift:
            self.shiftPressed = True

    def keyReleaseEvent(self, event):
        """handle shift key release event"""
        if event.key() == Qt.Key_Shift:
            self.shiftPressed = False

    def transformCoordinates(self, canvasPt):
        """transform een point to map coordinates and layer coordinates"""
        return (self.toMapCoordinates(canvasPt),
                self.toLayerCoordinates(self.layer, canvasPt))

    def startCapturing(self):
        """bij starten van het tekenen intialiseer de rubberbands"""
        #rubberband voor de al vastgelegde punten
        color = QColor("red")
        color.setAlphaF(0.2)
        self.rubberBand = QgsRubberBand(self.canvas, self.bandType())
        self.rubberBand.setWidth(2)
        self.rubberBand.setColor(color)
        self.rubberBand.show()

        #gestippelde rubberband -> voor het tekenen
        self.tempRubberBand = QgsRubberBand(self.canvas, self.bandType())
        self.tempRubberBand.setWidth(2)
        self.tempRubberBand.setColor(color)
        self.tempRubberBand.setLineStyle(Qt.DotLine)
        self.tempRubberBand.show()

        #2x loodrechte hulp tekenlijnen
        self.perpRubberBand = QgsRubberBand(self.canvas, QgsWkbTypes.LineGeometry)
        self.perpRubberBand.setWidth(1)
        self.perpRubberBand.setColor(QColor("blue"))
        self.perpRubberBand.setLineStyle(Qt.DotLine)
        self.perpRubberBand.show()

        self.perpRubberBand2 = QgsRubberBand(self.canvas, QgsWkbTypes.LineGeometry)
        self.perpRubberBand2.setWidth(1)
        self.perpRubberBand2.setColor(QColor("blue"))
        self.perpRubberBand2.setLineStyle(Qt.DotLine)
        self.perpRubberBand2.show()
        
        self.roundRubberBand = QgsRubberBand(self.canvas, QgsWkbTypes.LineGeometry)
        self.roundRubberBand.setWidth(1)
        borderColor = QColor("blue")
        borderColor.setAlphaF(0.5)
        fillColor = QColor("blue")
        fillColor.setAlphaF(0)
        self.roundRubberBand.setFillColor(fillColor)    
        self.roundRubberBand.setStrokeColor(borderColor)        
        self.roundRubberBand.setLineStyle(Qt.DotLine)
        self.roundRubberBand.show() 
        self.parent.straal.valueChanged.connect(self.roundrubberband_change_straal)        
        self.capturing = True

    def bandType(self):
        """bepaal het type rubberband (polygoon of line)"""
        if self.captureMode == CaptureTool.CAPTURE_POLYGON:
            return QgsWkbTypes.PolygonGeometry
        else:
            return QgsWkbTypes.LineGeometry

    def stopCapturing(self):
        """reset rubberbands als er gestopt wordt met tekenen"""
        if self.rubberBand:
            self.canvas.scene().removeItem(self.rubberBand)
            self.rubberBand = None
        if self.tempRubberBand:
            self.canvas.scene().removeItem(self.tempRubberBand)
            self.tempRubberBand = None
        if self.roundRubberBand:
            self.canvas.scene().removeItem(self.roundRubberBand)
            self.roundRubberBand = None
        if self.perpRubberBand:
            self.canvas.scene().removeItem(self.perpRubberBand)
            self.perpRubberBand = None
        if self.perpRubberBand2:
            self.canvas.scene().removeItem(self.perpRubberBand2)
            self.perpRubberBand2 = None              
        self.vertexmarker.hide()
        self.capturing = False
        self.capturedPoints = []
        self.canvas.refresh()

    def addVertex(self, canvasPoint):
        """bepaal het daadwerkelijk toe te voegen punt (snappunt of geklikt punt)"""
        polygon = None
        clickedPt = None
        if self.snapPt is not None:
            if self.snapFeature[2] is not None and self.snapFeature[1] is not None:
                polygon = self.snapFeature[2]
                clickedPt = polygon[self.snapFeature[1]]
            else:
                clickedPt = self.toLayerCoordinates(self.layer, canvasPoint)
            layerPt = self.toLayerCoordinates(self.layer, self.snapPt)
            mapPt = self.snapPt
            #bereken de snaphoek van het geklikte punt ten opzichte van het snappunt
            snapAngle = clickedPt.azimuth(layerPt)
            self.draw_perpendicularBand(layerPt, snapAngle)
        else:
            mapPt, layerPt = self.transformCoordinates(canvasPoint)
            if self.capturedPoints is not None:
                perpPt = self.capturedPoints[-1]
                snapAngle = layerPt.azimuth(perpPt) + 90
                self.draw_perpendicularBand(layerPt, snapAngle)
        #voeg het nieuwe map punt toe aan de rubberband
        self.rubberBand.addPoint(mapPt)
        #voeg het nieuwe layer punt toe aan de verzamelde punten
        self.capturedPoints.append(layerPt)
        #reset de temprubberband t.b.v. het volgende punt
        self.tempRubberBand.reset(self.bandType())
        if self.captureMode == CaptureTool.CAPTURE_LINE:
            self.tempRubberBand.addPoint(mapPt)
        elif self.captureMode == CaptureTool.CAPTURE_POLYGON:
            firstPoint = self.rubberBand.getPoint(0, 0)
            self.tempRubberBand.addPoint(firstPoint)
            self.tempRubberBand.movePoint(mapPt)
            self.tempRubberBand.addPoint(mapPt)

    def drawParallel(self, canvasPoint):
        """bepaal het daadwerkelijk toe te voegen punt (snappunt of geklikt punt)"""
        clickedPt = None
        if self.snapPt is not None and self.snapFeature[2] is None and self.capturedPoints is not None:
            clickedPt = self.toLayerCoordinates(self.layer, canvasPoint)
            layerPt = self.toLayerCoordinates(self.layer, self.snapPt)
            #bereken de snaphoek van het geklikte punt ten opzichte van het snappunt
            snapAngle = clickedPt.azimuth(layerPt) + 90
            bandSize  = self.rubberBand.numberOfVertices()
            lastPt    = self.rubberBand.getPoint(0, bandSize-1)
            self.draw_perpendicularBand(lastPt, snapAngle)

    def roundrubberband_change_straal(self):
        """change diameter of circular rubberband"""
        straal = self.parent.straal.value()
        startPt = self.capturedPoints[-1]
        test = QgsCircle(QgsPoint(startPt), straal)
        geom_cString = test.toCircularString()
        geom_from_curve = QgsGeometry(geom_cString)
        self.roundRubberBand.setToGeometry(geom_from_curve)

    def draw_perpendicularBand(self, startPt, angle):
        """bereken de haakse lijnen op basis van de gesnapte feature"""
        length = 100
        x1 = startPt.x() + length * sin(radians(angle))
        y1 = startPt.y() + length * cos(radians(angle))
        x2 = startPt.x() + length * sin(radians(angle + 180))
        y2 = startPt.y() + length * cos(radians(angle + 180))
        straal = self.parent.straal.value()
        test = QgsCircle(QgsPoint(startPt), straal)
        geom_cString = test.toCircularString()
        geom_from_curve = QgsGeometry(geom_cString)
        self.roundRubberBand.setToGeometry(geom_from_curve)
        self.snapLayer.append(self.roundRubberBand)
        #self.roundRubberBand.setToGeometry(geom_cString)
        self.perpRubberBand.addPoint(QgsPointXY(x1,y1))
        self.perpRubberBand.addPoint(QgsPointXY(x2,y2))
        self.perpRubberBand.show()
        #voeg de rubberband toe als mogelijke snap laag
        self.snapLayer.append(self.perpRubberBand)
        #als het een hoek betreft moeten er 2 haakse lijnen worden getekend
        if self.snapFeature is None or self.snapFeature[2] is None:
            if self.perpRubberBand2 in self.snapLayer:
                self.snapLayer.remove(self.perpRubberBand2)
        try:
            if self.snapFeature[2] is not None:
                x3 = startPt.x() + length * sin(radians(angle + 90))
                y3 = startPt.y() + length * cos(radians(angle + 90))
                x4 = startPt.x() + length * sin(radians(angle + 270))
                y4 = startPt.y() + length * cos(radians(angle + 270))
                self.perpRubberBand2.addPoint(QgsPointXY(x3,y3))
                self.perpRubberBand2.addPoint(QgsPointXY(x4,y4))
                self.perpRubberBand2.show()
                #voeg de rubberband toe als mogelijke snap laag
                self.snapLayer.append(self.perpRubberBand2)
        except:  # pylint: disable=bare-except
            pass

    def removeLastVertex(self):
        """verwijder het laatste punt (backspace of delete)"""
        if not self.capturing:
            return
        bandSize = self.rubberBand.numberOfVertices()
        tempBandSize = self.tempRubberBand.numberOfVertices()
        numPoints = len(self.capturedPoints)
        if bandSize < 1 or numPoints < 1:
            return
        self.rubberBand.removePoint(-1)
        if bandSize > 1:
            if tempBandSize > 1:
                point = self.rubberBand.getPoint(0, bandSize-2)
                self.tempRubberBand.movePoint(tempBandSize-2,
                                              point)
        else:
            self.tempRubberBand.reset(self.bandType())
        del self.capturedPoints[-1]

    def getCapturedGeometry(self):
        """return captured points"""
        snapAngle = None
        points = self.capturedPoints
        #voor lijn -> minimaal 2 punten
        if self.captureMode == CaptureTool.CAPTURE_LINE:
            if len(points) < 2:
                return None
        #voor polygoon -> minimaal 3 punten
        if self.captureMode == CaptureTool.CAPTURE_POLYGON:
            if len(points) < 3:
                return None
        # Close polygon door het eerste punt ook als laatste toe te voegen
        if self.captureMode == CaptureTool.CAPTURE_POLYGON:
            points.append(points[0])
        #geeft zowel de punten als ook de hoek terug (niet nodig bij lijn en polygoon, maar uniformering ivm punten)
        self.onGeometryAdded(points, snapAngle)
