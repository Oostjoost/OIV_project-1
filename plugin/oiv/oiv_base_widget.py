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
from qgis.PyQt import uic
from qgis.PyQt.QtWidgets import QDialog, QDockWidget

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'oiv_base_widget.ui'))

class oivBaseWidget(QDockWidget, FORM_CLASS):
    def __init__(self, parent=None):
        """Constructor."""
        super(oivBaseWidget, self).__init__(parent)
        self.setupUi(self)
