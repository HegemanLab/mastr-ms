#!/usr/bin/env python

#This is the MSDataSync API. This API provides functions to keep a remote set of directories
#synced with a local set.
#It uses rsync to keep the directories in sync, over an SSH tunnel.
#It can be controlled via a GUI or any other means, and can emit log messages back to the control harness.
#
#You can either use a worker thread to get non blocking operation, in which case you
#call startThread and stopThread, or not. Either way will still work, just one will block and the
#other won't.

import json
import urllib
import urllib2
import yaphc
from httplib2 import Http

import os
import os.path
import sys
import time
import shutil
import shlex
import pipes
import tempfile

import Queue
import threading
from subprocess import Popen, PIPE, STDOUT

from version import VERSION

import plogging
outlog = plogging.getLogger('client')
from MainWindow import APPSTATE


def nullFn(*args, **kwargs):
    outlog.debug('null fn')
    pass

class RemoteSyncParams(object):
    def __init__(self, configdict = {}, username="!"):
        self.host = ""
        self.rootdir = ""
        self.flags = []
        self.username = ""
        self.rules = []
        self.fileslist = None
        self.file_changes = None

        #pull the configdict into our local class members
        #but only the values we have defined
        try:
            for key in self.__dict__:
                if configdict.has_key(key):
                    setattr(self, key, configdict[key])
        except Exception, e:
            pass

        #Flags are config authoritative
        if self.flags in ['', '!', [] ]: #The config didn't specify anything
            self.flags = ['-rvz']
        else:
            # unquote and split args string from config
            self.flags = shlex.split(self.flags)

        #Username is client authoritative
        if username not in ['', '!']:
            #use passed in value, not json value
            self.username = username

class TransactionVars(object):
    _copiedFiles = {}
    _transferredSamples = {}
    _sampleFileMap = {}
    _samplesverified = False

    def __init__(self):
        self.reset()

    def reset(self):
        self._copiedFiles = {}
        self._transferredSamples = {}
        self._sampleFileMap = {}
        self._samplesverified = False

    @property
    def copied_files(self):
        return self._copiedFiles
    @copied_files.setter
    def copied_files(self, copiedfiles):
        self._copiedFiles = copiedfiles

    @property
    def transferred_samples(self):
        return self._transferredSamples
    @transferred_samples.setter
    def transferred_samples(self, value):
        self._transferredSamples = value

    @property
    def sample_file_map(self):
        return self._sampleFileMap
    @sample_file_map.setter
    def sample_file_map(self, value):
        self._sampleFileMap = value

    @property
    def samples_verified(self):
        return self._samplesverified

    @samples_verified.setter
    def set_samples_verified(self, value):
        self._samplesverified = value


