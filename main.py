# Copyright 2013 Matthew Woehlke <mw_triad@users.sourceforge.net>
# Licensed under GPLv3

import importlib
import sys

from PyQt4.QtCore import *

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

    options = KCmdLineOptions()
    options.add("!+service", ki18n("Python service definition"))
    options.add("!+archive", ki18n("Location of archive directory"))
    KCmdLineArgs.addCmdLineOptions(options)

    args = KCmdLineArgs.parsedArgs()
    if args.count() < 2:
        args.usageError(i18n("Not enough arguments"))

    archive = QDir(args.arg(1))
    if not archive.exists():
        sys.stderr.write("Archive directory '%s' does not exist\n" %
                         archive.path())
        sys.exit(1)

    service_module = importlib.import_module(str(args.arg(0)))

    app = KApplication()
    mainWindow = MainWindow(service_module.createService(archive), archive)
    mainWindow.show()
    app.exec_()

#==============================================================================
# kate: replace-tabs on; replace-tabs-save on; indent-width 4;
