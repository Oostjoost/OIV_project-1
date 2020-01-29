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
from . import resources
import webbrowser
from qgis.PyQt import uic
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtWidgets import QDialog, QDockWidget, QVBoxLayout, QLabel, QMessageBox, QComboBox, QDialogButtonBox
from qgis.gui import *
from qgis.core import *
from qgis.utils import iface
from .tools.utils import *
from .tools.identifyTool import IdentifyGeometryTool
from .oiv_stackwidget import oivStackWidget
from .tools.mapTool import CaptureTool
from .tools.identifyTool import SelectTool
from .oiv_object_tekenen import oivObjectTekenWidget

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'oiv_repressief_object_widget.ui'))

class oivRepressiefObjectWidget(QDockWidget, FORM_CLASS):

    read_config     = None
    iface           = None
    canvas          = None
    basewidget      = None
    selectTool      = None
    tekenTool       = None
    attributeform   = None
    objectFeature   = None
    identifyTool    = None
    draw_layer      = None
    identifier      = None
    parentlayer_name= None
    draw_layer_type = None
    lineTool        = None
    polygonTool     = None
    moveTool        = None
    snapLayerNames  = ["Bouwlagen", "BAG panden", "Object terrein"]

    def __init__(self, parent=None):
        super(oivRepressiefObjectWidget, self).__init__(parent)
        self.setupUi(self)
        self.iface = iface
        self.object_id.setVisible(False)
        self.stackwidget = oivStackWidget()        
        self.terug.clicked.connect(self.close_repressief_object_show_base)
        self.objectgegevens.clicked.connect(self.run_objectgegevens_bewerken)
        self.terugmelden.clicked.connect(self.openBagviewer)
        self.delete_f.clicked.connect(self.run_delete)
        self.object_tekenen.clicked.connect(self.object_terrein_tekenen)
        self.object_symbolen.clicked.connect(self.run_object_symbolen_tekenen)
        self.lengte_label.setVisible(False)
        self.lengte.setVisible(False)
        self.oppervlakte_label.setVisible(False)
        self.oppervlakte.setVisible(False)   

    def existing_object(self, ifeature, objectId):
        #Get the related BAG attributes from BAG API
        #self.formelenaam.setText(ifeature["formelenaam"]) 
        objectId = str(ifeature["id"])
        self.object_id.setText(str(objectId))
        self.formelenaam.setText(ifeature["formelenaam"])
        request = QgsFeatureRequest().setFilterExpression( '"id" = ' + str(objectId))
        tempLayer = self.draw_layer
        self.tFeature = next(tempLayer.getFeatures(request))

    def close_repressief_object_show_base(self):
        self.delete_f.clicked.disconnect()
        self.terug.clicked.disconnect()
        self.objectgegevens.clicked.disconnect()
        self.terugmelden.clicked.disconnect()
        self.object_tekenen.clicked.disconnect()
        try:
            del self.stackwidget
        except:
            None
        self.close()
        self.basewidget.show()
        del self        

    def activatePan(self):
        self.iface.actionPan().trigger()

    #select bouwlaag on canvas to edit the atrribute form
    def run_objectgegevens_bewerken(self):
        self.iface.addDockWidget(Qt.RightDockWidgetArea, self.stackwidget)
        self.stackwidget.parentWidget = self
        self.stackwidget.open_feature_form(self.draw_layer, self.tFeature)
        self.close()
        self.stackwidget.show()

    #open url based on BAG pand_id, i.v.m. terugmelden    
    def openBagviewer(self):
        e = iface.mapCanvas().extent()
        gemx = (e.xMaximum() + e.xMinimum())/2
        gemy = (e.yMaximum() + e.yMinimum())/2
        #url1 = 'https://bagviewer.kadaster.nl/lvbag/bag-viewer/#?searchQuery=' + str(self.pand_id.text())
        url2 = 'https://verbeterdekaart.kadaster.nl/#?geometry.x=' + str(gemx) + '&geometry.y=' + str(gemy) + '&zoomlevel=12'
        #webbrowser.open(url1)
        webbrowser.open(url2)

    # Read lines from input file and convert to list
    def read_config_file(self, file):
        config_list = []
        basepath = os.path.dirname(os.path.realpath(__file__))
        with open(basepath + file, 'r' ) as inp_file:
            lines = inp_file.read().splitlines()
        for line in lines:
            config_list.append(line.split(','))
        inp_file.close()
        return config_list

    def run_delete(self):
        ilayer = self.draw_layer
        self.iface.setActiveLayer(ilayer)
        objectId = self.object_id.text()
        request = QgsFeatureRequest().setFilterExpression( '"id" = ' + str(objectId))
        ifeature = next(ilayer.getFeatures(request))
        ilayer.startEditing()
        ilayer.selectByIds([ifeature.id()])
        reply = QMessageBox.question(self.iface.mainWindow(), 'Continue?', 
             "Weet u zeker dat u de geselecteerde feature wilt weggooien?", QMessageBox.Yes, QMessageBox.No)
        if reply == QMessageBox.No:
            #als "nee" deselecteer alle geselecteerde features
            ilayer.selectByIds([])
        elif reply == QMessageBox.Yes:
            #als "ja" -> verwijder de feature op basis van het unieke feature id
            ilayer.deleteFeature(ifeature.id())
            ilayer.commitChanges()
            reply = QMessageBox.information(self.iface.mainWindow(), 'Succesvol!', "Het object is succesvol verwijderd.")
        refresh_layers(self.iface)
        self.close_repressief_object_show_base()

    #open het formulier van een feature in een dockwidget, zodat de attributen kunnen worden bewerkt
    def edit_attribute(self, ilayer, ifeature):
        self.iface.addDockWidget(Qt.RightDockWidgetArea, self.stackwidget)
        self.stackwidget.parentWidget = self
        self.stackwidget.open_feature_form(ilayer, ifeature)
        self.close()
        self.stackwidget.show()
        self.selectTool.geomSelected.disconnect(self.edit_attribute)

    def object_terrein_tekenen(self):
        snapLayer = []
        self.lengte_label.setVisible(True)
        self.lengte.setVisible(True)
        self.oppervlakte_label.setVisible(True)
        self.oppervlakte.setVisible(True)
        self.polygonTool.parent = self
        for name in self.snapLayerNames:
            lyr = getlayer_byname(name)
            snapLayer.append(lyr)
        self.polygonTool.layer = self.draw_layer
        self.polygonTool.snapLayer = snapLayer
        self.polygonTool.canvas = self.canvas
        self.polygonTool.onGeometryAdded = self.place_object_terrein
        self.polygonTool.captureMode = 2
        self.canvas.setMapTool(self.polygonTool)

    def place_object_terrein(self, point, snapAngle): 
        childFeature = QgsFeature()
        parentFeature = QgsFeature()
        layer = getlayer_byname("Object terrein")
        self.iface.setActiveLayer(layer)
        objectId = int(self.object_id.text())
        iterator = self.draw_layer.getFeatures(QgsFeatureRequest().setFilterFid(objectId))
        feature = next(iterator)
        layer.dataProvider().changeGeometryValues({feature.id(): QgsGeometry.fromPolygonXY([point])})
        layer.commitChanges()
        layer.triggerRepaint()
        self.activatePan()

    def init_object_symbolen_tekenen(self):
        self.tekensymbolenwidget = oivObjectTekenWidget()        
        self.tekensymbolenwidget.read_config = self.read_config
        self.tekensymbolenwidget.canvas = self.canvas
        self.tekensymbolenwidget.selectTool = self.selectTool
        self.tekensymbolenwidget.basewidget = self.basewidget
        self.tekensymbolenwidget.tekenTool = self.tekenTool
        self.tekensymbolenwidget.lineTool = self.lineTool
        self.tekensymbolenwidget.polygonTool = self.polygonTool
        self.tekensymbolenwidget.moveTool = self.moveTool
        self.tekensymbolenwidget.identifyTool = self.identifyTool
        self.tekensymbolenwidget.repressiefobjectwidget = self
        self.tekensymbolenwidget.formelenaam.setText(self.formelenaam.text())
        self.tekensymbolenwidget.object_id.setText(self.object_id.text())

    def run_object_symbolen_tekenen(self):
        self.init_object_symbolen_tekenen()
        self.iface.addDockWidget(Qt.RightDockWidgetArea, self.tekensymbolenwidget)
        self.tekensymbolenwidget.connect_buttons(self.read_config)
        self.tekensymbolenwidget.show()
        self.close()