class MSDataSyncAPI(object):
    def __init__(self, config, log=None):
        self._tasks = Queue.Queue()
        if log is None:
            self.log = self.defaultLogSink
        else:
            self.log = log

        self._impl = MSDSImpl(self.log, self)
        self.config = config
        self.useThreading = False #Threading doesn't seem to help at the moment.
                                 #it needs to be enabled and then debugged -
                                 #we are still seeing UI lagging behind worker operations
        self.transactionvars = TransactionVars()

    # regard directories containing files which have this string in
    # their filename as being in the process of data collection.
    TEMP_FILE_NAMES = ["TEMP"]

    def defaultLogSink(self, *args, **kwargs):
        pass

    def startThread( self ):
        if hasattr( self, "_thread" ) and self._thread != None:
            return
        self._thread = self.Worker( self._tasks )
        self._thread.start()
        self.useThreading = True
        self.log("Threading is enabled")

    def stopThread( self ):
        if not hasattr( self, "_thread" ) or self._thread == None:
            return
        self._tasks.join()              # block until task queue is empty
        self._thread.die()              # tell the thread to die
        #print 'Flushing with None task'
        self._appendTask(None)          # dummy task to force thread to run
        self._thread.join()             # wait until thread is done
        self._thread = None
        self.useThreading = False
        self.log("Thread is stopped")

    def _appendTask(self, command, command_kwargs={}, callback=None, callback_kwargs={}):
        '''Either uses a thread (if available) or not.
           Obviously one doesn't block, and one does.
           Either way, the callback is called once done.'''
        if hasattr( self, "_thread" ) and self._thread != None:
            self._tasks.put_nowait((command, command_kwargs, callback, callback_kwargs))
        else:
            result = None
            try:
                result = command(**command_kwargs)
            except Exception, e:
                import traceback
                outlog.warning('Error running command (nonthreaded): %s' % traceback.format_exc(e))
                outlog.debug('Command args were: %s' % ", ".join("%s=%r" % x for x in command_kwargs.iteritems()))
                result = None
            if callback != None:
                callback(result, **callback_kwargs)

    def set_progress_state(self, progress, status):
        self.callingWindow.SetProgress(progress)
        self.callingWindow.setState(status)


    def handshakeRsync(self, callingWindow, returnFn = None):
        if returnFn is None:
            returnFn = self.defaultReturn
        self.callingWindow = callingWindow
        #get the local file list
        try:
            details = DataSyncServer(self.config).handshake()
        except DataSyncServer.RestError, e:
            returnFn(retcode=False, retstring="Error handshaking: %s" % e)
            return

        #I want to do an rsync -n
        rsyncconfig = RemoteSyncParams(configdict=details, username=self.config.getValue('user'))
        #Lets get any of the remote params
        #rsyncconfig.host = d['host']
        #rootdir
        #rsyncconfig.rootdir = ''
        #flags, server is authoratative
        rsyncconfig.flags = ['-n'] #n = dry run

        outlog.info( 'Handshaking' )
        #now rsync the whole thing over
        self._appendTask(self._impl.perform_rsync,
                         { "sourcedir": self.config.getValue("localdir"),
                           "rsyncconfig": rsyncconfig },
                         self.handshakeReturn)

    def ask_server_for_wanted_files(self, returnFn):
        self.callingWindow.setState(APPSTATE.INITIING_SYNC)
        self.callingWindow.SetProgress(100)
        details = {}
        files = {}

        #PART 1
        #first, tell the server who we are, and get a response
        server = DataSyncServer(self.config)
        jsonret = server.requestsync()

        if jsonret.get("success", False):
            details = jsonret["details"]
            files = jsonret["files"]
        else:
            #if there is an error, bail out by calling the return function
            returnFn(retcode=False, retstring="Sync Initiation failed: %s" % jsonret.get("message", "?"))

        return details, files

    def find_wanted_files(self, wantedfiles):
        self.callingWindow.setState(APPSTATE.CHECKING_FILES)
        self.callingWindow.SetProgress(0)
        #if something goes wrong, bail out by calling the return function
        #otherwise return the local file list
        localfilesdict = self.getFiles(self.config.getValue('localdir'), ignoredirs=[self.config.getLocalIndexPath()] )
        localindexdir = self.config.getLocalIndexPath()
        #see if we can resolve all wanted files:
        foundfiles = {}
        runsamplesdict = {}
        samplefilemap = {}
        for wantedfile in wantedfiles.keys():
            result = self.find_local_file_or_directory(localfilesdict, wantedfile)
            if result is not None:
                wantedrecord = wantedfiles[wantedfile]
                run_id = wantedrecord[0]
                sample_id = wantedrecord[1]
                relpath = wantedrecord[2]
                foundfiles[result] = os.path.join(localindexdir, relpath, wantedfile)
                if not runsamplesdict.has_key(run_id):
                    runsamplesdict[run_id] = []
                runsamplesdict[run_id].append(sample_id)
                if not samplefilemap.has_key(run_id):
                    samplefilemap[run_id] = {}
                samplefilemap[run_id][sample_id] = result #original file mapped to run:sample
        return foundfiles, runsamplesdict, samplefilemap

    def post_sync_step(self, server_reponse, filename_id_map):
        if self.config.getValue('archivesynced'):
            self._appendTask(self.archive_synced_files,
                             { "synced_samples_dict":
                                   server_reponse['synced_samples'],
                               "filename_id_map": filename_id_map })

        self._appendTask(self.cleanup_localindexdir)

    def archive_synced_files(self, synced_samples_dict, filename_id_map):
        if len(synced_samples_dict) > 0:
            # invert the filename -> id map and make ids strings
            filename_id_map = dict((tuple(map(str, v)), k)
                                   for (k, v) in filename_id_map.items())

            # Build list of (run_id, sample_id) pairs
            id_keys = []
            for run_id, sample_ids in synced_samples_dict.iteritems():
                for sample_id in sample_ids:
                    id_keys.append((str(run_id), str(sample_id)))

            # filenames from sample ids
            filenames = [filename_id_map[id_key] for id_key in id_keys
                         if id_key in filename_id_map]

            # Do the copy
            self.log("Archiving %d/%d synced files" % (len(filenames), len(id_keys)), thread=self.useThreading)
            for filename in filenames:
                self.archive_file(filename)
            self.log("Archive complete.", thread=self.useThreading)
        else:
            self.log("Nothing to archive.", thread=self.useThreading)

    def archive_file(self, filepath):
        "Move a file from config.localindexdir to config.archivedfilesdir."
        localindexdir = self.config.getLocalIndexPath()
        archivedfilesdir = self.config.getValue('archivedfilesdir')

        src = os.path.join(localindexdir, filepath)
        dst = os.path.join(archivedfilesdir, filepath)

        self.log("Move %s -> %s" % (src, dst), thread=self.useThreading)

        try:
            os.makedirs(os.path.dirname(dst))
        except OSError:
            pass # directory probably already exists

        try:
            shutil.move(src, dst)
        except EnvironmentError, e:
            self.log("Could not archive file: %s" % e, thread=self.useThreading)

    def cleanup_localindexdir(self):
        localindexdir = self.config.getLocalIndexPath()
        if os.path.exists(localindexdir):
            self.log("Clearing local index directory: %s" % localindexdir, thread=self.useThreading)
            def log_error(function, fullname, exc_info):
                self.log("Could not clear local index %s: %s" % (fullname, exc_info[1]),
                         type=self.log.LOG_WARNING, thread=self.useThreading)
            shutil.rmtree(localindexdir, onerror=log_error)

    #Actual API methods that DO something
    def checkRsync(self, callingWindow, statuschange, notused, returnFn = None):
        if returnFn is None:
            returnFn = self.defaultReturn
        c = self.config.getConfig()
        #get the local file list
        organisation = self.config.getValue('organisation')
        station = self.config.getValue('stationname')
        sitename = self.config.getValue('sitename')

        self.callingWindow = callingWindow

        remote_params, wantedfiles = self.ask_server_for_wanted_files(returnFn)
        self.transactionvars.reset()

        #localfilesdict is our map between local files that were found that the server wants,
        #and the file path that should exist on the remote end (and relative to our localindexdir)
        #runsamplesdict is just the list of found file sampleids, keyed on runid
        localfilesdict, runsamplesdict, samplefilemap = self.find_wanted_files(wantedfiles)
        self.transactionvars.sample_file_map = samplefilemap
        rsyncconfig = RemoteSyncParams(configdict = remote_params, username=self.config.getValue('user'))

        def wanted_filename((name, attrlist)):
            "Returns a tuple of (filename, (run_id, sample_id))"
            return ("%s/%s" % (attrlist[2], name), (attrlist[0], attrlist[1]))

        filename_id_map = dict(map(wanted_filename, wantedfiles.items()))
        rsyncconfig.fileslist = sorted(filename_id_map.keys())

        self.log('Server expects sync of %d files' % len(wantedfiles))
        self.log('Client found %d/%d files' % (len(localfilesdict), len(wantedfiles)))

        self.log("Server wants these files:\n%s" % "\n".join(rsyncconfig.fileslist),
                 type=self.log.LOG_DEBUG)

        #copy all the files
        self._appendTask(self._impl.copyfiles,
                         { "copydict": localfilesdict },
                         self.copyFilesReturn)

        if localfilesdict:
            # rsync the whole thing over
            self._appendTask(self._impl.perform_rsync,
                             { "sourcedir": self.config.getLocalIndexPath(),
                               "rsyncconfig": rsyncconfig },
                             self.rsyncReturn)

            #now tell the server to check the files off
            self._appendTask(self._impl.serverCheckRunSampleFiles,
                             { "rsyncconfig": rsyncconfig,
                               "filename_id_map": filename_id_map },
                             returnFn)
        else:
            self.log("No files to sync.", thread = self.useThreading)
            self._appendTask(self.set_progress_state,
                             { "progress": 100, "status": APPSTATE.IDLE })

    def defaultReturn(self, *args, **kwargs):
        #print 'rsync returned: ', retval
        self.log('Default return callback: args=%s, kwargs=%s' % (str(args), str(kwargs)), Debug=True, thread = self.useThreading)

    def copyFilesReturn(self, *args, **kwargs):
        self.log('Local file copy stage complete', thread = self.useThreading)
        #about to do the rsync. Set the progress state
        self.set_progress_state(50, APPSTATE.UPLOADING_DATA)
        outlog.debug("Finished copying")

    def rsyncReturn(self, success):
        "After rsync is finished, request the server to update samples."
        self.log('Remote transfer stage complete', thread = self.useThreading)
        self.set_progress_state(90, APPSTATE.CONFIRMING_TRANSFER)

    def handshakeReturn(self, success):
        self.log('Handshake complete', thread = self.useThreading)
        self.set_progress_state(100, APPSTATE.IDLE)

    def getFiles(self, dir, ignoredirs = []):
        '''returns a dictionary like structure representing the
           files. Like this:
           { '.' : [list of filenames],
             '/' : 'path to this dir'
             'dirname' : {dict like this one},
             'dirname2' : {dict like this one},
           }
        '''

        retfiles = {}
        retfiles['/'] = dir
        retfiles['.'] = {}
        for root, dirs, files in os.walk(dir):
            shouldignore = False
            for ignoredir in ignoredirs:
                if root.startswith(ignoredir):
                    shouldignore = True
                    break

            if shouldignore:
                #print 'did an ignore of: ', root, dirs, files
                continue #go to the next iteration of the loop

            #get the current 'node' of the dict for this level
            path = root.split(dir)[1].split(os.sep)
            node = retfiles
            for p in path:
                if len(p):
                    node = node[p]

            #don't create ignored dirs..
            for dirname in dirs:
                if not node.has_key(dirname) and os.path.join(root, dirname) not in ignoredirs:
                    outlog.debug( 'creating dirname: %s' % ( dirname.encode('utf-8') ) )
                    node[dirname] = {}
                    node[dirname]['.'] = {}
                    node[dirname]['/'] = os.path.join(root, dirname)

            for file in files:
                #print 'setting filename %s to None' % (file.encode('utf-8'))
                node['.'][file] = None

        #print 'retfiles is: ', unicode(retfiles).encode('utf-8')
        return retfiles

    def should_exclude(self, objectname):
        will_exclude = False
        for excludestring in self.TEMP_FILE_NAMES:
            if objectname.upper().startswith(excludestring.upper()):
                will_exclude = True
        return will_exclude

    def find_local_file_or_directory(self, localfiledict, filename):
        ''' does a depth first search of the localfiledict.
            will return the local path to the file/directory if found, or None.
            The filename comparison is non case sensitive '''

        def checkfilesatnode(node, filename):
            #print "Node:", node
            #print

            #check against files.
            if node.has_key('.'):
                for fname in node['.']:
                    #print "Checking file ", fname
                    if fname.upper() == filename.upper():
                        if not self.should_exclude(filename):
                            return os.path.join(node['/'], fname)

            #check against dirs
            for dname in node.keys():
                if dname not in ['.', '/']:
                    #print 'checking dir ', dname
                    if dname.upper() == filename.upper():
                        #for dirs, their correct path will be in their node:
                        found_exclude = False
                        for fname in node[dname]['.']:
                            if self.should_exclude(fname):
                                found_exclude = True
                        if not found_exclude:
                            return node[dname]['/']
                    else:
                        #descend into the dir
                        found =  checkfilesatnode(node[dname], filename)
                        if found is not None:
                            return found


            #no directories to descend into?
            #and you got this far?
            #then return None.
            return None

        return checkfilesatnode(localfiledict, filename)

    #------- WORKER CLASS-----------------------
    class Worker( threading.Thread ):
        SLEEP_TIME = 0.1

        #-----------------------------------------------------------------------
        def __init__( self, tasks ):
            threading.Thread.__init__( self )
            self._isDying = False
            self._tasks = tasks

        #-----------------------------------------------------------------------
        def run( self ):
            while not self._isDying:
                (command, command_kwargs, callback, callback_kwargs) = self._tasks.get()
                if command is None:
                    continue
                result = None
                try:
                    #print 'worker thread executing %s with args %s' % (str(command), str(command_kwargs))
                    result = command(**command_kwargs)
                except Exception, e:
                    import traceback
                    outlog.warning('Error running command (threaded): %s' % traceback.format_exc(e))
                    outlog.debug('Command args were: %s' % ", ".join("%s=%r" % x for x in command_kwargs.iteritems()))
                    #print 'command(kwargs) was: %s(%s,%s)' % (str(command), str(command_kwargs))

                    result = None
                if callback != None:
                    callback(result, **callback_kwargs)
                self._tasks.task_done()

        #-----------------------------------------------------------------------
        def die( self ):
            self._isDying = True


