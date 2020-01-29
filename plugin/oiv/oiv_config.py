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
from qgis.PyQt.QtCore import pyqtSignal
from qgis.PyQt import uic
from qgis.PyQt.QtWidgets import QDialog, QDockWidget

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'oiv_config_widget.ui'))

class oivConfigWidget(QDockWidget, FORM_CLASS):

    canvas = None
    iface = None
    layer =  None
    read_config = None
    selectTool = None
    objectId = None
    objectwidget = None
    bouwlaagList = []

    def __init__(self, parent=None):
        super(oivConfigWidget, self).__init__(parent)
        self.setupUi(self)
        self.table_widget = self.findChild(QtGui.QTableWidget, "tableWidget")
        self.load.clicked.connect(self.load_config_file)
        self.terug.clicked.connect(self.close_config)

    def load_config_file(self):
        self.read_config = self.read_config_file("/config_files/config_layer.txt")
        self.populate_table()

    def read_config_file(self, file):
        config_list = []
        basepath = os.path.dirname(os.path.realpath(__file__))
        with open(basepath + file, 'r' ) as inp_file:
            lines = inp_file.read().splitlines()
        for line in lines:
            config_list.append(line.split(','))
        inp_file.close()
        return config_list

    def populate_table(self):
        header = []
        header = self.read_config[0]
        self.table_widget.setHorizontalHeaderLabels(header)
        column = self.table_widget.horizontalHeader()
        for i in range(len(header)):
            column.setResizeMode(i, QHeaderView.ResizeToContents)
        for i in range(len(self.read_config) - 1):
            for j in range(len(header)):
            #name = QTableWidgetItem(field)
                value = QTableWidgetItem(self.read_config[i + 1][j])
            #self.table_widget.setItem(i,0,name)
                self.table_widget.setItem(i,j,value)

    def close_config(self):
        self.close()