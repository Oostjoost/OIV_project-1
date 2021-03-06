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
from .tools.query_bag import *
from .oiv_bouwlaag import oivBouwlaagWidget
from .oiv_stackwidget import oivStackWidget
from .oiv_tekenen import oivTekenWidget
from .oiv_import_file import oivImportFileWidget

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'oiv_objectgegevens_widget.ui'))

class oivObjectWidget(QDockWidget, FORM_CLASS):

    read_config     = None
    iface           = None
    canvas          = None
    basewidget      = None
    selectTool      = None
    tekenTool       = None
    sortedList      = []
    attributeform   = None
    objectFeature   = None
    lineTool        = None
    polygonTool     = None
    moveTool        = None
    identifyTool    = None
    min_bouwlaag    = 0
    max_bouwlaag    = 0

    def __init__(self, parent=None):
        super(oivObjectWidget, self).__init__(parent)
        self.setupUi(self)
        self.iface = iface
        self.bouwlaagwidget = oivBouwlaagWidget()
        self.tekenwidget = oivTekenWidget()
        self.importwidget = oivImportFileWidget()
        self.stackwidget = oivStackWidget()        
        self.bouwlaag_toevoegen.clicked.connect(self.run_bouwlaag)
        self.tekenen.clicked.connect(self.run_tekenen)
        self.comboBox.currentIndexChanged.connect(self.set_layer_subset_object)
        self.bouwlaag_bewerken.clicked.connect(self.run_bouwlaag_bewerken)
        self.import_2.clicked.connect(self.run_import)
        self.terug.clicked.connect(self.close_object_show_base)
        self.terugmelden.clicked.connect(self.openBagviewer)
        self.delete_f.clicked.connect(self.run_delete)

    #edit attribute form of floor feature
    def run_edit_bouwlagen(self, ilayer, ifeature):
        self.iface.addDockWidget(Qt.RightDockWidgetArea, self.stackwidget)
        self.stackwidget.update()
        self.stackwidget.parentWidget = self
        self.stackwidget.open_feature_form(ilayer, ifeature)
        self.close()
        self.stackwidget.show()

    def existing_object(self, ifeature, objectId):
        #Get the related BAG attributes from BAG API
        ilayer = getlayer_byname('BAG panden')
        foreignKey = 'identificatie'
        request = QgsFeatureRequest().setFilterExpression(foreignKey + " = '" + str(objectId) + "'")
        tempFeature = next(ilayer.getFeatures(request))
        bagGebruiksdoel = str(tempFeature['gebruiksdoel'])
        if self.adres_1.text() == "":
            bag_adres1, bag_adres2, bag_gebruiksdoel = ask_bag_adress(objectId, bagGebruiksdoel)
            self.adres_1.setText(bag_adres1)
            self.adres_2.setText(bag_adres2)
            self.gebruiksdoel.setText(bag_gebruiksdoel)
        self.pand_id.setText(str(objectId))
        #set actieve bouwlaag to 1 and fill combobox
        self.bouwlagen_to_combobox(objectId, 1)

    #fill combobox with existing floors
    def bouwlagen_to_combobox(self, objectId, actieveBouwlaag):
        run_layer = 'Bouwlagen'
        qstring = 'foreign_key'
        tempLayer = getlayer_byname(run_layer)
        objectId = self.pand_id.text()
        foreignKey = get_draw_layer_attr(run_layer, qstring, self.read_config)
        tempLayer.setSubsetString('')
        #request all existing floors of object feature
        request = QgsFeatureRequest().setFilterExpression(foreignKey + " = '" + str(objectId) + "'")
        tempFeatureIt = tempLayer.getFeatures(request)
        #create unique list of existing floors and sort it from small to big
        bouwlaagList = [it["bouwlaag"] for it in tempFeatureIt]
        self.sortedList = create_unique_sorted_list(bouwlaagList)
        #block signal of combobox to add existing floors
        self.comboBox.blockSignals(True)
        self.comboBox.clear()
        for i in range(len(self.sortedList)):
            self.comboBox.addItem(str(self.sortedList[i]))
        #if there are existing floors "tekenen" can be enabled
        if len(self.sortedList) == 0:
            self.tekenen.setEnabled(False)
        else:
            self.tekenen.setEnabled(True)
        self.comboBox.blockSignals(False)
        #set substring of childlayers
        sub_string = "bouwlaag = " + str(actieveBouwlaag)
        set_layer_substring(self.read_config, sub_string)
        index = self.comboBox.findText(str(actieveBouwlaag), Qt.MatchFixedString)
        if index >= 0:
            self.comboBox.setCurrentIndex(index)
        self.iface.actionPan().trigger()        

    #if index of combobox has changed set substring of childlayers
    def set_layer_subset_object(self):
        sub_string = "bouwlaag = " + str(self.comboBox.currentText())
        set_layer_substring(self.read_config, sub_string) 

    def close_object_show_base(self):
        sub_string = "bouwlaag = 1"
        set_layer_substring(self.read_config, sub_string)
        try:
            del self.tekenwidget
        except:
            None
        try:
            del self.stackwidget
        except:
            None
        try:
            del self.bouwlaagwidget
        except:
            None
        self.close()
        self.basewidget.show()
        self.iface.actionPan().trigger()
        del self        

    #select bouwlaag on canvas to edit the atrribute form
    def run_bouwlaag_bewerken(self):
        run_layer = "Bouwlagen"
        qstring = 'foreign_key'
        ilayer = getlayer_byname(run_layer)
        objectId = self.pand_id.text()
        foreignKey = get_draw_layer_attr(run_layer, qstring, self.read_config)
        request = QgsFeatureRequest().setFilterExpression(foreignKey + " = '" + str(objectId) + "'")
        ifeature = next(ilayer.getFeatures(request))
        self.run_edit_bouwlagen(ilayer, ifeature)

    #add new floor    
    def run_bouwlaag(self):
        while True:
            bouwlaag, bouwlaagMax, ok = BouwlaagDialog.getBouwlagen()
            if (bouwlaag != 0 and bouwlaagMax >= bouwlaag and ok == True):
                self.close()
                self.iface.addDockWidget(Qt.RightDockWidgetArea, self.bouwlaagwidget)
                self.bouwlaagwidget.canvas = self.canvas
                self.bouwlaagwidget.bouwlaagList = self.sortedList
                self.bouwlaagwidget.read_config = self.read_config
                self.bouwlaagwidget.objectId = self.pand_id.text()
                self.bouwlaagwidget.objectwidget = self
                self.bouwlaagwidget.selectTool = self.selectTool
                self.bouwlaagwidget.identifyTool = self.identifyTool
                self.bouwlaagwidget.polygonTool = self.polygonTool
                self.bouwlaagwidget.teken_bouwlaag.setText(str(bouwlaag) + ' t/m ' + str(bouwlaagMax))
                self.bouwlaagwidget.bouwlaag_min.setText(str(bouwlaag))
                self.bouwlaagwidget.bouwlaag_max.setText(str(bouwlaagMax))
                self.bouwlaagwidget.teken_bouwlaag.setEnabled(False)
                sub_string = "bouwlaag = " + str(bouwlaag)
                set_layer_substring(self.read_config, sub_string)
                self.bouwlaagwidget.show()
                break
            elif bouwlaagMax < bouwlaag:
                QMessageBox.information(None, "Oeps:", "De hoogste bouwlaag kan niet lager zijn als de laagste, vul opnieuw in!.")
            elif ok == False:
                break
            else:    
                True

    #init teken widget
    def run_tekenen(self):
        self.tekenwidget.canvas = self.canvas
        self.tekenwidget.read_config = self.read_config
        self.tekenwidget.tekenTool = self.tekenTool
        self.tekenwidget.lineTool = self.lineTool
        self.tekenwidget.polygonTool = self.polygonTool
        self.tekenwidget.moveTool = self.moveTool
        self.tekenwidget.selectTool = self.selectTool        
        self.tekenwidget.objectwidget = self
        sub_string = "bouwlaag = " + str(self.comboBox.currentText())
        set_layer_substring(self.read_config, sub_string)        
        self.tekenwidget.bouwlaag.setText(str(self.comboBox.currentText()))
        self.iface.addDockWidget(Qt.RightDockWidgetArea, self.tekenwidget) 
        self.close()
        self.tekenwidget.show()
        self.tekenwidget.connect_buttons(self.read_config)     

    #open url based on BAG pand_id, i.v.m. terugmelden    
    def openBagviewer(self):
        url = 'https://bagviewer.kadaster.nl/lvbag/bag-viewer/#?searchQuery=' + str(self.pand_id.text())
        webbrowser.open(url)

    def run_delete(self):
        layerName = "Bouwlagen"
        ilayer = getlayer_byname(layerName)
        self.iface.setActiveLayer(ilayer)
        objectId = self.pand_id.text()
        request = QgsFeatureRequest().setFilterExpression( '"pand_id" = ' + str(objectId)).setFlags(QgsFeatureRequest.NoGeometry).setSubsetOfAttributes([])
        ifeature = next(ilayer.getFeatures(request))
        ilayer.startEditing()
        ilayer.selectByIds([ifeature.id()])
        reply = QMessageBox.question(self.iface.mainWindow(), 'Continue?', 
             "Weet u zeker dat u de geselecteerde feature wilt weggooien?", QMessageBox.Yes, QMessageBox.No)
        if reply == QMessageBox.No:
            #als "nee" deselecteer alle geselecteerde features
            ilayer.setSelectedFeatures([])
        elif reply == QMessageBox.Yes:
            #als "ja" -> verwijder de feature op basis van het unieke feature id
            ilayer.deleteFeature(ifeature.id())
            ilayer.commitChanges()
            reply = QMessageBox.information(self.iface.mainWindow(), 'Succesvol!', "Het object is succesvol verwijderd.")
            refresh_layers(self.iface)
            #set actieve bouwlaag to 1 and fill combobox
            self.bouwlagen_to_combobox(ifeature.id(), 1)

    def run_import(self):
        self.importwidget.parentWidget = self
        self.importwidget.object_id.setText(self.pand_id.text())
        self.importwidget.bouwlaag.setText(self.comboBox.currentText())
        self.importwidget.selectTool = self.selectTool
        self.importwidget.canvas = self.canvas
        self.importwidget.read_config = self.read_config
        self.iface.addDockWidget(Qt.RightDockWidgetArea, self.importwidget) 
        self.close()
        self.importwidget.show()

