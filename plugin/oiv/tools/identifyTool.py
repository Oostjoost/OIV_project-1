from qgis.PyQt.QtCore import pyqtSignal, Qt
from qgis.PyQt.QtWidgets import QDialog, QVBoxLayout, QLabel, QDialogButtonBox, QComboBox, QMessageBox
from qgis.core import *
from qgis.gui import *
from .utils import *

#identify and select tools

class IdentifyGeometryTool(QgsMapToolIdentify, QgsMapTool):
    def __init__(self, canvas):
        self.canvas = canvas
        QgsMapToolIdentify.__init__(self, canvas)

    geomIdentified = pyqtSignal(['QgsVectorLayer', 'QgsFeature'])

    def canvasReleaseEvent(self, mouseEvent):
        results = self.identify(mouseEvent.x(), mouseEvent.y(), self.TopDownStopAtFirst, self.VectorLayer)
        if len(results) > 0:
            tempfeature = results[0].mFeature
            idlayer = results[0].mLayer
            self.geomIdentified.emit(idlayer, tempfeature)

class SelectTool(QgsMapToolIdentify, QgsMapTool):
    read_config = []

    def __init__(self, canvas):
        self.canvas = canvas
        QgsMapToolIdentify.__init__(self, canvas)

    geomSelected = pyqtSignal(['QgsVectorLayer', 'QgsFeature'])

    def canvasReleaseEvent(self, mouseEvent):
        results = self.identify(mouseEvent.x(), mouseEvent.y(), self.TopDownStopAtFirst, self.VectorLayer)
        if len(results) > 0:
            idlayer = results[0].mLayer
            allFeatures = []
            if len(results) > 1:
                for i in range(len(results)):
                    allFeatures.append(results[i].mFeature)
                tempfeature = self.ask_user_for_feature(idlayer, allFeatures)
            else:
                tempfeature = results[0].mFeature
            self.geomSelected.emit(idlayer, tempfeature)
        else:
            reply = QMessageBox.information(None, 'Geen tekenlaag!', 
                 "U heeft geen feature op een tekenlaag aangeklikt!\n\nKlik a.u.b. op de juiste locatie.", QMessageBox.Ok)

    def ask_user_for_feature(self, idLayer, allFeatures):
        targetFeature = None
        print(idLayer.name())
        print(self.read_config)
        type_layer_name = get_draw_layer_attr(idLayer.name(), "type_layer_name", self.read_config)
        attr_id = get_draw_layer_attr(idLayer.name(), "identifier", self.read_config)
        sortList = []
        for i in range(len(allFeatures)):
            if type_layer_name != '':
                request = QgsFeatureRequest().setFilterExpression('"id" = ' + str(allFeatures[i][attr_id]))
                type_layer = getlayer_byname(type_layer_name)
                tempFeature = next(type_layer.getFeatures(request))
                sortList.append([allFeatures[i]["id"], tempFeature["naam"]])
            else:
                sortList.append([allFeatures[i]["id"], allFeatures[i][attr_id]])
        AskFeatureDialog.askList = sortList
        chosen, ok = AskFeatureDialog.askFeature()
        for i in range(len(allFeatures)):
            if allFeatures[i]["id"] == int(chosen):
                targetFeature = allFeatures[i]
        return targetFeature

class AskFeatureDialog(QDialog):

    askList = []

    def __init__(self, parent = None):
        super(AskFeatureDialog, self).__init__(parent)
        self.setWindowTitle("Selecteer feature")
        qlayout = QVBoxLayout(self)
        self.qlineA = QLabel(self)
        self.qlineB = QLabel(self)
        self.qComboA = QComboBox(self)
        self.qlineA.setText("U heeft meerdere features geselecteerd.")
        self.qlineB.setText("Selecteer in de lijst de feature die u wilt bewerken.")

        self.qComboA.setFixedWidth(100)
        self.qComboA.setMaxVisibleItems(30)
        for i in range(len(self.askList)):
            self.qComboA.addItem(str(self.askList[i][1]), str(self.askList[i][0]))
        qlayout.addWidget(self.qlineA)
        qlayout.addWidget(self.qlineB)
        qlayout.addWidget(self.qComboA)
        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel,
            Qt.Horizontal, self)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        qlayout.addWidget(buttons)

    # static method to create the dialog and return (date, time, accepted)
    @staticmethod
    def askFeature(parent = None):
        dialog = AskFeatureDialog(parent)
        result = dialog.exec_()
        indexCombo = dialog.qComboA.currentIndex()
        return (dialog.qComboA.itemData(indexCombo), result == QDialog.Accepted)         

class IdentifyPandTool(QgsMapToolIdentify, QgsMapTool):
    def __init__(self, canvas):
        self.canvas = canvas
        QgsMapToolIdentify.__init__(self, canvas)

    pandIdentified = pyqtSignal(['QgsVectorLayer', 'QgsFeature'])

    def canvasReleaseEvent(self, mouseEvent):
        tempfeature = QgsFeature()
        results = self.identify(mouseEvent.x(), mouseEvent.y(), self.TopDownStopAtFirst, self.VectorLayer)
        if len(results) > 0:
            tempfeature = results[0].mFeature
            idlayer = results[0].mLayer
            self.pandIdentified.emit(idlayer, tempfeature)
        else:
            self.pandIdentified.emit(None, tempfeature)