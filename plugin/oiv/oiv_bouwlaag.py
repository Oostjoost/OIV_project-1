# -*- coding: utf-8 -*-
"""
/***************************************************************************
 oivTekenWidget
                                 A QGIS plugin
 place oiv objects
                             -------------------
        begin                : 2017-11-14
        git sha              : $Format:%H$
        copyright            : (C) 2017 by Joost Deen
        email                : jdeen@vrnhn.nl
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
from qgis.PyQt import uic
from qgis.PyQt.QtWidgets import QDockWidget, QCheckBox, QMessageBox
from qgis.utils import iface
from qgis.gui import *
from qgis.core import *
from .tools.identifyTool import SelectTool
from .tools.utils import *

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'oiv_bouwlaag_widget.ui'))

class oivBouwlaagWidget(QDockWidget, FORM_CLASS):

    canvas      = None
    iface       = None
    layer       = None
    read_config = None
    selectTool  = None
    polygonTool = None
    objectId    = None
    objectwidget   = None
    bouwlaagList   = []
    snapLayerNames = ["Bouwlagen", "BAG panden", "Bouwkundige veiligheidsvoorzieningen", "Ruimten"]

    #initialize dockwidget and connect slots and signals
    def __init__(self, parent=None):
        super(oivBouwlaagWidget, self).__init__(parent)
        self.setupUi(self)
        self.iface = iface
        self.bouwlaag_bag.clicked.connect(self.run_bag_overnemen)
        self.bouwlaag_tekenen.clicked.connect(self.run_bouwlaag_tekenen)
        self.bouwlaag_overnemen.clicked.connect(self.run_bouwlaag_overnemen)
        self.terug.clicked.connect(self.close_bouwlaag)
        self.copy.clicked.connect(self.run_select_bouwlaag) 
        self.label1.setVisible(False)
        self.label2.setVisible(False)
        self.label3.setVisible(False)
        self.lengte_label.setVisible(False)
        self.lengte.setVisible(False)
        self.oppervlakte_label.setVisible(False)
        self.oppervlakte.setVisible(False)
        self.bouwlaag_max.setVisible(False)
        for var in vars(self):
            typeVar = type(vars(self)[var])
            if typeVar == QCheckBox:
                vars(self)[var].setVisible(False)
        self.bouwlaag.setVisible(False)
        self.copy.setVisible(False)

    #copy polygon of bag feature
    def run_bag_overnemen(self):
        #connect selecttool and set the maptool
        layerName = "BAG panden"
        ilayer = getlayer_byname(layerName)
        request = QgsFeatureRequest().setFilterExpression( '"identificatie" = ' + str(self.objectId))
        ifeature = next(ilayer.getFeatures(request))
        self.copy_bag_bouwlaag(ilayer, ifeature)
    
    #copy floor from another floor
    def run_bouwlaag_overnemen(self):
        #make buttons and labels visible to the user
        self.label1.setVisible(True)
        self.label2.setVisible(True)
        self.label3.setVisible(True)
        self.bouwlaag.setVisible(True)
        for var in vars(self):
            typeVar = type(vars(self)[var])
            if typeVar == QCheckBox:
                vars(self)[var].setVisible(True)
        #append combobox with unique existing floors
        self.bouwlagen_to_combobox()
        self.copy.setVisible(True)
        #connect signal to slot
        self.bouwlaag.currentIndexChanged.connect(self.set_layer_subset_bouwlaag)
        self.selectTool.geomSelected.connect(self.copy_bag_bouwlaag)        
    
    #draw a floor with the basic functionality of QGIS
    def run_bouwlaag_tekenen(self):
        snapLayer = []
        for name in self.snapLayerNames:
            lyr = getlayer_byname(name)
            snapLayer.append(lyr)
        self.draw_layer = getlayer_byname('Bouwlagen')
        self.polygonTool.layer = self.draw_layer
        self.polygonTool.snapLayer = snapLayer
        self.polygonTool.canvas = self.canvas
        self.polygonTool.onGeometryAdded = self.draw_feature
        self.polygonTool.captureMode = 2
        self.canvas.setMapTool(self.polygonTool)
        self.lengte_label.setVisible(True)
        self.lengte.setVisible(True)
        self.oppervlakte_label.setVisible(True)
        self.oppervlakte.setVisible(True)
        self.polygonTool.parent = self

    def run_select_bouwlaag(self):
        self.canvas.setMapTool(self.selectTool)
    
    #set layers substring which are a childlayer of "bouwlagen"
    def set_layer_subset_bouwlaag(self):
        comboboxText = str(self.bouwlaag.currentText())
        if comboboxText != "":
            sub_string = "bouwlaag = " + str(self.bouwlaag.currentText())
            set_layer_substring(self.read_config, sub_string)            

    def copy_layers(self, parentID, newID , layer, bouwlaag):
        # select the features
        fields = layer.fields()
        newFeature = QgsFeature()        
        newFeature.initAttributes(fields.count())
        newFeature.setFields(fields)
        attr_id = get_draw_layer_attr(layer.name(), "identifier", self.read_config)
        attr_fk = get_draw_layer_attr(layer.name(), "foreign_key", self.read_config)
        attr_label = get_draw_layer_attr(layer.name(), "input_label", self.read_config)
        attr_rotatie = get_draw_layer_attr(layer.name(), "rotatie", self.read_config)
        #get features by bouwlaag ID
        request = attr_fk + '=' + str(parentID)
        it = layer.getFeatures(QgsFeatureRequest().setFilterExpression (request))        
        for feat in it:
            newFeature.setGeometry(feat.geometry()) 
            if attr_id != '':
                if str(feat[attr_id]).isdigit():
                    newFeature[attr_id] = int(feat[attr_id])
                else:
                    newFeature[attr_id] = feat[attr_id]            
            if attr_label != '':
                newFeature[attr_label] = feat[attr_label]
            if attr_rotatie != '':
                newFeature[attr_rotatie] = feat[attr_rotatie]
            newFeature[attr_fk] = int(newID)
            newFeature["bouwlaag"] = bouwlaag
            write_layer(layer, newFeature)
            
    def copy_selected_layers(self, ifeature, newFeatureId, bouwlaag):
        bouwlaagID = ifeature["id"]
        for var in vars(self):
            typeVar = type(vars(self)[var])
            if typeVar == QCheckBox:
                if vars(self)[var].isChecked():
                    copyLayer = getlayer_byname(vars(self)[var].text())
                    self.copy_layers(bouwlaagID, newFeatureId, copyLayer, bouwlaag) 

    def draw_feature(self, points, snapAngle):
        minBouwlaag = int(self.bouwlaag_min.text())
        maxBouwlaag = int(self.bouwlaag_max.text())
        childFeature = QgsFeature()
        layerName = 'Bouwlagen'
        layer = getlayer_byname(layerName)
        question  = get_draw_layer_attr(layerName, "question", self.read_config)
        label_req = get_draw_layer_attr(layerName, "label_required", self.read_config)        
        #get bouwdeel from user
        input_label = user_input_label(label_req, question)
        attr_fk    = get_draw_layer_attr(layerName, "foreign_key", self.read_config)
        attr_label = get_draw_layer_attr(layerName, "input_label", self.read_config)
        self.iface.setActiveLayer(self.draw_layer)
        #construct QgsFeature to save
        for i in range(minBouwlaag, maxBouwlaag + 1):
            if i != 0:
                childFeature.setGeometry(QgsGeometry.fromPolygonXY([points]))
                fields = layer.fields()        
                childFeature.initAttributes(fields.count())
                childFeature.setFields(fields)
                childFeature[attr_fk] = self.objectId
                childFeature[attr_label] = input_label
                childFeature["bouwlaag"] = i
                newFeatureId = write_layer(layer, childFeature)
                #block the signals of changing the comboBox to add the new floor
                self.bouwlaag.blockSignals(True)
                self.bouwlaag.clear()        
                if i not in self.bouwlaagList:
                    self.bouwlaagList.append(i)
        self.bouwlaagList.sort()
        self.bouwlagen_to_combobox()           
        self.bouwlaag.blockSignals(False)
        self.iface.actionPan().trigger()
        #set all layers substring to the right floor
        sub_string = "bouwlaag = " + str(minBouwlaag)
        set_layer_substring(self.read_config, sub_string)
        if maxBouwlaag != minBouwlaag:
            QMessageBox.information(None, "Gereed!", "Alle bouwlagen zijn succesvol aangemaakt!")
            
    def copy_bag_bouwlaag(self, ilayer, ifeature):
        if ilayer.name() == 'Bouwlagen' or ilayer.name() == 'BAG Panden':
            childFeature = QgsFeature()
            layerName = 'Bouwlagen'
            #get active floor from dockwidget
            minBouwlaag = int(self.bouwlaag_min.text())
            maxBouwlaag = int(self.bouwlaag_max.text())
            layer = getlayer_byname(layerName)
            #get necessary attributes from config file
            question = get_draw_layer_attr(layerName, "question", self.read_config)
            label_req = get_draw_layer_attr(layerName, "label_required", self.read_config)        
            #get bouwdeel from user
            input_label = user_input_label(label_req, question)
            attr_fk = get_draw_layer_attr(layerName, "foreign_key", self.read_config)
            attr_label = get_draw_layer_attr(layerName, "input_label", self.read_config)
            self.iface.setActiveLayer(layer)
            #construct QgsFeature to save
            for i in range(minBouwlaag, maxBouwlaag + 1):
                if i != 0:
                    childFeature.setGeometry(ifeature.geometry())
                    fields = layer.fields()        
                    childFeature.initAttributes(fields.count())
                    childFeature.setFields(fields)
                    childFeature[attr_fk] = self.objectId
                    childFeature[attr_label] = input_label
                    childFeature["bouwlaag"] = i
                    newFeatureId = write_layer(layer, childFeature)
                    #copy also the selected layers
                    if ilayer.name() == "Bouwlagen":
                        self.copy_selected_layers(ifeature, newFeatureId, i)  
                    #block the signals of changing the comboBox to add the new floor
                    self.bouwlaag.blockSignals(True)
                    self.bouwlaag.clear()        
                    if i not in self.bouwlaagList:
                        self.bouwlaagList.append(i)
            self.bouwlaagList.sort()
            self.bouwlagen_to_combobox()           
            self.bouwlaag.blockSignals(False)
            self.iface.actionPan().trigger()
            #set all layers substring to the right floor
            sub_string = "bouwlaag = " + str(minBouwlaag)
            set_layer_substring(self.read_config, sub_string)
            try:
                self.selectTool.geomSelected.disconnect()
            except:
                None
            if maxBouwlaag >= minBouwlaag:
                QMessageBox.information(None, "Gereed!", "Alle bouwlagen zijn succesvol aangemaakt!")
        else:
            QMessageBox.information(None, "Oeps:", "U heeft geen bouwlaag aangeklikt, selecteer opnieuw.")
            try:
                self.selectTool.geomSelected.disconnect()
            except:
                None
            self.selectTool.geomSelected.connect(self.copy_bag_bouwlaag)
            
    #add existing floors to the comboBox of the "bouwlaagdockwidget"
    def bouwlagen_to_combobox(self):
        self.bouwlaag.blockSignals(True)    
        self.bouwlaag.clear()
        for i in range(len(self.bouwlaagList) + 1):
            if i == 0:
                self.bouwlaag.addItem("")
            else:
                self.bouwlaag.addItem(str(self.bouwlaagList[i - 1]))
        self.bouwlaag.blockSignals(False)
        index = self.bouwlaag.findText(str(self.bouwlaag_min.text()), QtCore.Qt.MatchFixedString)
        if index >= 0:
            self.bouwlaag.setCurrentIndex(index)
        else:
            self.bouwlaag.setCurrentIndex(0)
        
    def close_bouwlaag(self):
        self.label1.setVisible(False)
        self.label2.setVisible(False)
        self.label3.setVisible(False)
        self.bouwlaag.setVisible(False)
        self.copy.setVisible(False)
        for var in vars(self):
            typeVar = type(vars(self)[var])
            if typeVar == QCheckBox:
                vars(self)[var].setVisible(False)
        self.objectwidget.sortedList = self.bouwlaagList
        self.objectwidget.bouwlagen_to_combobox(self.objectId, int(self.bouwlaag_min.text()))
        self.objectwidget.show()
        self.close()
        try:
            del self.objectwidget
        except:
            None
        del self