class MSDSImpl(object):
    '''the implementation of the MSDataSyncAPI'''
    def __init__(self, log, controller):
       self.log = log #we expect 'log' to be a callable function.
       self.controller = controller
       self.lastError = ""

    def cygwin_pathname(self, sourcedir):
        #fix the sourcedir.
        #On windows, the driveletter and colon make rsync think
        #that it is a host:path pair. So on windows, we need to fix that.
        #What we do is find the drive letter, get rid of the colon, and then prefix
        #the sourcedir name with /cygdrive
        #we also make sure the path is 'normalised', so that they look like posix paths,
        #since both mac, linux, and cygwin all use it.
        if sys.platform.startswith("win"):
            #print 'WINDOWS SOURCE DIR HACK IN PROGRESS'
            #os.path.normpath makes sure slashes are native - on windows this is an escaped backslash \\
            #os.sep gives you the dir sepator for this platform (windows = \\)
            #os.path.splitdrive splits the path into drive,path : ('c:', '\something\\somethingelse')
            drive,winpath = os.path.splitdrive(os.path.normpath(sourcedir))
            outlog.debug('drive is %s and winpath is %s' % (drive, winpath))

            #so for the winpath, we replace all \\ and then \ with /
            winpath=winpath.replace(os.sep, '/')
            winpath=winpath.replace('\\', '/')
            if drive:
                #then we take the drive letter (drive[0]) and put it after /cygdrive
                cygpath = "/%s/%s%s" % ('cygdrive', drive[0], winpath)
                outlog.debug('cygpath is: %s' % ( cygpath ) )
                sourcedir = cygpath
            else:
                sourcedir = winpath

        return sourcedir

    @staticmethod
    def ensure_trailing_slash(dirname):
        "make sure it ends in a slash"
        if dirname and dirname[-1] != "/":
            return dirname + '/'
        return dirname

    def perform_rsync(self, sourcedir, rsyncconfig):
        outlog.debug('checkRsync implementation entered!')

        sourcedir = self.ensure_trailing_slash(self.cygwin_pathname(sourcedir))

        logfile = self.cygwin_pathname(self.controller.config.getValue('logfile')) #if its a windows path, convert it. cwrsync wants posix paths ALWAYS

        #cmdhead = ['rsync', '-tavz'] #t, i=itemize-changes,a=archive,v=verbose,z=zip
        cmdhead = ['rsync']
        cmdhead.extend(rsyncconfig.flags)
        remote_dir = '%s@%s:%s' % (rsyncconfig.username, rsyncconfig.host,
                                   rsyncconfig.rootdir)
        cmdtail = ['--log-file=%s' % logfile, sourcedir, remote_dir]

        cmd = []
        cmd.extend(cmdhead)

        #self.log('Rules is %s' %(str(rules)) )
        rules = rsyncconfig.rules
        if rules is not None and len(rules) > 0:
            for r in rules:
                if r is not None:
                    cmd.append(r)

        cmd.extend(cmdtail)

        # On linux, assume file system encoding is utf-8.
        # On windows, the file system probably stores filenames in
        # utf-16. But cygwin rsync kindly translates these into utf-8
        # for us.
        rsync_encoding = "utf-8"

        files_list = tempfile.NamedTemporaryFile()

        if rsyncconfig.fileslist is not None:
            fixed_files_list = sorted(map(self.cygwin_pathname, rsyncconfig.fileslist))
            self.log('--include-from list is\n  %s' % u"\n  ".join(fixed_files_list),
                     thread=self.controller.useThreading, type=self.log.LOG_DEBUG)
            files_list.write((u"\0".join(fixed_files_list)).encode(rsync_encoding))
            files_list.flush()
            cmd.extend(["--include-from", self.cygwin_pathname(files_list.name), "--from0"])

        cmd.extend(["--itemize-changes"] * 2)

        self.log('Rsync command is: %s' % u" ".join(map(pipes.quote, cmd)),
                 thread=self.controller.useThreading, type=self.log.LOG_DEBUG)

        p = Popen(cmd, shell=False, stdout=PIPE, stderr=PIPE,
                  universal_newlines=True)

        (stdoutdata, stderrdata) = p.communicate()
        self.lastError = stderrdata

        stdoutdata = unicode(stdoutdata, rsync_encoding)
        stderrdata = unicode(stderrdata, rsync_encoding)

        self.log("rsync output is:\n%s" % stdoutdata,
                 thread=self.controller.useThreading, type=self.log.LOG_DEBUG)

        rsyncconfig.file_changes = self.parse_rsync_changes(stdoutdata)

        if len(stderrdata) > 0:
            self.log('Error Rsyncing: %s' % stderrdata, type=self.log.LOG_ERROR, thread=self.controller.useThreading)

        return p.returncode == 0

    @staticmethod
    def parse_rsync_changes(data):
        """
        The rsync --itemize-changes option produces data on which
        files changed during transfer. This function parses the output
        and returns a map of filename -> (bool, bool) indicating which
        items changed during rsync, and which were directories.
        """
        def parse_line(line):
            # See rsync(1) for information on the %i format
            split = 11
            code = line[:split]
            filename = line[split+1:]
            if len(code) == split:
                ischanged = lambda c: c not in (".", " ")
                changed = (code[0] in ("<", "c") and
                           (ischanged(code[2]) or ischanged(code[3])))
                return (code[1] == "d", strip_trailing_slash(filename), changed)
            else:
                return None

        def strip_trailing_slash(path):
            return path.rstrip("/")

        def changes_dict(change_list):
            """
            Convert [(isdir, filename, changed)] to a dict mapping
            filename -> (isdir, changed).

            If files are changed within a directory, then it is also
            marked as changed.
            """
            changes = {}
            for isdir, filename, changed in change_list:
                if changed:
                    # mark filename as changed and propagate this up
                    # the directory tree
                    parent = filename
                    while parent:
                        changes[parent] = (isdir, True)
                        parent = os.path.split(parent)[0]
                        isdir = True
                else:
                    changes.setdefault(filename, (isdir, False))

            return changes

        change_list = filter(bool, map(parse_line, data.split("\n")))
        return changes_dict(change_list)

    @staticmethod
    def cull_empty_dirs(file_changes):
        """
        Removes empty directories from the rsync file_changes listing
        and strip out isdir attribute.
        file_changes is a dictionary of { filename: (isdir, changed) }
        and this function returns [(filename, changed)].
        """
        files = sorted(file_changes.keys())

        def has_children(dirname):
            "Returns whether there are filenames prefixed with dirname"
            return any(f for f in files
                       if f != dirname and f.startswith(dirname))

        sorted_change_list = [(f, file_changes[f]) for f in files]

        return [(filename, changed)
                for filename, (isdir, changed) in sorted_change_list
                if not isdir or has_children(filename)]

    def make_run_sample_dict(self, rsyncconfig, filename_id_map):
        # It's difficult to know when a complete sample is
        # transferred.
        # So we consider a sample file to be complete
        # when the *second time* it is rsynced across, the file is not
        # updated.
        # If the sample filename is a directory and it contains TEMP files,
        # immediately assume the instrument software is still writing
        # data and therefore the sample is not complete.
        runsampledict = {}
        for filename, updated in self.cull_empty_dirs(rsyncconfig.file_changes):
            has_temp = bool(self.find_temp_files(filename))
            if not updated and filename in filename_id_map and not has_temp:
                run_id, sample_id = filename_id_map[filename]
                runsampledict.setdefault(run_id, []).append(sample_id)
        return runsampledict

    def serverCheckRunSampleFiles(self, rsyncconfig, filename_id_map):
        runsampledict = self.make_run_sample_dict(rsyncconfig, filename_id_map)

        self.log('Informing the server of transfer: %s' % runsampledict,
                 thread=self.controller.useThreading)

        server = DataSyncServer(self.controller.config)

        try:
            jsonret = server.checksamplefiles(runsampledict, self.lastError)
            self.log('Server returned %s' % jsonret, thread = self.controller.useThreading)
            self.log('Finished informing the server of transfer', thread = self.controller.useThreading)
            self.controller.post_sync_step(jsonret, filename_id_map)
        except DataSyncServer.RestError, e:
            self.log('Could not confirm sample files: %s' % e,
                     type=self.log.LOG_ERROR,
                     thread=self.controller.useThreading)

    def find_temp_files(self, objectname):
        """
        If objectname is a directory within the datadir, return list
        of pathnames (relative to localdir) of any TEMP files.
        """
        localdir = self.controller.config.getValue("localdir")

        objectname = os.path.basename(objectname)

        def find_object(dir, name):
            "generates all instances of objectname within the data dir"
            for dirpath, dirnames, filenames in os.walk(dir):
                for dirname in dirnames:
                    if dirname == name:
                        yield os.path.join(dirpath, dirname)

        is_temp = self.controller.should_exclude

        temp_files = []
        for dirname in find_object(localdir, objectname):
            for dirpath, dirnames, filenames in os.walk(dirname):
                temp_files.extend(os.path.join(dirpath, f)
                                  for f in filenames if is_temp(f))
                temp_files.extend(os.path.join(dirpath, f)
                                  for f in dirnames if is_temp(f))

        return [os.path.relpath(f, localdir) for f in temp_files]

    def copyfiles(self, copydict):
        '''Takes a dict keyed on source filename, and copies each one to the dest filename (value) '''
        outlog.debug("Entered copy procedure")

        copiedfiles = {}

        try:
            for filename in copydict.keys():
                self.log( '\tCopying %s to %s' % (os.path.normpath(filename), os.path.normpath(copydict[filename] ) ), thread=self.controller.useThreading  )
                src = os.path.normpath(filename)
                dst = os.path.normpath(copydict[filename])
                self.copyfile( src, dst)
                copiedfiles[src] = dst
        except Exception, e:
            self.log('Problem copying: %s' % e, type=self.log.LOG_ERROR,  thread = self.controller.useThreading )

        self.controller.transactionvars.copied_files = copiedfiles

    def copyfile(self, src, dst):
        try:
            if os.path.isdir(src) and not os.path.exists(dst):
                shutil.copytree(src, dst)
            else:
                thepath = os.path.dirname(dst)
                if not os.path.exists(thepath):
                    self.log('Path %s did not exist - creating' % thepath,
                             thread=self.controller.useThreading)
                    os.makedirs(thepath)
                shutil.copy2(src, dst)
        except EnvironmentError, e:
            self.log('Error copying %s to %s : %s' % (src, dst, e), type = self.log.LOG_ERROR,  thread = self.controller.useThreading )

    def getFileTree(self, directory):
        allfiles = []
        try:
            for root, dirs, files in os.walk(directory): #topdown=True, onerror=None, followlinks=False
                for f in files:
                    allfiles.append(os.path.join(root, f))
                #self.log('root: %s' % (str(root)) )
                #self.log('dirs: %s' % (str(dirs)) )
                #self.log('files: %s' % (str(files)) )
            for f in allfiles:
                self.log('File: %s' % f, thread = self.controller.useThreading )
        except Exception, e:
            self.log('getFileTree: Exception: %s' % e, self.log.LOG_ERROR, thread = self.controller.useThreading)
        return allfiles

