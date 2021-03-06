import wx
import os
import os.path
import NodeConfigSelector
from MSDataSyncAPI import DataSyncServer

from identifiers import *
import  wx.lib.filebrowsebutton as filebrowse
import plogging

import AdvancedPreferences


outlog = plogging.getLogger('client')

class Preferences(wx.Dialog):
    def __init__(self, parent, ID, config, log):
        # Instead of calling wx.Dialog.__init__ we precreate the dialog
        # so we can set an extra style that must be set before
        # creation, and then we create the GUI object using the Create
        # method.

        self.preference_keys = ['localdir', 'user', 'updateurl', 'loglevel']

        pre = wx.PreDialog()
        pre.SetExtraStyle(wx.DIALOG_EX_CONTEXTHELP)
        pre.Create(parent, ID, 'Preferences', wx.DefaultPosition, wx.DefaultSize, wx.DEFAULT_FRAME_STYLE)
        pre.width = 400
        #Turn the object into a proper dialog wrapper.
        self.PostCreate(pre)

        self.log = log
        self.parentApp = parent
        self.config = config

        # Now continue with the normal construction of the dialog
        # contents
        sizer = wx.BoxSizer(wx.VERTICAL)
        self.nodeconfigselector = None
        #Get the rest of the config
        k = self.config.getConfig().keys()
        k.sort()

        #report current node config name, and give button to choose
        box = wx.BoxSizer(wx.HORIZONTAL)
        self.nodeconfiglabel = wx.StaticText(self, -1, "" )
        self.setNodeConfigLabel()
        #box.Add(label, 1, wx.ALIGN_LEFT|wx.ALL, 2)

        sizer.Add(box, 1, wx.GROW|wx.ALIGN_CENTER_VERTICAL|wx.ALL, INTERNAL_BORDER_WIDTH)
        self.nodeconfigselector = NodeConfigSelector.NodeConfigSelector(self, ID_NODESELECTOR_DIALOG, self.log, None)

        #self.nodeconfigselector.createTree()
        sizer.Add(self.nodeconfigselector, 6, wx.GROW|wx.ALL, EXTERNAL_BORDER_WIDTH)


        buttonsbox = wx.BoxSizer(wx.HORIZONTAL)
        #and a button to upload keys
        keybutton = wx.Button(self, ID_SENDKEY_BUTTON)
        keybutton.SetLabel("Send Key")
        keybutton.Bind(wx.EVT_BUTTON, self.OnSendKey)
        buttonsbox.Add(keybutton, 1, wx.ALIGN_LEFT | wx.ALL, INTERNAL_BORDER_WIDTH)

        self.keybutton = keybutton

        #and a 'handshake' button
        hsbutton = wx.Button(self, ID_HANDSHAKE_BUTTON)
        hsbutton.SetLabel("Handshake")
        hsbutton.Bind(wx.EVT_BUTTON, self.OnHandshake)
        buttonsbox.Add(hsbutton, 1, wx.ALIGN_LEFT | wx.ALL, INTERNAL_BORDER_WIDTH)

        self.keybutton = keybutton
        self.handshakebutton = hsbutton

        sizer.Add(buttonsbox, 1, wx.GROW|wx.ALIGN_CENTER_VERTICAL|wx.ALL, INTERNAL_BORDER_WIDTH)

        self.fields = {}
        for key in self.preference_keys:
            if self.config.getShowVar(key):
                box = wx.BoxSizer(wx.HORIZONTAL)
                #if key == 'syncold':
                #    ctrl = wx.CheckBox(self, -1, "Sync Completed")
                #    self.Bind(wx.EVT_CHECKBOX, self.toggleSyncChoose, ctrl)
                #    #populate the checkbox with the current value
                #    val = self.config.getValue(key)
                #    if val:
                #        ctrl.SetValue(wx.CHK_CHECKED)
                #    else:
                #        ctrl.SetValue(wx.CHK_UNCHECKED)
                #    ctrl.SetHelpText(self.config.getHelpText(key))
                #    box.Add(ctrl, 1, wx.ALIGN_RIGHT|wx.ALL, border=INTERNAL_BORDER_WIDTH)
                if key == 'localdir':
                    ctrl = filebrowse.DirBrowseButton(self, -1, size=(450, -1), changeCallback = None, labelText=self.config.getFormalName(key), startDirectory = str(self.config.getValue(key)) )
                    ctrl.SetValue(str(self.config.getValue(key)) )
                    ctrl.SetHelpText(self.config.getHelpText(key))
                    box.Add(ctrl, 1, wx.ALIGN_RIGHT|wx.ALL, border=INTERNAL_BORDER_WIDTH)
                elif key == 'loglevel':
                    levelslist = [
                                    plogging.LoggingLevels.DEBUG.name,
                                    plogging.LoggingLevels.INFO.name,
                                    plogging.LoggingLevels.WARNING.name,
                                    plogging.LoggingLevels.FATAL.name,
                                    plogging.LoggingLevels.CRITICAL.name
                                 ]

                    ctrl =  wx.Choice(self, -1, choices=levelslist )

                    #make a 'getvalue' for the control:
                    def gv(self):
                        label = self.GetStringSelection()
                        level = plogging.LoggingLevels.getByName(label)
                        ret = plogging.LoggingLevels.WARNING #a good default, just in case
                        if (level):
                            ret = level
                        #actually set the logging level
                        plogging.set_level('client', ret)
                        return ret

                    #ctrl.GetValue = instancemethod(gv, ctrl, wx.Choice)
                    from types import MethodType
                    ctrl.GetValue = MethodType(gv, ctrl)

                    self.Bind(wx.EVT_CHOICE, self.logLevelChoose, ctrl)

                    #Lastly, lets select the current logging level.
                    n = ctrl.FindString(self.config.getValue('loglevel').name)
                    if n != wx.NOT_FOUND:
                        ctrl.Select(n)
                    label = wx.StaticText(self, -1, self.config.getFormalName(key))
                    ctrl.SetHelpText(self.config.getHelpText(key))
                    box.Add(label, 0, wx.ALIGN_LEFT| wx.ALIGN_CENTER_VERTICAL|wx.ALL, border=INTERNAL_BORDER_WIDTH)
                    box.Add(ctrl, 1, wx.ALIGN_RIGHT|wx.ALL, border=INTERNAL_BORDER_WIDTH)
                else:
                    label = wx.StaticText(self, -1, self.config.getFormalName(key))
                    label.SetHelpText(self.config.getHelpText(key))
                    box.Add(label, 0, wx.ALIGN_LEFT| wx.ALIGN_CENTER_VERTICAL|wx.ALL, border=INTERNAL_BORDER_WIDTH)
                    #the text entry field
                    ctrl = wx.TextCtrl(self, -1, str(self.config.getValue(key)) ) #, size=(80,-1))
                    ctrl.SetHelpText(self.config.getHelpText(key))
                    box.Add(ctrl, 1, wx.ALIGN_RIGHT|wx.ALL, border=INTERNAL_BORDER_WIDTH)
                sizer.Add(box, 1, wx.GROW|wx.ALIGN_CENTER_VERTICAL|wx.ALL, border=INTERNAL_BORDER_WIDTH)

                #store the field so we can serialise it later
                self.fields[key] = ctrl

        box = wx.BoxSizer(wx.HORIZONTAL)
        advbutton = wx.Button(self, ID_ADVANCED_PREFS_BUTTON)
        advbutton.SetLabel("Advanced")
        advbutton.Bind(wx.EVT_BUTTON, self.openAdvancedPrefs)
        box.Add(advbutton, 1, wx.ALIGN_CENTER_VERTICAL|wx.ALL, border=0)
        sizer.Add(box, 1, wx.GROW | wx.ALIGN_CENTER_VERTICAL | wx.ALL, border=INTERNAL_BORDER_WIDTH)

        btnsizer = wx.StdDialogButtonSizer()

        if wx.Platform != "__WXMSW__":
            btn = wx.ContextHelpButton(self)
            btnsizer.AddButton(btn)

        btn = wx.Button(self, wx.ID_OK)
        btn.SetHelpText("The OK button completes the dialog")
        btn.SetDefault()
        btnsizer.AddButton(btn)
        btn.Bind(wx.EVT_BUTTON, self.OKPressed)

        btn = wx.Button(self, wx.ID_CANCEL)
        btn.SetHelpText("Cancel changes")
        btnsizer.AddButton(btn)
        btnsizer.Realize()

        sizer.Add(btnsizer, 1, wx.ALIGN_CENTER_VERTICAL|wx.ALL, border=6)

        self.SetSizer(sizer)
        sizer.Fit(self)


    def openAdvancedPrefs(self, event):
        self.advanced = AdvancedPreferences.AdvancedPreferences(self, -1, self.config, self.log)
        self.advanced.Show()
        val = self.advanced.ShowModal()
        #doesn't return until the dialog is closed
        self.advanced.Destroy()

    def toggleSyncChoose(self, event):
        #Set the value of the checkbox to whatever the opposite of the current config value is.
        currentvalue = self.config.getValue('syncold')
        self.config.setValue('syncold', not currentvalue)

    def logLevelChoose(self, event):
        #self.log('Logging level set to: %s (%s)' % (event.GetString(), plogging.LoggingLevels.getByName(event.GetString()).value ) )
        self.log('Logging level set to: %s' % (event.GetString()) )

    def OKPressed(self, *args):
        self.save(args)
        self.EndModal(0)

    def OnSendKey(self, evt):
        outlog.debug('send keys!')
        self.keybutton.Disable()
        origlabel = self.keybutton.GetLabel()
        self.keybutton.SetLabel('Sending')

        try:
            #key is in the dir above the datadir
            keyfile = 'id_rsa.pub'
            keyfilepath = os.path.join(DATADIR, '..', keyfile)

            # Send it
            retval = DataSyncServer(self.config).send_key(keyfile, keyfilepath)
            outlog.debug('OnSendKey: retval is %s' % retval)
            self.log('Key send response: %s' % retval)
        except DataSyncServer.RestError, e:
            outlog.warning('OnSendKey: Exception occured: %s' % e)
            self.log('Exception occured sending key: %s' % e, type=self.log.LOG_ERROR)

        self.keybutton.Enable()
        self.keybutton.SetLabel(origlabel)

    def OnHandshake(self, evt):
        outlog.info('OnHandshake!')
        self.save()
        self.parentApp.MSDSHandshakeFn(self.parentApp, returnFn=None)

    def save(self, *args):
        #k = self.config.getConfig().keys()
        for key in self.preference_keys:
            if self.config.getShowVar(key): #if this is var shown on this dialog (not in the tree)
                outlog.debug('Setting config at %s to %s' % (str(key), self.fields[key].GetValue()) )
                self.config.setValue(key, self.fields[key].GetValue())

        #call the method that will serialise the config.
        self.config.save()
        self.parentApp.resetTimeTillNextSync()


    def setNodeConfigLabel(self):
        self.nodeconfiglabel.SetLabel("Current Node: %s" % (self.config.getNodeName()) )

    #this function gets called by the node chooser dialog,
    #and uses the data it passes to put values into the config, which arent
    #collected in the 'save' method above.
    def setNodeConfigName(self, datadict):
        for k in datadict.keys():
            self.config.setValue(k, datadict[k])
        self.setNodeConfigLabel()
