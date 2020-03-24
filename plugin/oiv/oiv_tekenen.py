"""
/***************************************************************************
 oiv
                                 A QGIS plugin
 place oiv objects
                              -------------------
        begin                : 2019-08-15
        git sha              : $Format:%H$
        copyright            : (C) 2019 by Joost Deen
        email                : jdeen@vrnhn.nl
        versie               : 2.9.93
 ***************************************************************************/
/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""
import os

from qgis.PyQt import uic
from qgis.PyQt.QtWidgets import QDockWidget, QPushButton, QMessageBox
from qgis.PyQt.QtCore import Qt

from qgis.core import QgsFeature, QgsGeometry
from qgis.utils import iface

from .tools.mapTool import CaptureTool
from .tools.identifyTool import SelectTool
from .tools.utils import check_layer_type, get_draw_layer_attr, getlayer_byname, write_layer, user_input_label, nearest_neighbor
from .oiv_stackwidget import oivStackWidget

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'oiv_tekenen_widget.ui'))

class oivTekenWidget(QDockWidget, FORM_CLASS):
    """Organize all draw features on the map"""
    read_config = None
    iface= None
    canvas = None
    tekenTool = None
    identifier = None
    parentlayer_name = None
    draw_layer_type = None
    draw_layer = None
    editable_layers = []
    objectwidget = None
    lineTool = None
    polygonTool = None
    moveTool = None
    selectTool = None
    #id van pictogram
    snappicto = ['1', '10', '32', '47', '148', '149', '150', '151', '152',\
                 '1011', 'Algemeen', 'Voorzichtig', 'Waarschuwing', 'Gevaar'] 
    moveLayerNames = []
    snapLayerNames = ["Bouwlagen", "BAG panden", "Object terrein",\
                        "Bouwkundige veiligheidsvoorzieningen", "Ruimten"]

    def __init__(self, parent=None):
        """Constructor."""
        super(oivTekenWidget, self).__init__(parent)
        self.setupUi(self)

        self.iface = iface
        self.stackwidget = oivStackWidget()

        self.lengte_label.setVisible(False)
        self.lengte.setVisible(False)
        self.straal_label.setVisible(False)
        self.straal.setVisible(False)        
        self.oppervlakte_label.setVisible(False)
        self.oppervlakte.setVisible(False)

        self.move.clicked.connect(self.run_move_point)
        self.identify.clicked.connect(self.run_edit_tool)
        self.select.clicked.connect(self.run_select_tool)
        self.delete_f.clicked.connect(self.run_delete_tool)
        self.pan.clicked.connect(self.activatePan)
        self.terug.clicked.connect(self.close_teken_show_object)

    def connect_buttons(self, configLines):
        """connect button and signals to the real action run"""
        #skip first line because of header
        for line in configLines[1:]:
            layerName = line[0]
            csvPath = line[1]

            if csvPath:
                self.editable_layers.append(layerName)
                layer = getlayer_byname(layerName)
                layerType = check_layer_type(layer)

                if layerType == "Point":
                    self.moveLayerNames.append(layerName)

                actionList = self.read_config_file(csvPath)
                self.ini_action(actionList, layerName)

    def ini_action(self, actionList, run_layer):
        """connect all the buttons to the action"""
        for action in actionList:
            buttonNr = action[0]
            buttonName = str(action[1].lower())
            strButton = self.findChild(QPushButton, buttonName)

            if strButton:
                #set tooltip per buttonn
                strButton.setToolTip(buttonName)
                #geef met de signal ook mee welke knop er is geklikt -> nr
                strButton.clicked.connect(lambda dummy='dummyvar', rlayer=run_layer, who=buttonNr: self.run_tekenen(dummy, rlayer, who))

    def read_config_file(self, file):
        """Read lines from input file and convert to list"""
        configList = []
        basepath = os.path.dirname(os.path.realpath(__file__))

        with open(basepath + file, 'r') as inputFile:
            lines = inputFile.read().splitlines()

        for line in lines:
            configList.append(line.split(','))
        inputFile.close()

        return configList

    def activatePan(self):
        """trigger pan function to loose other functions"""
        self.iface.actionPan().trigger()

    def run_edit_tool(self):
        """activate the edit feature tool"""
        try:
            self.selectTool.geomSelected.disconnect()
        except: # pylint: disable=bare-except
            pass
        self.selectTool.read_config = self.read_config
        self.canvas.setMapTool(self.selectTool)
        self.selectTool.geomSelected.connect(self.edit_attribute)

    def run_select_tool(self):
        """activate the select feature tool"""
        try:
            self.selectTool.geomSelected.disconnect()
        except: # pylint: disable=bare-except
            pass
        self.canvas.setMapTool(self.selectTool)
        self.selectTool.geomSelected.connect(self.select_feature)

    def select_feature(self, ilayer, ifeature):
        """catch emitted signal from selecttool"""
        self.iface.setActiveLayer(ilayer)
        ids = []
        ids.append(ifeature.id())
        ilayer.selectByIds(ids)
        ilayer.startEditing()
        self.selectTool.geomSelected.disconnect(self.select_feature)

    def run_delete_tool(self):
        """activate delete feature tool"""
        try:
            self.selectTool.geomSelected.disconnect()
        except: # pylint: disable=bare-except
            pass
        self.selectTool.read_config = self.read_config
        self.canvas.setMapTool(self.selectTool)
        self.selectTool.geomSelected.connect(self.delete_feature)

    def delete_feature(self, ilayer, ifeature):
        """controleer of het een feature betreft binnenn de lijst editable_layers"""
        if ilayer.name() in self.editable_layers:
            self.iface.setActiveLayer(ilayer)
            ids = []
            ids.append(ifeature.id())
            ilayer.selectByIds(ids)
            ilayer.startEditing()
            reply = QMessageBox.question(self.iface.mainWindow(), 'Continue?',
                                         "Weet u zeker dat u de geselecteerde feature wilt weggooien?", QMessageBox.Yes, QMessageBox.No)
            if reply == QMessageBox.No:
                #als "nee" deselecteer alle geselecteerde features
                self.selectTool.geomSelected.disconnect(self.delete_feature)
                ilayer.selectByIds([])
            elif reply == QMessageBox.Yes:
                #als "ja" -> verwijder de feature op basis van het unieke feature id
                ilayer.deleteFeature(ifeature.id())
                ilayer.commitChanges()
                self.selectTool.geomSelected.disconnect(self.delete_feature)
                self.run_delete_tool()
        #als er een feature is aangeklikt uit een andere laag, geef dan een melding
        else:
            reply = QMessageBox.information(self.iface.mainWindow(), 'Geen tekenlaag!', 
                                            "U heeft geen feature op een tekenlaag aangeklikt!\n\nKlik a.u.b. op de juiste locatie.\n\n\
                                            Weet u zeker dat u iets wilt weggooien?", QMessageBox.Yes, QMessageBox.No)
            if reply == QMessageBox.No:
                self.selectTool.geomSelected.disconnect(self.delete_feature)
                ilayer.selectByIds([])
            else:
                self.selectTool.geomSelected.disconnect(self.delete_feature)
                self.run_delete_tool()

    def edit_attribute(self, ilayer, ifeature):
        """open het formulier van een feature in een dockwidget, zodat de attributen kunnen worden bewerkt"""
        self.iface.addDockWidget(Qt.RightDockWidgetArea, self.stackwidget)
        self.stackwidget.parentWidget = self
        self.stackwidget.open_feature_form(ilayer, ifeature)
        self.close()
        self.stackwidget.show()
        self.selectTool.geomSelected.disconnect(self.edit_attribute)
        self.run_edit_tool()

    def run_move_point(self):
        """om te verschuiven/roteren moeten de betreffende lagen op bewerken worden gezet"""
        for lyrName in self.moveLayerNames:
            moveLayer = getlayer_byname(lyrName)
            moveLayer.startEditing()
        self.moveTool.onMoved = self.stop_moveTool
        self.canvas.setMapTool(self.moveTool)

    def stop_moveTool(self):
        """na de actie verschuiven/bewerken moeten de betreffende lagen opgeslagen worden en bewerken moet worden uitgezet"""
        for lyrName in self.moveLayerNames:
            moveLayer = getlayer_byname(lyrName)
            moveLayer.commitChanges()        
        self.activatePan()

    def run_tekenen(self, dummy, run_layer, feature_id):
        """activate the right draw action"""
        snapLayer = []
        #welke pictogram is aangeklikt en wat is de bijbehorende tekenlaag
        self.identifier = feature_id
        self.draw_layer = getlayer_byname(run_layer)
        #betreft het een punt, lijn of polygoon laag?
        self.draw_layer_type = check_layer_type(self.draw_layer)
        #wat is the parentlayer, uitlezen vanuit de config file
        self.parentlayer_name = get_draw_layer_attr(run_layer, "parent_layer", self.read_config)
        #aan welke lagen kan worden gesnapt?
        for name in self.snapLayerNames:
            lyr = getlayer_byname(name)
            snapLayer.append(lyr)
        if self.draw_layer_type == "Point":
            self.tekenTool.snapPt = None
            self.tekenTool.snapping = False
            self.tekenTool.startRotate = False
            self.tekenTool.snapLayer = snapLayer
            if self.identifier in self.snappicto:
                self.tekenTool.snapping = True
            self.tekenTool.layer = self.draw_layer
            self.canvas.setMapTool(self.tekenTool)
            self.lengte_label.setVisible(False)
            self.lengte.setVisible(False)
            self.straal.setVisible(False)
            self.straal_label.setVisible(False)
            self.oppervlakte_label.setVisible(False)
            self.oppervlakte.setVisible(False) 
            self.tekenTool.onGeometryAdded = self.place_feature
        elif self.draw_layer_type == "Line":
            self.lineTool.layer = self.draw_layer
            self.lineTool.snapLayer = snapLayer
            self.lineTool.canvas = self.canvas
            self.lineTool.onGeometryAdded = self.place_feature
            self.lineTool.captureMode = 1
            self.canvas.setMapTool(self.lineTool)
            self.lengte_label.setVisible(True)
            self.lengte.setVisible(True)
            self.straal.setVisible(True)
            self.straal_label.setVisible(True)            
            self.oppervlakte_label.setVisible(False)
            self.oppervlakte.setVisible(False)
            self.lineTool.parent = self
        elif self.draw_layer_type == "Polygon":
            self.polygonTool.layer = self.draw_layer
            self.polygonTool.snapLayer = snapLayer
            self.polygonTool.canvas = self.canvas
            self.polygonTool.onGeometryAdded = self.place_feature
            self.polygonTool.captureMode = 2
            self.canvas.setMapTool(self.polygonTool)
            self.lengte_label.setVisible(True)
            self.lengte.setVisible(True)
            self.straal.setVisible(True)
            self.straal_label.setVisible(True)             
            self.oppervlakte_label.setVisible(True)
            self.oppervlakte.setVisible(True)
            self.polygonTool.parent = self

    def place_feature(self, points, snapAngle):
        """Save and place feature on the canvas"""
        childFeature = QgsFeature()
        self.iface.setActiveLayer(self.draw_layer)
        #converteer lijst van punten naar QgsGeometry, afhankelijk van soort geometrie
        if self.draw_layer_type == "Point":
            childFeature.setGeometry(QgsGeometry.fromPointXY(points))
            geom = points
        elif self.draw_layer_type == "Line":
            childFeature.setGeometry(QgsGeometry.fromPolylineXY(points))
            geom = points[0]
        elif self.draw_layer_type == "Polygon":
            childFeature.setGeometry(QgsGeometry.fromPolygonXY([points]))
            geom = points[0]
        parentlayer = getlayer_byname(self.parentlayer_name)
        #vindt dichtsbijzijnde parentfeature om aan te koppelen
        dummy, parentId = nearest_neighbor(self.iface, parentlayer, geom)
        #foutafhandeling ivm als er geen parentfeature is gevonden binnen het kaartvenster in QGIS
        if parentId is None:
            QMessageBox.information(None, "Oeps:", "Geen bouwlaag gevonden om aan te koppelen.")
        else:
            #wegschrijven van de nieuwe feature, inclusief foreign_key en rotatie
            buttonCheck = self.get_attributes(parentId, childFeature, snapAngle)
            if buttonCheck != 'Cancel':
                write_layer(self.draw_layer, childFeature)
        #opnieuw activeren tekentool, zodat er meerdere pictogrammen achter elkaar kunnen worden geplaatst
        self.run_tekenen('dummy', self.draw_layer.name(), self.identifier)
        #self.activatePan()

    def get_attributes(self, foreignKey, childFeature, snapAngle):
        """get the aatributes that are obligated"""
        input_id = self.identifier
        #haal de vraag voor de inputdialog vanuit de config file
        question = get_draw_layer_attr(self.draw_layer.name(), "question", self.read_config)
        #is de label verplicht of niet?
        label_req = get_draw_layer_attr(self.draw_layer.name(), "label_required", self.read_config)
        input_label = user_input_label(label_req, question)
        #attribuut naam ophalen van de foreignkey
        if input_label != 'Cancel':
            input_fk = foreignKey
            attr_id = get_draw_layer_attr(self.draw_layer.name(), "identifier", self.read_config)
            attr_label = get_draw_layer_attr(self.draw_layer.name(), "input_label", self.read_config)
            attr_fk = get_draw_layer_attr(self.draw_layer.name(), "foreign_key", self.read_config)
            fields = self.draw_layer.fields()
            #initialiseer de childFeature
            childFeature.initAttributes(fields.count())
            childFeature.setFields(fields)
            #invullen van label, foreignkey en rotatie op de juiste plaats in childFeature
            if attr_id != '':
                if str(input_id).isdigit():
                    childFeature[attr_id] = int(input_id)
                else:
                    childFeature[attr_id] = input_id
            if attr_label != '':
                childFeature[attr_label] = input_label
            if attr_fk != '':
                childFeature[attr_fk] = input_fk
            if snapAngle is not None:
                childFeature['rotatie'] = snapAngle
            return childFeature
        else:
            return 'Cancel'

    def close_teken_show_object(self):
        """destroy and close self"""
        try:
            self.move.clicked.disconnect()
            self.identify.clicked.disconnect()
            self.select.clicked.disconnect()
            self.delete_f.clicked.disconnect()
            self.pan.clicked.disconnect()
            self.terug.clicked.disconnect()
        except: # pylint: disable=bare-except
            pass
        try:
            del self.stackwidget
        except: # pylint: disable=bare-except
            pass
        self.close()
        self.objectwidget.show()
        del self
