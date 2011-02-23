# vim:fileencoding=utf-8
import os
from vimWrapper import VimWrapper
from xml.sax.saxutils import escape
from const import *

class ExVimFileExplorer:

    def __init__(self):
        self.vw = VimWrapper(vimExec = vimExec)
        self.vw.start()
        curdir = os.getcwd()
        jQuery('#targetPath').val(curdir)

    def listup(self, topdir):
        if not os.path.isdir(topdir):
            return
        i = 0
        tree = {}
        rows = []
        for root, dirs, files in os.walk(topdir, topdown=True):
            for dir_ in dirs:
                i = i + 1
                node = 'node-' + str(i)
                full_path = os.path.join(root, dir_)
                parent = ''
                if root in tree:
                    parent = ' class="child-of-' + tree[root] + '"'
                rows.append([ full_path, '<tr id="' + node + '"' + parent + '>' \
                    + '<td><span class="folder" title="' + escape(full_path) \
                    + '">' + escape(dir_) + '</td>' \
                    + '</tr>' ]);
                tree[full_path] = node
            for file_ in files:
                i = i + 1
                node = 'node-' + str(i)
                full_path = os.path.join(root, file_)
                mod_path = os.path.join(root, '|' + file_)
                parent = ''
                if root in tree:
                    parent = ' class="child-of-' + tree[root] + '"'
                rows.append([ mod_path, '<tr id="' + node + '"' + parent + '>' \
                    + '<td><span class="file" title="' + escape(full_path) \
                    + '">' + escape(file_) + '</td>' \
                    + '</tr>' ]);
        rows.sort()
        table = jQuery('#result').empty()
        parent_dir = os.path.realpath(topdir + '/..')
        table.append('<tr id="node-0"><td><span class="folder" title="' \
            + parent_dir + '">..</span></td></tr>')
        for path, row in rows:
            table.append(row)

    def loadFile(self, path):
        if not os.path.exists(path):
            return
        bufId = self.vw.openFile(path)
        self.vw.server.sendCmd(bufId, 'stopDocumentListen', True)

