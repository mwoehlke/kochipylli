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
    programName = ki18nc("@title application name", "Kochipylli")
    version     = "0.1.0"
    description = ki18n("Online image browsing, searching and archiving tool")
    license     = KAboutData.License_GPL
    copyright   = ki18n("Copyright 2013 Matthew Woehlke")
    text        = KLocalizedString()
    homePage    = ""
    bugEmail    = "mw_triad@users.sourceforge.net"

    aboutData   = KAboutData(appName, catalog, programName, version,
                             description, license, copyright, text,
                             homePage, bugEmail)
    KCmdLineArgs.init(sys.argv, aboutData)

    options = KCmdLineOptions()
    options.add("!+service", ki18nc("Command line argument help text",
                                    "Python service definition"))
    options.add("!+archive", ki18nc("Command line argument help text",
                                    "Location of archive directory"))
    KCmdLineArgs.addCmdLineOptions(options)

    args = KCmdLineArgs.parsedArgs()
    if args.count() < 2:
        args.usageError(i18nc("Command line usage error",
                              "Not enough arguments"))

    archive = QDir(args.arg(1))
    if not archive.exists():
        msg = i18nc("Command line error",
                    "Archive directory '%1' does not exist",
                    archive.path())
        sys.stderr.write(str(msg) + "\n")
        sys.exit(1)

    service_module = importlib.import_module(str(args.arg(0)))

    app = KApplication()
    mainWindow = MainWindow(service_module.createService(archive), archive)
    mainWindow.show()
    app.exec_()

#==============================================================================
# kate: replace-tabs on; replace-tabs-save on; indent-width 4;
