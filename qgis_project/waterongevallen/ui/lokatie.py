
#-----------------------------------------------------------
#
# Operationele Informatie Voorziening
#
# Copyright    : (C) 2016 Baas geo-information
# Email        : b.baas@baasgeo.com
#
#-----------------------------------------------------------
#
# licensed under the terms of GNU GPL 2
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this progsram; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
#
#---------------------------------------------------------------------

from PyQt4.QtCore import *
from PyQt4.QtGui import *
from qgis.core import QgsFeature,  QgsMapLayerRegistry, QgsSpatialIndex, QgsFeatureRequest
from qgis.utils import iface
 
myLayer = None
featureGeometry = None
 
def formOpen(dialog, layer, feature):
    global myLayer
    global featureGeometry
    myLayer = layer
    try:
        if (feature.geometry()):
            featureGeometry = feature.geometry()
            geom = feature.geometry().asPoint()
            extent = iface.mapCanvas().extent()
            objectenLayer = getVectorLayerByName("Lokaties")
            index = QgsSpatialIndex(objectenLayer.getFeatures(QgsFeatureRequest(extent)))
            features = index.nearestNeighbor(geom, 2)
            feature = objectenLayer.getFeatures(QgsFeatureRequest(features[0]))
            featureId = feature.next().id()
            dialog.changeAttribute("wo_lokatie_id", featureId)
            buttonBox = dialog.findChild(QDialogButtonBox, "buttonBox")
            bnOk = buttonBox.button(QDialogButtonBox.Ok)
            bnOk.clicked.connect(applySave)
    except:
        pass
 
def applySave():
    if (featureGeometry):
        myLayer.commitChanges()
        myLayer.startEditing()

def getVectorLayerByName(layerName):
    layerMap = QgsMapLayerRegistry.instance().mapLayers()
    for name, layer in layerMap.iteritems():
        if layer.type() == QgsMapLayer.VectorLayer and layer.originalName() == layerName:
            if layer.isValid():
                return layer
            else:
                return None