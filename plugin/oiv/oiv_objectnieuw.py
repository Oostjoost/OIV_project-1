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
from qgis.PyQt.QtWidgets import QDialog, QDockWidget
from qgis.gui import *
from qgis.core import *
from qgis.utils import iface
from .tools.utils import *
from .tools.query_bag import *
from .oiv_objectgegevens import oivObjectWidget

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'oiv_objectnieuw_widget.ui'))

class oivObjectNieuwWidget(QDockWidget, FORM_CLASS):

    canvas = None
    read_config = None
    draw_layer = None
    basewidget = None
    objectwidget = None
    mapTool = None

    def __init__(self, parent=None):
        """Constructor."""
        super(oivObjectNieuwWidget, self).__init__(parent)
        self.setupUi(self)
        self.iface = iface        
        self.opslaan.clicked.connect(self.run_tekenen)
        self.terug.clicked.connect(self.close_objectnieuw_show_base)

    def close_objectnieuw_show_base(self):
        self.close()
        try:
            del self.objectwidget
        except:
            None
        self.basewidget.show()
        del self

    #place new object (i-tje)
    def run_tekenen(self):
        if self.bron.text() == 'BAG':
            run_layer = "Objecten"
        else:
            run_layer = "Objecten BGT"
        self.draw_layer = getlayer_byname(run_layer)
        self.canvas.setMapTool(self.mapTool)
        self.mapTool.canvasClicked.connect(self.place_feature)        

    #construct the feature and save
    def place_feature(self, point):
        childFeature = QgsFeature()
        self.iface.setActiveLayer(self.draw_layer)
        #set geometry from the point clicked on the canvas
        childFeature.setGeometry(QgsGeometry.fromPointXY(point))
        foreignKey = self.identificatienummer.text()
        print(foreignKey)
        buttonCheck = self.get_attributes(foreignKey, childFeature)
        #return of new created feature id
        if buttonCheck != 'Cancel':
            newFeatureId = write_layer(self.draw_layer, childFeature)
            tempFeature = QgsFeature()
            self.newObject = newFeatureId
            request = QgsFeatureRequest().setFilterExpression( '"id" = ' + str(self.newObject))
            print(str(self.newObject))
            tempFeature = next(self.draw_layer.getFeatures(request))
            #with new created feature run existing object widget
            self.run_objectgegevens(tempFeature)
        else:
            self.iface.actionPan().trigger()

    #get the right attributes from user
    def get_attributes(self, foreignKey, childFeature):
        input_fk = foreignKey
        question = get_draw_layer_attr(self.draw_layer.name(), "question", self.read_config)
        label_req = get_draw_layer_attr(self.draw_layer.name(), "label_required", self.read_config)        
        input_label = user_input_label(label_req, question)
        if input_label != 'Cancel':
            attr_label = get_draw_layer_attr(self.draw_layer.name(), "input_label", self.read_config)
            attr_fk = get_draw_layer_attr(self.draw_layer.name(), "foreign_key", self.read_config)       
            fields = self.draw_layer.fields()        
            childFeature.initAttributes(fields.count())
            childFeature.setFields(fields)
            if attr_label != '':
                childFeature[attr_label] = input_label
            if attr_fk != '':
                childFeature[attr_fk] = input_fk
            childFeature["bron"] = self.bron.text()
            childFeature["bron_tabel"] = self.bron_table.text()
            return childFeature
        else:
            return 'Cancel'

    #continue to existing object woth the newly created feature and already searched address
    def run_objectgegevens(self, tempFeature):
        self.draw_layer = getlayer_byname('Objecten')
        self.objectwidget.draw_layer = self.draw_layer
        self.objectwidget.existing_object(tempFeature, self.newObject)
        self.iface.addDockWidget(Qt.RightDockWidgetArea, self.objectwidget)
        self.objectwidget.show()
        self.iface.actionPan().trigger()
        self.close()        
        del self.objectwidget
        del self