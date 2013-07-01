# Copyright 2013 Matthew Woehlke <mw_triad@users.sourceforge.net>
# Licensed under GPLv3

import sys

from PyKDE4.kdecore import *
from PyKDE4.kdeui import *

from mainwindow import MainWindow

#==============================================================================
if __name__ == '__main__':

    appName     = "kochipylli"
    catalog     = ""
    programName = ki18n("Kochipylli")
    version     = "0.1.0"
    description = ki18n("Online image browsing, searching and archiving tool")
    license     = KAboutData.License_GPL
    copyright   = ki18n("Copyright 2013 Matthew Woehlke")
    text        = ki18n("none")
    homePage    = ""
    bugEmail    = "mw_triad@users.sourceforge.net"

    aboutData   = KAboutData(appName, catalog, programName, version,
                             description, license, copyright, text,
                             homePage, bugEmail)

    KCmdLineArgs.init(sys.argv, aboutData)

    app = KApplication()
    mainWindow = MainWindow(None)
    mainWindow.show()
    app.exec_()

#==============================================================================
# kate: replace-tabs on; replace-tabs-save on; indent-width 4;
