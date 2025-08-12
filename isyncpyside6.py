# isyncpyside6py
# minimal pyside6 skeleton using fusion style placeholder ui to begin porting from tk

import sys 

try :
    from PySide6 import QtWidgets ,QtGui ,QtCore 
except Exception as e :
    print ("PySide6 is required. Install with: pip install PySide6")
    raise 


class MainWindow (QtWidgets .QMainWindow ):
    def __init__ (self ):
        super ().__init__ ()
        self .setWindowTitle ("iSync (Qt) — iPhone IPA Installer")
        self .resize (1000 ,700 )

        # central widget with tabs
        central =QtWidgets .QWidget (self )
        self .setCentralWidget (central )
        vbox =QtWidgets .QVBoxLayout (central )

        self .tabs =QtWidgets .QTabWidget ()
        vbox .addWidget (self .tabs )

        # installer tab placeholder
        self .installer_tab =QtWidgets .QWidget ()
        self .tabs .addTab (self .installer_tab ,"Installer")
        self ._build_installer_tab ()

        # ixplorer tab placeholder
        self .ixplorer_tab =QtWidgets .QWidget ()
        self .tabs .addTab (self .ixplorer_tab ,"iXplorer")
        self ._build_ixplorer_tab ()

        # jailfr3e-installipa tab placeholder
        self .jf_tab =QtWidgets .QWidget ()
        self .tabs .addTab (self .jf_tab ,"JAILFR3E-INSTALLIPA")
        self ._build_jf_tab ()

        # applications tab placeholder
        self .apps_tab =QtWidgets .QWidget ()
        self .tabs .addTab (self .apps_tab ,"Applications")
        self ._build_apps_tab ()

        # about tab
        self .about_tab =QtWidgets .QWidget ()
        self .tabs .addTab (self .about_tab ,"About")
        self ._build_about_tab ()

        # status bar
        self .status =self .statusBar ()
        self .status .showMessage ("Ready")

    def _build_installer_tab (self ):
        lay =QtWidgets .QVBoxLayout (self .installer_tab )
        info =QtWidgets .QLabel ("Installer (Qt port placeholder). Use the Tk version (isync.py) for full features.")
        info .setWordWrap (True )
        lay .addWidget (info )

    def _build_ixplorer_tab (self ):
        lay =QtWidgets .QVBoxLayout (self .ixplorer_tab )
        info =QtWidgets .QLabel ("iXplorer (Qt port placeholder). Drag/drop + SCP pending.")
        info .setWordWrap (True )
        lay .addWidget (info )

    def _build_jf_tab (self ):
        lay =QtWidgets .QVBoxLayout (self .jf_tab )
        info =QtWidgets .QLabel ("JAILFR3E-INSTALLIPA (Qt port placeholder). AppDrop/Jailfree flows pending.")
        info .setWordWrap (True )
        lay .addWidget (info )

    def _build_apps_tab (self ):
        lay =QtWidgets .QVBoxLayout (self .apps_tab )
        info =QtWidgets .QLabel ("Applications (Qt port placeholder). Listing/launch pending.")
        info .setWordWrap (True )
        lay .addWidget (info )

    def _build_about_tab (self ):
        lay =QtWidgets .QVBoxLayout (self .about_tab )
        text =QtWidgets .QTextEdit ()
        text .setReadOnly (True )
        text .setPlainText (
        "iSync — iPhone IPA Installer & Explorer (Qt Edition)\n\n"
        "This is a preliminary PySide6 port using the Fusion style.\n"
        "Functional parity with the Tk app (isync.py) will be added incrementally.\n"
        )
        lay .addWidget (text )


def main ():
    app =QtWidgets .QApplication (sys .argv )
    # force fusion style
    QtWidgets .QApplication .setStyle ("Fusion")
    # optional: dark palette example - commented can be enabled later
    # palette = apppalette
    # appsetpalettepalette

    win =MainWindow ()
    win .show ()
    sys .exit (app .exec ())


if __name__ =="__main__":
    main ()