class DataSyncSite(object):
    """
    Represents a data sync client site.
    """
    def __init__(self, organisation, station, sitename):
        self.organisation = organisation
        self.station = station
        self.sitename = sitename

    @classmethod
    def from_config(cls, config):
        organisation = config.getValue('organisation')
        station = config.getValue('stationname')
        sitename = config.getValue('sitename')
        return cls(organisation, station, sitename)

    def url(self):
        return u"%(organisation)s/%(sitename)s/%(station)s" % vars(self)

class DataSyncServer(object):
    """
    This class makes REST API calls to the MS data sync server and
    repository components.
    These methods all block, so need to be run different thread to the UI.
    """

    class RestError(EnvironmentError):
        "This exception type is raised if anything goes wrong with an API call"
        pass

    def __init__(self, config):
        self.config = config

    def handshake(self):
        """
        Handshake with server, whatever that means.
        Raises DataSyncServer.RestError if something went wrong.
        """
        #return self._handshake_wrong(DataSyncSite.from_config(self.config))
        return self.requestsync()["details"]

    def _handshake_wrong(self, site):
        postvars = {
            'files': self._jsonify({}),
            'organisation': self._jsonify(site.organisation),
            'sitename': self._jsonify(site.sitename),
            'stationname': self._jsonify(site.station),
            }

        return self._jsoncall(self._get_synchub_url(), postvars)

    def requestsync(self):
        """
        Ask server for wanted files.
        Returns a dictionary with keys "success", "message", ...
        This method handles exceptions.
        """
        site = DataSyncSite.from_config(self.config)
        return self._requestsync(site)

    def _requestsync(self, site):
        syncvars = {"version": VERSION , "sync_completed": self.config.getValue("syncold") }
        outlog.debug("syncvars are: %s" % syncvars)

        url = self._get_requestsync_url(site)

        try:
            jsonret = self._jsoncall(url, syncvars)
            jsonret.setdefault("success", True)
        except self.RestError, e:
            jsonret = { "success": False, "message": str(e) }

        return jsonret

    def checksamplefiles(self, runsampledict, last_error):
        site = DataSyncSite.from_config(self.config)
        return self._checksamplefiles(site, runsampledict, last_error)

    def _checksamplefiles(self, site, runsampledict, last_error):
        postvars = {
            'runsamplefiles' : self._jsonify(runsampledict),
            'lastError': last_error,
            'organisation': site.organisation,
            'sitename': site.sitename,
            'stationname': site.station,
            }
        outlog.debug("Postvars: %s " % repr(postvars))
        url = self._get_checksamplefiles_url()
        return self._jsoncall(url, postvars)

    def get_node_names(self):
        url = self._get_node_names_url()
        try:
            retval = self._jsoncall(url, timeout=1)
            outlog.debug('node config: %s' % retval)
            assert isinstance(retval, dict), 'Returned json was not a dict'
            outlog.debug( 'node config loaded object is: %s' % (retval) )
        except self.RestError, e:
            outlog.warning( 'Error retrieving node config data: %s' % (str(e)) )
            retval = None

        return retval

    def send_key(self, keyfile, keyfilepath):
        #Start the multipart encoded post of whatever file our log is saved to:
        posturl = self._get_send_key_url()
        outlog.debug('sending log %s to %s' % (keyfile, posturl))
        return self._yaphc(posturl,
                           {'nodename': self.config.getNodeName()},
                           [('uploaded', keyfile, keyfilepath)])

    def send_log(self, logfile, logfile_path):
        #Start the multipart encoded post of whatever file our log is saved to:
        outlog.debug('reading logfile' )
        params = {'nodename': self.config.getNodeName() }
        files = [('uploaded', logfile, logfile_path)]
        return self._yaphc(self._get_send_log_url(), params, files)

    def _yaphc(self, url, params, files):
        http = yaphc.Http()
        request = yaphc.PostRequest(self._get_send_key_url(), params=params, files=files)
        outlog.debug("opening url %s" % url)
        try:
            resp, jsonret = http.make_request(request)
            outlog.debug('finished receiving data')
            outlog.debug("received: %s" % jsonret)
        except Exception, e:  # not good
            raise self.RestError(e)

        try:
            return json.loads(jsonret)
        except ValueError, e:
            outlog.exception("Couldn't decode this JSON:\n%s\n" % jsonret)
            raise self.RestError(e)

    def _jsoncall(self, url, params=None, timeout=None):
        """
        Makes a request to `url' and decodes the json response.
        If `params' is a dict, the request method will be POST.
        Will raise a RestError if anything went wrong.
        """

        # pinched from http://stackoverflow.com/questions/6480723/urllib-urlencode-doesnt-like-unicode-values-how-about-this-workaround
        def encoded_dict(in_dict):
            out_dict = {}
            for k, v in in_dict.iteritems():
                if isinstance(v, unicode):
                    v = v.encode('utf8')
                elif isinstance(v, str):
                    # Must be encoded in UTF-8
                    v.decode('utf8')
                out_dict[k] = v
            return out_dict

        data = None if params is None else urllib.urlencode(encoded_dict(params))
        try:
            req = urllib2.Request(url)
            f = urllib2.urlopen(req, data, timeout)
        except IOError, e: # fixme: exception handling
            raise self.RestError(e)
        except ValueError, e:
            raise self.RestError(e)

        jsondata = unicode(f.read(), "utf-8")

        outlog.debug( 'Checking response' )

        try:
            ob = json.loads(jsondata)
            outlog.info('Synchub config loaded object is: %s' % self._jsonify(ob))
            return ob
        except ValueError, e:
            outlog.exception("Couldn't decode this JSON:\n%s\n" % jsondata)
            raise self.RestError(e)

    def _jsonify(self, ob):
        return json.dumps(ob, ensure_ascii=False, sort_keys=True, indent=2)

    def _get_synchub_url(self, *path):
        sync_baseurl = self.config.getValue('synchub')
        slash = "/" if not sync_baseurl.endswith('/') else ""
        path = "".join(elem + "/" for elem in path)
        return sync_baseurl + slash + urllib.quote(path.encode('utf8'))

    def _get_requestsync_url(self, site):
        return self._get_synchub_url("requestsync", site.url())

    def _get_checksamplefiles_url(self):
        return self._get_synchub_url("checksamplefiles")

    def _get_node_names_url(self):
        return self._get_synchub_url("nodes")

    def _get_send_key_url(self):
        return self._get_synchub_url("keyupload")

    def _get_send_log_url(self):
        return self._get_synchub_url("logupload")