class BouwlaagDialog(QDialog):
    def __init__(self, parent = None):
        super(BouwlaagDialog, self).__init__(parent)
        max_bouwlaag = 30
        min_bouwlaag = -10
        self.setWindowTitle("Bouwlagen toevoegen")
        qlayout = QVBoxLayout(self)
        self.qlineA = QLabel(self)
        self.qlineB = QLabel(self)
        self.qlineC = QLabel(self)
        self.qComboA = QComboBox(self)
        self.qComboB = QComboBox(self)
        self.qlineA.setText("U kunt meerdere bouwlagenlagen in 1x creeren, door van en t/m in te vullen!")
        self.qlineB.setText("Van:")
        self.qlineC.setText("Tot en met:")
        for i in range(max_bouwlaag - min_bouwlaag + 1):
            if max_bouwlaag - i != 0:
                self.qComboA.addItem(str(max_bouwlaag - i))
                self.qComboB.addItem(str(max_bouwlaag - i))
                if max_bouwlaag - i == 1:
                    init_index = i
        self.qComboA.setCurrentIndex(init_index) 
        self.qComboB.setCurrentIndex(init_index)  
        self.qComboA.setFixedWidth(100)
        self.qComboA.setMaxVisibleItems(30)
        self.qComboB.setFixedWidth(100)
        self.qComboB.setMaxVisibleItems(30) 
        self.qComboA.currentIndexChanged.connect(self.set_comboboxB)
        qlayout.addWidget(self.qlineA)
        qlayout.addWidget(self.qlineB)
        qlayout.addWidget(self.qComboA)
        qlayout.addWidget(self.qlineC)
        qlayout.addWidget(self.qComboB)
        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel,
            Qt.Horizontal, self)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        qlayout.addWidget(buttons)

    def set_comboboxB(self):
        ind = self.qComboA.currentIndex()
        self.qComboB.setCurrentIndex(ind)

    @staticmethod
    def getBouwlagen(parent = None):
        dialog = BouwlaagDialog(parent)
        result = dialog.exec_()
        return (int(dialog.qComboA.currentText()), int(dialog.qComboB.currentText()), result == QDialog.Accepted)