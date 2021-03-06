import wx
from StatusBar import StatusBar
from SysTrayIcon import SystrayIcon
from FileList import ListCtrlPanel
import time
import sys
from version import VERSION
from identifiers import *
import plogging
from WxLogger import Log

class APPSTATE:

    INITIING_SYNC = "Initiating sync with server"
    CHECKING_FILES = "Checking for files locally"
    GATHERING_FILES = "Gathering files for transfer"
    CHECKING_SYNCHUB = 'Negotiating with server'
    CONTACTING_RSYNC = 'Contacting Rsync server'
    CONFIRMING_TRANSFER = 'Confirming transfer'
    UPLOADING_DATA   = 'Uploading data'
    IDLE             = 'Idle'

import weakref

outlog = plogging.getLogger('client')

# Create and set a help provider.  Normally you would do this in
# the app's OnInit as it must be done before any SetHelpText calls.
provider = wx.SimpleHelpProvider()
wx.HelpProvider.Set(provider)
class MainWindow(wx.Frame):
    def __init__(self, config, parent):
        self.config = config

        plogging.set_level('client', self.config.getValue('loglevel'))
        wx.Frame.__init__(self, parent, -1, 'MS Datasync Application: v%s' % (VERSION))
        self.countDownEnabled = True #sets the countdown to be active

        self.contentPanel = wx.Panel(self, -1)
        _cp = self.contentPanel


        #progressLabel = wx.StaticText(parent = _cp)
        #progressLabel.SetLabel(label="Progress")

        #First thing, set up the log.
        self.logArea = wx.CollapsiblePane(_cp, -1, "Log", name='LogArea')
        self.logAreaPane = self.logArea.GetPane()
        self.logAreaSizer = wx.BoxSizer(wx.VERTICAL)
        self.logTextCtrl = wx.TextCtrl(self.logAreaPane, -1,
                                    style = wx.TE_MULTILINE|wx.TE_READONLY|wx.HSCROLL)



        #modify the log
        if wx.Platform == "__WXMAC__":
            self.logTextCtrl.MacCheckSpelling(False)

        self.log = Log(self.logTextCtrl)
        wx.Log_SetActiveTarget(self.log)



        #self.ListCtrlPanel = ListCtrlPanel(self, self.log)

        #menu bar
        #We set this up fairly early on in the piece so that the things below
        #status bars and timers etc, can enable/disable items in it.
        self.menuBar = wx.MenuBar()
        fileMenu = wx.Menu()
        #fileMenu.Append(ID_TEST_CONNECTION, "&Test Connection", "Test your connection to the server")
        fileMenu.Append(ID_CHECK_NOW, "&Check Now", "Check for required uploads now")
        fileMenu.AppendSeparator()
        fileMenu.Append(ID_PROGRAMUPDATES, "&Program Updates", "Check for new versions of this program")
        fileMenu.Append(ID_MINIMISE, "&Minimize", "Minimize the app to the system tray")
        fileMenu.Append(ID_QUIT, "&Quit", "Quits the application completely")

        editMenu = wx.Menu()
        editMenu.Append(ID_PREFERENCES, "&Preferences", "Application Preferences")

        helpMenu = wx.Menu()
        helpMenu.Append(ID_ABOUT, "&About", "About")
        helpMenu.Append(ID_PYCRUST, "&Pycrust", "Pycrust")

        self.menuBar.Append(fileMenu, "&File")
        self.menuBar.Append(editMenu, "&Edit")
        self.menuBar.Append(helpMenu, "&Help")

        #status bar
        self.StatusBar = StatusBar(self, self.log)
        self.SetStatusBar(self.StatusBar)
        self.state = APPSTATE.IDLE
        #self.StatusBar.SetStatusText(self.state)

        #sys tray icon
        self.SystrayIcon = SystrayIcon(self, self.log)
        self.SystrayIcon.SetIconTimer()

        self.setState(APPSTATE.IDLE)

        #Create a timer.
        self.timer = wx.Timer(self, -1)
        self.Bind(wx.EVT_TIMER, self.OnTimerTick, self.timer)
        self.timer.Start(milliseconds = 1000, oneShot = False)
        self.secondsUntilNextSync = 0
        self.syncFreq = 0 #local cache of syncfreq

        #Menu Events
        self.SetMenuBar(self.menuBar)
        self.Bind(wx.EVT_MENU_HIGHLIGHT_ALL, self.OnMenuHighlight)
        #self.Bind(wx.EVT_MENU, self.__testMenuFunction, id=ID_TEST_CONNECTION )
        self.Bind(wx.EVT_MENU, self.OnCheckNow, id=ID_CHECK_NOW )
        self.Bind(wx.EVT_MENU, self.OnMenuMinimise, id=ID_MINIMISE )
        self.Bind(wx.EVT_MENU, self.OnMenuQuit, id=ID_QUIT)
        self.Bind(wx.EVT_MENU, self.OnMenuPreferences, id=ID_PREFERENCES )
        self.Bind(wx.EVT_MENU, self.pycrust, id=ID_PYCRUST )
        self.Bind(wx.EVT_MENU, self.OnUpdateProgram, id=ID_PROGRAMUPDATES )
        self.Bind(wx.EVT_MENU, self.OnAbout, id=ID_ABOUT )

        #Collapsible pane event (the logArea):
        self.Bind(wx.EVT_COLLAPSIBLEPANE_CHANGED, self.OnPaneChanged, self.logArea)

        #A button to send logs to the webserver
        self.logbutton = wx.Button(self.logAreaPane, ID_SENDLOGS_BUTTON)
        self.logbutton.SetLabel("Send Log")
        self.logbutton.Bind(wx.EVT_BUTTON, self.OnSendLog)
        self.screenshotbutton = wx.Button(self.logAreaPane, ID_SENDSCREENSHOT_BUTTON)
        self.screenshotbutton.SetLabel("Send Shot")
        self.screenshotbutton.Bind(wx.EVT_BUTTON, self.OnTakeScreenshot)
        logWrap = wx.CheckBox(parent=self.logAreaPane, label="Wrap")
        logWrap.SetValue(False)
        logWrap.Bind(wx.EVT_CHECKBOX, self.ToggleLogWrap)

        #now lay everything out.
        self.logAreaSizer.Add(self.logTextCtrl, 1, flag=wx.ALL|wx.GROW|wx.EXPAND, border=0)
        #Log  footer box
        logfooterbox = wx.BoxSizer(wx.HORIZONTAL)
        #A place to set the log variable
        conf = self.config.getConfig()
        if self.config.getConfig():

            box = wx.BoxSizer(wx.HORIZONTAL)
            ctrl = wx.TextCtrl(self.logAreaPane, -1, str(self.config.getValue('logfile')), size=(80,-1))
            ctrl.SetHelpText(  self.config.getHelpText('logfile') )

            def OnLogFilenameSave(evt):
                self.config.setValue('logfile', ctrl.GetValue() )
                self.config.save()

            label =  wx.StaticText(self.logAreaPane, -1, self.config.getFormalName('logfile'))
            label.SetHelpText(self.config.getHelpText('logfile'))
            btn = wx.Button(self.logAreaPane, -1)
            btn.SetLabel('Set')
            btn.Bind(wx.EVT_BUTTON, OnLogFilenameSave )
            box.Add(label, 0, wx.ALIGN_LEFT| wx.ALIGN_CENTER_VERTICAL|wx.ALL, 0)
            box.Add(ctrl, 1, wx.ALIGN_CENTRE|wx.ALL, 0)
            box.Add(btn, 0, wx.ALIGN_RIGHT|wx.ALL, 0)
            logfooterbox.Add(box, 1,  wx.GROW|wx.ALIGN_CENTER_VERTICAL|wx.ALL, 0 )

        logfooterbox.Add(self.logbutton, 0, wx.ALL, 0)
        logfooterbox.Add(self.screenshotbutton, 0, wx.ALL, 0)
        logfooterbox.Add(logWrap, 0, wx.ALIGN_LEFT| wx.ALIGN_CENTER_VERTICAL|wx.ALL, 0)
        self.logAreaSizer.Add(logfooterbox, 0, flag=wx.ALL|wx.GROW|wx.EXPAND, border=2)
        self.logAreaPane.SetSizerAndFit(self.logAreaSizer)

        #timing controls:
        timingbox = wx.BoxSizer(wx.HORIZONTAL)
        self.nextsynctxt = wx.StaticText(_cp, -1, label="Next Sync in:")
        self.freqspin = wx.SpinCtrl(_cp, -1)
        self.freqspin.SetRange(1, 100000)
        self.freqspin.SetValue(int(self.config.getValue('syncfreq')))
        self.freqspin.Bind(wx.EVT_SPINCTRL, self.OnSpin)
        #freqbox = wx.BoxSizer(wx.HORIZONTAL)
        freqlab1 = wx.StaticText(_cp, -1, "Sync Frequency:")
        freqlab2 = wx.StaticText(_cp, -1, "mins")
        freqbox = wx.BoxSizer(wx.HORIZONTAL)
        freqbox.Add(freqlab1, 1, wx.ALIGN_RIGHT | wx.ALIGN_CENTER_VERTICAL | wx.ALL, border=0)
        freqbox.Add(self.freqspin, 1, wx.ALIGN_RIGHT | wx.GROW | wx.EXPAND | wx.ALL, border=0)
        freqbox.Add(freqlab2, 1, wx.ALIGN_RIGHT | wx.ALIGN_CENTER_VERTICAL | wx.ALL, border=0)
        timingbox.Add(self.nextsynctxt, 1, wx.ALIGN_LEFT | wx.GROW | wx.EXPAND | wx.ALL, border=0)
        timingbox.Add(freqbox, 1, wx.ALIGN_RIGHT | wx.GROW | wx.EXPAND | wx.ALL, border=0)

        #Populate the main window with the components
        contentpanelsizer = wx.BoxSizer(wx.VERTICAL)
        contentpanelsizer.Add(timingbox, 0, wx.GROW | wx.EXPAND | wx.ALL, border=0)
        contentpanelsizer.Add(self.logArea, 1, wx.ALL | wx.GROW | wx.EXPAND, border=0)
        #contentpanelsizer.Add(self.logArea, 1, wx.ALL | wx.GROW | wx.EXPAND | wx.FIXED_MINSIZE, border=0)

        self.contentPanel.SetSizerAndFit(contentpanelsizer)
        self.contentpanelsizer = contentpanelsizer

        #Expand the debug area by default:
        self.logArea.Expand()

        self.OnPaneChanged() #force a layout fit

        self.Bind(wx.EVT_CLOSE, self.OnCloseWindow)
        self.log('Finished loading application')

    def is_using_threading(self):
        if hasattr(self, 'msds'):
            return self.msds.useThreading #see main.py for how msds got set
        else:
            return False

    def ToggleLogWrap(self, evt):
        self.logTextCtrl.SetWindowStyle(self.logTextCtrl.GetWindowStyle() ^ wx.HSCROLL)
        self.logTextCtrl.Refresh()
        #self.log('Toggling Wrapping', type=self.log.LOG_DEBUG)

    def PauseCountdown(self):
        self.countDownEnabled = False

    def UnPauseCountdown(self):
        self.countDownEnabled = True

    def OnPaneChanged(self, event=None):
        if event:
            outlog.debug('wx.EVT_COLLAPSIBLEPANE_CHANGED: %s' % event.Collapsed)

        # redo the layout
        #if self.logArea.IsCollapsed():
        #    self.contentpanelsizer.Fit(self)
        #    #self.contentpanelsizer.Remove(self.logArea)
        #    self.logAreaSizer.Fit(self)#.contentPanel)
        #    self.contentpanelsizer.Fit(self)
        #else:
        #    #self.contentpanelsizer.Add(self.logArea, 1, flag=wx.ALL | wx.GROW | wx.EXPAND | wx.FIXED_MINSIZE, border=2)
        #    self.logAreaSizer.Layout()#.contentPanel)
        #    self.contentpanelsizer.Layout()

        #self.logAreaSizer.Fit(self)#.contentPanel)
        self.contentpanelsizer.Fit(self)
        #self.logAreaSizer.Layout()#.contentPanel)
        self.contentpanelsizer.Layout()


    def resetTimeTillNextSync(self, forceReset = False):
        f = int(self.config.getValue('syncfreq'))
        if forceReset or self.syncFreq != f:
            self.syncFreq = f
            self.secondsUntilNextSync = 60 * f

    def _set_state(self, state):
        self.state = state
        self.StatusBar.SetStatusText(state)
        if state != APPSTATE.IDLE:
            self.menuBar.Enable(ID_CHECK_NOW, False)
        else:
            self.menuBar.Enable(ID_CHECK_NOW, True)

    def setState(self, state):
        '''setState needs to set the statusbar text, and enable/disable the menu item for 'check now' '''
        #The menu on the system tray icon is created every time it is clicked:
        #We don't need to do anything here, as long as the state is set.

        thread = self.is_using_threading()
        if (thread):
            wx.CallAfter(self._set_state, state)
        else:
            self._set_state(state)

    def OnSpin(self, event):
        self.config.setValue('syncfreq', self.freqspin.GetValue())
        self.config.save()
        self.resetTimeTillNextSync()


    def OnMenuHighlight(self, event):
        # Show how to get menu item info from this event handler
        id = event.GetMenuId()
        item = self.GetMenuBar().FindItemById(id)
        if item:
            text = item.GetText()
            help = item.GetHelp()

        # but in this case just call Skip so the default is done
        event.Skip()

    def OnUpdateProgram(self, event):
        self.menuBar.Enable(ID_CHECK_NOW, False)
        self.PauseCountdown()
        if getattr(sys,"frozen",False):
            import esky
            url = self.config.getValue('updateurl')
            app = esky.Esky(sys.executable,url)
            try:
                self.log("The current version is: %s" % (str( app.active_version ) ) )
                self.log('Checking for program updates from %s' % (url))
                v = app.find_update()
                if v:
                    self.log("A newer version %s is available" % (str(v)) )
                    self.log("Fetching %s" % (str(v)))
                    app.fetch_version(v)
                    self.log("Completed download. Installing %s" % (str(v)) )
                    app.install_version(v)
                    wx.MessageBox('Upgrade to %s complete. The application will now close. Please restart it manually.' % (str(v)), 'Upgrade Complete!')
                    app.reinitialize()
                    self.OnMenuQuit(None)
                else:
                    self.log("There are no better versions available")
                    app.cleanup()
                #app.auto_update()
            except Exception, e:
                self.log("Error updating app: %s" % (str(e)), type=self.log.LOG_ERROR)
            app.cleanup()
        else:
            self.log('App must be frozen to initiate update')
        self.menuBar.Enable(ID_CHECK_NOW, True)
        self.UnPauseCountdown()


    def OnMenuMinimise(self, event):
        if not self.IsIconized():
            self.Iconize(True)
        if self.IsShown():
            self.Show(False)
        self.Lower()
        #self.log('Minimising App', type=self.log.LOG_DEBUG)

    def OnMenuQuit(self, evt):
        '''Close (quit) the parent app.'''
        #This is the only way to quit the app.
        self.log('Quitting...', type=self.log.LOG_DEBUG)
        try:
            self.Bind(wx.EVT_TIMER, None)
        except AssertionError, e:
            self.log("Assertion error, not sure why: %s" % e, type=self.log.LOG_DEBUG)
        self.timer.Stop()
        self.StatusBar.Destroy()
        self.SystrayIcon.Destroy()
        #self.MenuBar.Destroy() #this causes a seg fault!
        self.log('Called Exit. Cleaning up...', type=self.log.LOG_DEBUG)
        self.Destroy()


    def OnAbout(self, evt):
        #a = About.About(self, -1)
        #val = a.ShowModal()
        #a.Destroy()
        a = wx.AboutDialogInfo();
        a.AddDeveloper("Brad Power")
        a.AddDocWriter("Brad Power")
        a.SetCopyright("(C) 2010 CCG")
        a.SetDescription("MS data synchronisation tool for the Mastr-MS website")
        a.SetName("MS Datasync")
        a.SetVersion(VERSION)
        a.SetWebSite("http://ccg.murdoch.edu.au")
        wx.AboutBox(a);

    def OnMenuPreferences(self, evt):
        '''open the prefs dialog which BLOCKS'''
        import Preferences
        self.prefs = Preferences.Preferences(self, -1, self.config, self.log)
        self.prefs.Show() #Show the dialog first
        #Now refresh its stuff
        self.prefs.nodeconfigselector.refreshWebData()
        self.prefs.nodeconfigselector.selectNode()
        #Now make it modal
        # this does not return until the dialog is closed.
        val = self.prefs.ShowModal()
        #do something here with val if you like (==wx.ID_OK for instance)
        self.prefs.Destroy()
        self.prefs = None

    def OnCheckNow(self, evt):
        if self.state != APPSTATE.IDLE: #already busy. Just return
            return
        #MSDSCheckFn is defined by the main app - MDataSyncApp. It just sets the method in a hacky way :(
        self.SetProgress(0) #set progress to 0
        self.setState(APPSTATE.CHECKING_SYNCHUB)
        try:
            self.MSDSCheckFn(self, APPSTATE.UPLOADING_DATA, 'notused', self.CheckReturnFn)
        except Exception, e:
            import traceback
            self.log("Exception encountered: %s" % traceback.format_exc(e), type=self.log.LOG_ERROR)

    def SetProgress(self, prognum, add=False):

        #may be being called from a thread
        thread = self.is_using_threading()
        if (thread):
            wx.CallAfter(self._SetProgress, prognum, add=add)
        else:
            self._SetProgress(prognum, add=add)

    def _SetProgress(self, prognum, add = False):
        if (add):
            prognum += self.StatusBar.getProgress()

        self.StatusBar.setProgress(prognum)


    def CheckReturnFn(self, retcode = True, retstring = "", *args):
        #we may have come back from a thread here.
        thread = self.is_using_threading()
        if thread:
            wx.CallAfter(self.setState, APPSTATE.IDLE)
            wx.CallAfter(self.SetProgress, 100)
        else:

            self.setState(APPSTATE.IDLE)
            self.SetProgress(100)

        outlog.debug('return function called')
        if retcode:
            self.log('Check function returned', type=self.log.LOG_DEBUG, thread = thread)
        else:
            self.log(retstring, type=self.log.LOG_DEBUG, thread=thread)


    def __testMenuFunction(self, event):
        self.log('Menu event! %s' % str(event), type = self.log.LOG_DEBUG)

    def getLog(self):
        #return weakref.ref(self.log)
        return self.log

    def OnCloseWindow(self, event):
        self.OnMenuMinimise(event) #closing minimises

    def OnTimerTick(self, event):
        if not self.countDownEnabled:
            return

        if self.secondsUntilNextSync > 0:
            self.secondsUntilNextSync -= 1
            self.nextsynctxt.SetLabel("Next Sync in %s" % (str(self.secondsUntilNextSync) ) )
            #self.StatusBar.SetStatusText("Next sync in %s" % (str(self.secondsUntilNextSync) ), 1 )
        else:
            self.resetTimeTillNextSync(forceReset = True)
            self.OnCheckNow(None)

    def pycrust(self,event):
        import wx.py as py
        w= py.crust.CrustFrame(parent = self)
        w.Show()


    def OnSendLog(self, evt):
        outlog.debug('send logs!')
        self.logbutton.Disable()
        origlabel = self.logbutton.GetLabel()
        self.logbutton.SetLabel('Sending')
        rsync_logfile_path = self.config.getValue('logfile')
        rsync_logfile = os.path.split(rsync_logfile_path)[1]
        from MSDataSyncAPI import DataSyncServer
        try:
            retval = DataSyncServer(self.config).send_log(rsync_logfile, rsync_logfile_path)
            self.log('Log send response: %s' % retval)
        except DataSyncServer.RestError, e:
            outlog.warning('OnSendLog: Exception occured: %s' % (str(e)) )
            self.log('Exception occured sending log: %s' % (str(e)), type=self.log.LOG_ERROR)

        self.logbutton.Enable()
        self.logbutton.SetLabel(origlabel)

    def OnTakeScreenshot(self, event):
        """ Takes a screenshot of the screen at give pos & size (rect). """
        outlog.info('Taking screenshot...')
        rect = self.GetRect()
        # see http://aspn.activestate.com/ASPN/Mail/Message/wxpython-users/3575899
        # created by Andrea Gavana

        # adjust widths for Linux (figured out by John Torres
        # http://article.gmane.org/gmane.comp.python.wxpython/67327)
        if sys.platform == 'linux2':
            client_x, client_y = self.ClientToScreen((0, 0))
            border_width = client_x - rect.x
            title_bar_height = client_y - rect.y
            rect.width += (border_width * 2)
            rect.height += title_bar_height + border_width

        #Create a DC for the whole screen area
        dcScreen = wx.ScreenDC()

        #Create a Bitmap that will hold the screenshot image later on
        #Note that the Bitmap must have a size big enough to hold the screenshot
        #-1 means using the current default colour depth
        bmp = wx.EmptyBitmap(rect.width, rect.height)

        #Create a memory DC that will be used for actually taking the screenshot
        memDC = wx.MemoryDC()

        #Tell the memory DC to use our Bitmap
        #all drawing action on the memory DC will go to the Bitmap now
        memDC.SelectObject(bmp)

        #Blit (in this case copy) the actual screen on the memory DC
        #and thus the Bitmap
        memDC.Blit( 0, #Copy to this X coordinate
                    0, #Copy to this Y coordinate
                    rect.width, #Copy this width
                    rect.height, #Copy this height
                    dcScreen, #From where do we copy?
                    rect.x, #What's the X offset in the original DC?
                    rect.y  #What's the Y offset in the original DC?
                    )

        #Select the Bitmap out of the memory DC by selecting a new
        #uninitialized Bitmap
        memDC.SelectObject(wx.NullBitmap)

        img = bmp.ConvertToImage()
        import time
        timetext = time.asctime().replace(' ', '_').replace(':', '-')
        fileName = "screenshot_%s.png" % (timetext)
        fullfileName = os.path.join(DATADIR, fileName)
        img.SaveFile(fullfileName, wx.BITMAP_TYPE_PNG)
        outlog.info('...saving as png!')

        from MSDataSyncAPI import DataSyncServer

        try:
            retval = DataSyncServer(self.config).send_log(fileName, fullfileName)
            self.log('Screenshot send response: %s' % retval)
        except DataSyncServer.RestError, e:
            outlog.warning('OnSendScreenShot: Exception occured: %s' % e)
            self.log('Exception occured sending screenshot: %s' % e, type=self.log.LOG_ERROR)
