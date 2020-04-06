"""
/***************************************************************************
 oiv
                                 A QGIS plugin
 place oiv objects
                              -------------------
        begin                : 2019-08-15
        git sha              : $Format:%H$
        copyright            : (C) 2019 by Joost Deen
        email                : jdeen@safetyct.com
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

from qgis.core import QgsFeature, QgsGeometry, QgsFeatureRequest
from qgis.utils import iface

from .tools.mapTool import CaptureTool
from .tools.identifyTool import SelectTool
from .tools.snappointTool import SnapPointTool
from .tools.utils import check_layer_type, get_draw_layer_attr, getlayer_byname, write_layer, user_input_label, nearest_neighbor, read_config_file, get_actions, get_possible_snapFeatures
from .oiv_stackwidget import oivStackWidget

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'oiv_tekenen_widget.ui'))

class oivTekenWidget(QDockWidget, FORM_CLASS):
    """Organize all draw features on the map"""

    configFileBouwlaag = None
    iface = None
    canvas = None
    tekenTool = None
    identifier = None
    parentLayerName = None
    drawLayerType = None
    drawLayer = None
    editableLayerNames = []
    objectwidget = None
    drawTool = None
    moveTool = None
    selectTool = None
    #id van pictogram
    snapPicto = ['1', '10', '32', '47', '148', '149', '150', '151', '152',\
                 '1011', 'Algemeen', 'Voorzichtig', 'Waarschuwing', 'Gevaar'] 
    moveLayerNames = []
    snapLayerNames = ["BAG panden", "Bouwlagen", \
                        "Bouwkundige veiligheidsvoorzieningen", "Ruimten"]

    def __init__(self, parent=None):
        """Constructor."""
        super(oivTekenWidget, self).__init__(parent)
        self.setupUi(self)
        self.iface = iface
        self.stackwidget = oivStackWidget()
        self.initUI()

    def initUI(self):
        """intitiate the UI elemets on the widget"""
        self.set_lengte_oppervlakte_visibility(False, False, False)
        #connect buttons to the action
        self.move.clicked.connect(self.run_move_point)
        self.identify.clicked.connect(self.run_edit_tool)
        self.select.clicked.connect(self.run_select_tool)
        self.delete_f.clicked.connect(self.run_delete_tool)
        self.pan.clicked.connect(self.activatePan)
        self.terug.clicked.connect(self.close_teken_show_object)
        self.configFileBouwlaag = read_config_file("/config_files/csv/config_bouwlaag.csv", None)        
        actionList, self.editableLayerNames, self.moveLayerNames = get_actions(self.configFileBouwlaag)
        self.initActions(actionList)

    def initActions(self, actionList):
        """connect all the buttons to the action"""
        for lyr in actionList:
            for action in lyr:
                runLayerName = action[0]
                buttonNr = action[1]
                buttonName = str(action[2].lower())
                strButton = self.findChild(QPushButton, buttonName)

                if strButton:
                    #set tooltip per buttonn
                    strButton.setToolTip(buttonName)
                    #geef met de signal ook mee welke knop er is geklikt -> nr
                    strButton.clicked.connect(lambda dummy='dummyvar', rlayer=runLayerName, who=buttonNr: self.run_tekenen(dummy, rlayer, who))

    def activatePan(self):
        """trigger pan function to loose other functions"""
        self.iface.actionPan().trigger()

    def run_edit_tool(self):
        """activate the edit feature tool"""
        try:
            self.selectTool.geomSelected.disconnect()
        except: # pylint: disable=bare-except
            pass
        self.selectTool.configFileBouwlaag = self.configFileBouwlaag
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
        self.selectTool.configFileBouwlaag = self.configFileBouwlaag
        self.canvas.setMapTool(self.selectTool)
        self.selectTool.geomSelected.connect(self.delete_feature)

    def delete_feature(self, ilayer, ifeature):
        """controleer of het een feature betreft binnenn de lijst editableLayers"""
        if ilayer.name() in self.editableLayerNames:
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

    def set_lengte_oppervlakte_visibility(self, lengteTF, straalTF, oppTF):
        self.lengte_label.setVisible(lengteTF)
        self.lengte.setVisible(lengteTF)
        self.straal.setVisible(straalTF)
        self.straal_label.setVisible(straalTF)
        self.oppervlakte_label.setVisible(oppTF)
        self.oppervlakte.setVisible(oppTF)

    def run_tekenen(self, dummy, run_layer, feature_id):
        """activate the right draw action"""
        #welke pictogram is aangeklikt en wat is de bijbehorende tekenlaag
        self.identifier = feature_id
        self.drawLayer = getlayer_byname(run_layer)
        self.drawLayerType = check_layer_type(self.drawLayer)
        self.parentLayerName = get_draw_layer_attr(run_layer, "parent_layer", self.configFileBouwlaag)
        objectId = self.pand_id.text()
        #aan welke lagen kan worden gesnapt?
        possibleSnapFeatures = get_possible_snapFeatures(self.snapLayerNames, objectId)

        if self.drawLayerType == "Point":
            self.tekenTool.snapPt = None
            self.tekenTool.snapping = False
            self.tekenTool.startRotate = False
            self.tekenTool.possibleSnapFeatures = possibleSnapFeatures
            if self.identifier in self.snapPicto:
                self.tekenTool.snapping = True
            self.tekenTool.layer = self.drawLayer
            self.canvas.setMapTool(self.tekenTool)
            self.set_lengte_oppervlakte_visibility(False, False, False)
            self.tekenTool.onGeometryAdded = self.place_feature
        else:
            if self.drawLayerType == "Line":
                self.drawTool.captureMode = 1
            else:
                self.drawTool.captureMode = 2
            self.drawTool.layer = self.drawLayer
            self.drawTool.possibleSnapFeatures = possibleSnapFeatures
            self.drawTool.canvas = self.canvas
            self.drawTool.onGeometryAdded = self.place_feature
            self.canvas.setMapTool(self.drawTool)
            self.set_lengte_oppervlakte_visibility(True, True, False)
            self.drawTool.parent = self

    def place_feature(self, points, snapAngle):
        """Save and place feature on the canvas"""
        childFeature = QgsFeature()
        self.iface.setActiveLayer(self.drawLayer)
        #converteer lijst van punten naar QgsGeometry, afhankelijk van soort geometrie
        if self.drawLayerType == "Point":
            childFeature.setGeometry(QgsGeometry.fromPointXY(points))
            geom = points
        elif self.drawLayerType == "Line":
            childFeature.setGeometry(QgsGeometry.fromPolylineXY(points))
            geom = points[0]
        elif self.drawLayerType == "Polygon":
            childFeature.setGeometry(QgsGeometry.fromPolygonXY([points]))
            geom = points[0]
        parentlayer = getlayer_byname(self.parentLayerName)
        #vindt dichtsbijzijnde parentfeature om aan te koppelen
        dummy, parentId = nearest_neighbor(self.iface, parentlayer, geom)
        #foutafhandeling ivm als er geen parentfeature is gevonden binnen het kaartvenster in QGIS
        if parentId is None:
            QMessageBox.information(None, "Oeps:", "Geen bouwlaag gevonden om aan te koppelen.")
        else:
            #wegschrijven van de nieuwe feature, inclusief foreign_key en rotatie
            buttonCheck = self.get_attributes(parentId, childFeature, snapAngle)
            if buttonCheck != 'Cancel':
                write_layer(self.drawLayer, childFeature)
        #opnieuw activeren tekentool, zodat er meerdere pictogrammen achter elkaar kunnen worden geplaatst
        self.run_tekenen('dummy', self.drawLayer.name(), self.identifier)

    def get_attributes(self, foreignKey, childFeature, snapAngle):
        """get the aatributes that are obligated"""
        input_id = self.identifier
        #haal de vraag voor de inputdialog vanuit de config file
        question = get_draw_layer_attr(self.drawLayer.name(), "question", self.configFileBouwlaag)
        #is de label verplicht of niet?
        label_req = get_draw_layer_attr(self.drawLayer.name(), "label_required", self.configFileBouwlaag)
        input_label = user_input_label(label_req, question)
        #attribuut naam ophalen van de foreignkey
        if input_label != 'Cancel':
            input_fk = foreignKey
            attr_id = get_draw_layer_attr(self.drawLayer.name(), "identifier", self.configFileBouwlaag)
            attr_label = get_draw_layer_attr(self.drawLayer.name(), "input_label", self.configFileBouwlaag)
            attr_fk = get_draw_layer_attr(self.drawLayer.name(), "foreign_key", self.configFileBouwlaag)
            fields = self.drawLayer.fields()
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
        for widget in self.children():
            if isinstance(widget, QPushButton):
                try:
                    widget.clicked.disconnect()
                except: # pylint: disable=bare-except
                    pass
        self.close()
        self.objectwidget.show()
        del self
