from qgis.core import *
from qgis.gui import *
from qgis.PyQt.QtWidgets import QInputDialog, QLineEdit, QMessageBox

import os

#get QgsLayer by name
def getlayer_byname(layername):
    layer = None
    layers = QgsProject.instance().mapLayersByName(layername)
    layer = layers[0]
    return (layer)

def user_input_label(label_req, question):
    label = ''
    qid = QInputDialog()
    #communiceer met de gebruiker voor input, waarbij question de vraag is die wordt gesteld
    if label_req < '2':
        while True:
            label, ok = QInputDialog.getText(qid, "Label:", question, QLineEdit.Normal,)
            if ok:
                if label != '' or label_req == '0':
                    return label
                    break
            else:
                label = 'Cancel'
                return label
                break

#derivation of layer type
def check_layer_type(layer):
    if layer.geometryType() == QgsWkbTypes.PointGeometry:
        return "Point"
    elif layer.geometryType() == QgsWkbTypes.LineGeometry:
        return "Line"
    elif layer.geometryType() == QgsWkbTypes.PolygonGeometry:
        return "Polygon"

#write the attributes to layer
def write_layer(layer, childFeature):
    layer.startEditing()
    result, newFeatures = layer.dataProvider().addFeatures([childFeature])
    layer.commitChanges()
    layer.triggerRepaint()
    return newFeatures[0].id()

#search the nearest parent feature id
def nearest_neighbor(iface, layer, point):
    index = None
    parentId = None
    parentFeature = None
    extent = iface.mapCanvas().extent()
    #veroorzaakt foutmelding als er niets in het kaartvenster staat, daarom in try/except statement
    index = QgsSpatialIndex(layer.getFeatures(QgsFeatureRequest(extent)))
    try:
        parentId = index.nearestNeighbor(point, 1)[0]
        parentFeature = next(layer.getFeatures(QgsFeatureRequest(parentId)))
    except:
        parentId = None
    return parentFeature, parentId

#get feature from specific id    
def request_feature(ifeature, layer_feature_id, layer_name):
    objectId = ifeature[layer_feature_id]
    request = QgsFeatureRequest().setFilterExpression( '"id" = ' + str(objectId))
    tempLayer = getlayer_byname(layer_name)
    tempFeature = next(tempLayer.getFeatures(request))
    return tempFeature, objectId

#create unique sorted dropdown list
def create_unique_sorted_list(sortList):
    output = []
    for x in sortList:
        if x not in output:
            output.append(x)
    output.sort()
    return output

#get attribute value out of config file related to header(q_string)
def get_draw_layer_attr(run_layer, q_string, read_config):
    myList = []
    answer = ''
    myList = read_config[0]
    attr_y = myList.index(q_string)
    for i in range(len(read_config)):
        if read_config[i][0] == run_layer:
            answer = read_config[i][attr_y]
    return answer

#set layer subset according (you can check the subset under properties of the layer)
def set_layer_substring(read_config, sub_string):
    for i in range(1, len(read_config)):
        layer = getlayer_byname(read_config[i][0])
        layer.setSubsetString(sub_string)

def refresh_layers(iface):
    for layer in iface.mapCanvas().layers():
        layer.triggerRepaint()