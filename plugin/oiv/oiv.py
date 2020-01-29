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

#compile resources: pyrcc4 -o C:\Users\oiv\.qgis2\python\plugins\oiv_imroi\resources.py C:\Users\oiv\.qgis2\python\plugins\oiv_imroi\resources.qrc
#pyrcc4 -o C:\Users\joost\.qgis2\python\plugins\oiv_imroi_v2\resources.py C:\Users\joost\.qgis2\python\plugins\oiv_imroi_v2\resources.qrc

#Import the PyQt and QGIS libraries
from qgis.PyQt.QtCore import QSettings, QTranslator, QCoreApplication, Qt
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction, QLabel, QComboBox, QMessageBox, QInputDialog
from qgis.core import *
from qgis.gui import *

#initialize Qt resources from file resources.py
from . import resources
import os

#import plugin widget and tools
from .tools.identifyTool import *
from .tools.utils import *
from .tools.mapTool import CaptureTool
from .tools.movepointTool import MovePointTool
from .tools.snappointTool import SnapPointTool
from .oiv_objectgegevens import oivObjectWidget
from .oiv_repressief_object import oivRepressiefObjectWidget
from .oiv_base_widget import oivBaseWidget
from .oiv_objectnieuw import oivObjectNieuwWidget
from .oiv_config import oivConfigWidget

class oiv:
    #initialize class attributes

    read_config_bl   = []
    read_config_obj  = []
    min_bouwlaag     = -10
    max_bouwlaag     = 30
    check_visible    = False
    draw_layer       = None
    place_feature    = None
    soort_info       = None

    # Save reference to the QGIS interface
    def __init__(self, iface):
        self.iface  = iface
        self.canvas = self.iface.mapCanvas()
        self.pandidentifyTool = IdentifyPandTool(self.canvas)
        self.identifyTool = IdentifyGeometryTool(self.canvas)
        self.pinTool = QgsMapToolEmitPoint(self.canvas)
        self.tekenTool = SnapPointTool(self.canvas)
        self.selectTool = SelectTool(self.canvas)
        self.pinLine = CaptureTool(self.canvas)        
        self.pinPolygon = CaptureTool(self.canvas)        
        self.moveTool = MovePointTool(self.canvas, self.draw_layer)
        self.read_config_bl = self.read_config_file("/config_files/csv/config_bouwlaag.csv")

    def initGui(self):
        #init actions plugin
        self.toolbar = self.iface.addToolBar("OIV Objecten")
        self.action = QAction(QIcon(":/plugins/oiv/config_files/png/oiv_plugin.png"), "OIV Objecten", self.iface.mainWindow())
        self.action.triggered.connect(self.run)
        self.toolbar.addAction(self.action)
        self.iface.addPluginToMenu('&OIV Objecten', self.action)
        self.settings = QAction(QIcon(":/plugins/oiv/config_files/png/settings.png"), "Settings", self.iface.mainWindow())
        self.settings.triggered.connect(self.run_config)
        self.iface.addPluginToMenu('&OIV Objecten', self.settings)        
        #add label to toolbar
        self.label = QLabel(self.iface.mainWindow())
        self.labelAction = self.toolbar.addWidget(self.label)
        self.label.setText("OIV 3.0.0 | Actieve bouwlaag: ")
        #init dropdown to switch floors
        self.projCombo = QComboBox(self.iface.mainWindow())       
        for i in range(self.max_bouwlaag - self.min_bouwlaag + 1):
            if self.max_bouwlaag - i != 0:
                if self.max_bouwlaag - i == 1:
                    init_index = i
                self.projCombo.addItem(str(self.max_bouwlaag - i))
        self.projComboAction = self.toolbar.addWidget(self.projCombo)
        self.projCombo.setFixedWidth(100)
        self.projCombo.setMaxVisibleItems(30)
        #set intial index to floor 1
        self.projCombo.setCurrentIndex(init_index)
        #connect to set layer subset if the index is changed
        self.projCombo.currentIndexChanged.connect(self.set_layer_subset_toolbar)
        #init projectVariable to communicate from plugin to original drawing possibilities
        project = QgsProject.instance()
        QgsExpressionContextUtils.setProjectVariable(project, 'actieve_bouwlaag', 1)

    def close_basewidget(self):
        #close plugin and re-activate toolbar combobox
        self.basewidget.close()
        self.toolbar.setEnabled(True)
        self.projCombo.setEnabled(True)
        self.check_visible = False

    # Read lines from input file and convert to list to link the signal and slots
    def read_config_file(self, file):
        config_list = []
        basepath = os.path.dirname(os.path.realpath(__file__))
        with open(basepath + file, 'r' ) as inp_file:
            lines = inp_file.read().splitlines()
        for line in lines:
            config_list.append(line.split(','))
        inp_file.close()
        return config_list

    #remove the plugin menu item and remove the widgets    
    def unload(self):
        try:
            del self.basewidget
        except:
            None
        try:
            del self.objectwidget
        except:
            None 
        try:            
            del self.objectnieuwwidget
        except:
            None 
        self.iface.removePluginMenu("&OIV Objecten", self.action)
        self.iface.removePluginMenu("&OIV Objecten", self.settings)
        self.projCombo.currentIndexChanged.disconnect()
        self.action.triggered.disconnect()
        self.settings.triggered.disconnect()
        del self.toolbar
        self.check_visible = None
        self.iface.removeToolBarIcon(self.action)
 
    def run_config(self):
        question = "Geef het wachtwoord:"
        qid = QInputDialog()
        password, ok = QInputDialog.getText(qid, "Password:", question, QLineEdit.Password,)
        if password == "01v":
            self.configwidget = oivConfigWidget()
            self.iface.addDockWidget(Qt.RightDockWidgetArea, self.configwidget)
            self.configwidget.show()
        else:
            QMessageBox.information(None, "DEBUG:", "Verkeerd password!")

    #get the identification of a pand from the user
    def run_identify_pand(self):
        self.soort_info = 'pand'
        self.canvas.setMapTool(self.pandidentifyTool)
        self.pandidentifyTool.pandIdentified.connect(self.get_identified_pand)

    def run_identify_gebouw_terrein(self):
        self.soort_info = 'gebouw_terrein'
        self.canvas.setMapTool(self.pandidentifyTool)
        self.pandidentifyTool.pandIdentified.connect(self.get_identified_gebouw_terrein)

    #Return of identified layer and feature and get related object
    def get_identified_pand(self, ilayer, ifeature):
        #the identified layer must be "bouwlagen" or "BAG panden"
        if ilayer.name() == "Bouwlagen":
            #get_draw_layer_attr -> get attribute of identified layer from the config_file: Input (layername, attributename, searchable_config_list)
            objectId = str(ifeature["pand_id"])
            #open dockwidget object and pass along the identified object and feature
            self.run_bouwlagen()
            self.objectwidget.existing_object(ifeature, objectId)
        #a new object has to be created if a BAG pand was identified objectId -> Bag identificatie nummer    
        elif ilayer.name() == "BAG panden":
            objectId = str(ifeature["identificatie"])
            #open dockwidget object and pass along the identified object and feature
            self.run_bouwlagen()
            self.objectwidget.existing_object(ifeature, objectId)    
        #if another layer is identified there is no object that can be determined, so a message is send to the user
        else:
            QMessageBox.information(None, "Oeps:", "Geen pand gevonden! Klik boven op een pand.")
        self.pandidentifyTool.pandIdentified.disconnect()

    #Return of identified layer and feature and get related object
    def get_identified_gebouw_terrein(self, ilayer, ifeature):
        #the identified layer must be "bouwlagen" or "BAG panden"
        if ilayer == None:
            self.run_new_object('wordt gekoppeld in de database', 'BGT', 'wordt gekoppeld in de database')
        elif ilayer.name() == "Objecten" or ilayer.name() == "Object terrein":
            #get_draw_layer_attr -> get attribute of identified layer from the config_file: Input (layername, attributename, searchable_config_list)
            objectId = ifeature["id"]
            #if ifeature["bron"] == 'BAG':
            self.draw_layer = getlayer_byname("Objecten")
            #else:
            #    self.draw_layer = getlayer_byname("Objecten BGT")
            #open dockwidget object and pass along the identified object and feature
            self.run_object()
            self.repressiefobjectwidget.existing_object(ifeature, objectId)
            #a new object has to be created if a BAG pand was identified objectId -> Bag identificatie nummer  
        elif ilayer.name() == "BAG panden":
            objectId   = str(ifeature["identificatie"])
            bron       = ifeature["bron"]
            bron_tabel = ifeature["bron_tbl"]
            self.run_new_object(objectId, bron, bron_tabel) 
        elif ilayer.name() == "Bouwlagen":
            objectId   = str(ifeature["pand_id"])
            bron       = 'BAG'
            bron_tabel = 'pand'
            #open dockwidget object and pass along the identified object and feature
            self.run_new_object(objectId, bron, bron_tabel)
        else:
            QMessageBox.information(None, "Oeps:", "Geen repressief object gevonden! Selecteer opnieuw.")
        self.pandidentifyTool.pandIdentified.disconnect()

    #laag filter aanpassen naar de geselecteerd bouwlaag
    def set_layer_subset_toolbar(self):
        QgsExpressionContextUtils.setProjectVariable(QgsProject.instance(), 'actieve_bouwlaag', int(self.projCombo.currentText()))
        sub_string = "bouwlaag = " + str(self.projCombo.currentText())
        set_layer_substring(self.read_config_bl, sub_string)        

    #pass on the tools to objectgegevens widget, intitializing the tools in the sub widget, draws an error
    def init_object_widget(self):
        #Load configuration file
        self.objectwidget = oivObjectWidget()
        self.objectwidget.read_config = self.read_config_bl
        self.objectwidget.canvas = self.canvas
        self.objectwidget.selectTool = self.selectTool
        self.objectwidget.basewidget = self.basewidget
        self.objectwidget.tekenTool = self.tekenTool
        self.objectwidget.lineTool = self.pinLine
        self.objectwidget.polygonTool = self.pinPolygon
        self.objectwidget.moveTool = self.moveTool
        self.objectwidget.identifyTool = self.identifyTool

    #pass on the tools to objectgegevens widget, intitializing the tools in the sub widget, draws an error
    def init_repressief_object_widget(self):
        self.read_config_obj = self.read_config_file("/config_files/csv/config_object.csv")
        self.repressiefobjectwidget = oivRepressiefObjectWidget()
        self.repressiefobjectwidget.read_config = self.read_config_obj
        self.repressiefobjectwidget.canvas = self.canvas
        self.repressiefobjectwidget.draw_layer = self.draw_layer
        self.repressiefobjectwidget.selectTool = self.selectTool
        self.repressiefobjectwidget.basewidget = self.basewidget
        self.repressiefobjectwidget.tekenTool = self.tekenTool
        self.repressiefobjectwidget.lineTool = self.pinLine
        self.repressiefobjectwidget.polygonTool = self.pinPolygon
        self.repressiefobjectwidget.moveTool = self.moveTool
        self.repressiefobjectwidget.identifyTool = self.identifyTool
        #self.repressiefobjectwidget.connect_buttons(self.read_config_obj)         

    #start objectgegevens widget
    def run_bouwlagen(self):
        self.init_object_widget()
        self.iface.addDockWidget(Qt.RightDockWidgetArea, self.objectwidget)
        self.iface.actionPan().trigger()
        self.objectwidget.show()
        self.basewidget.close()

    def run_object(self):
        self.init_repressief_object_widget()
        self.iface.addDockWidget(Qt.RightDockWidgetArea, self.repressiefobjectwidget)
        self.iface.actionPan().trigger()
        self.repressiefobjectwidget.show()
        self.basewidget.close()

    #start new object widget, eventhough passing trough the tools to objectgegevens widget
    def run_new_object(self, objectId, bron, bron_tbl):
        self.init_repressief_object_widget()
        self.objectnieuwwidget = oivObjectNieuwWidget()
        self.objectnieuwwidget.basewidget = self.basewidget
        self.objectnieuwwidget.objectwidget = self.repressiefobjectwidget
        self.iface.addDockWidget(Qt.RightDockWidgetArea, self.objectnieuwwidget)
        self.objectnieuwwidget.read_config = self.read_config_obj
        self.objectnieuwwidget.canvas = self.canvas
        self.objectnieuwwidget.mapTool = self.pinTool
        self.objectnieuwwidget.identificatienummer.setText(str(objectId))
        self.objectnieuwwidget.bron.setText(str(bron))
        self.objectnieuwwidget.bron_table.setText(str(bron_tbl))
        self.iface.actionPan().trigger()
        self.objectnieuwwidget.show()
        self.basewidget.close()

    #run the plugin, if project is not OIV object, deactivate plugin when clicked on icon
    def run(self):
        project = QgsProject.instance()
        projectTest = str(QgsExpressionContextUtils.projectScope(project).variable('project_title'))
        if 'Objecten' not in projectTest:
            self.toolbar.setEnabled(False)
            self.action.setEnabled(False)
        else:
            #always start from floor 1
            sub_string = "bouwlaag = 1"
            set_layer_substring(self.read_config_bl, sub_string)
            self.basewidget = oivBaseWidget()
            self.iface.addDockWidget(Qt.RightDockWidgetArea, self.basewidget)
            self.basewidget.identify_pand.clicked.connect(self.run_identify_pand)
            self.basewidget.identify_gebouw.clicked.connect(self.run_identify_gebouw_terrein)
            self.basewidget.closewidget.clicked.connect(self.close_basewidget)
            self.basewidget.show()
            self.toolbar.setEnabled(False)
            self.projCombo.setEnabled(False)
            self.check_visible = True