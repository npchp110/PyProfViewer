#!/usr/local/bin/python
import wx
import wx.lib.mixins.listctrl as listmix
from operator import lt

from pstats import Stats, f8, func_std_string, func_strip_path
import os, sys
import locale

STRIPE_DIR = True

class CustColumnSorterMixin(wx.lib.mixins.listctrl.ColumnSorterMixin):
    def __init__(self, numColumns):
        wx.lib.mixins.listctrl.ColumnSorterMixin.__init__(self, numColumns)

    def GetColumnSorter(self):
        return self.CustColumnSorter

    def CustColumnSorter(self, key1, key2):
        col = self._col
        ascending = self._colSortFlag[col]
        item1 = self.itemDataMap[key1][col]
        item2 = self.itemDataMap[key2][col]

        #--- Internationalization of string sorting with locale module
        if type(item1) == type('') or type(item2) == type(''):
            cmpVal = locale.strcoll(str(item1), str(item2))
        else:
            cmpVal = -1 if lt(item1, item2) else 1
        #---

        # If the items are equal then pick something else to make the sort value unique
        if cmpVal == 0:
            cmpVal = -1 if lt(*self.GetSecondarySortValues(col, key1, key2)) else 1

        if ascending:
            return cmpVal
        else:
            return -cmpVal

class FuncList(wx.ListCtrl, CustColumnSorterMixin):
    def __init__(self, parent):
        wx.ListCtrl.__init__(self, parent, style=wx.LC_REPORT|wx.BORDER_SUNKEN, size=(-1,100))
        self.InsertColumn(0, 'Call Count', width=70)
        self.InsertColumn(1, 'Internal Time', width=100)
        self.InsertColumn(2, 'I per Call', width=100)
        self.InsertColumn(3, 'Cumulative Time', width=100)
        self.InsertColumn(4, 'C per Call', width=100)
        self.InsertColumn(5, 'Name', width=500)
        CustColumnSorterMixin.__init__(self, 6)
        self.itemDataMap = {}

    def GetListCtrl(self):
        return self

    def strip_dirs(self, strip=True):
        for r in range(self.GetItemCount()):
            item = self.GetItem(r)
            i = item.GetData()
            func = self.itemDataMap[i][-1]
            if strip:
                func = func_strip_path(func)
            self.SetStringItem(r, 5, func_std_string(func))

    def show(self):
        self.DeleteAllItems()
        r = 0
        for k, v in iter(self.itemDataMap.items()):
            self.InsertStringItem(r, v[0])
            self.SetStringItem(r,1,f8(v[1]))
            self.SetStringItem(r,2,f8(v[2]))
            self.SetStringItem(r,3,f8(v[3]))
            self.SetStringItem(r,4,f8(v[4]))
            self.SetStringItem(r,5,v[5])

            self.SetItemData(r, r)
            r = r + 1
        self.SortListItems(3, 0)

    def fill_line(self, r, func, cc, nc, tt, ct, strip=True):
        name = func_std_string(func)
        if strip:
            name = func_std_string(func_strip_path(func))
        c = str(nc)
        if nc != cc:
            c = c + '/' + str(cc)
        self.itemDataMap[r] = (c, tt, float(tt)/nc, ct, float(ct)/cc, name, func)

class OverviewFuncList(FuncList):
    def set_stats(self, stats, strip=True):
        self.stats = stats
        self.itemDataMap.clear()
        width, list = self.stats.get_print_list([])
        r = 0
        if list:
            for func in list:
                cc, nc, tt, ct, callers = self.stats.stats[func]
                self.fill_line(r, func, cc, nc, tt, ct, strip=strip)
                r += 1
        self.show()


class StackFuncList(FuncList):
    def fill_rows(self, call_dict, strip=True):
        r = self.GetItemCount()
        for func, v in iter(call_dict.items()):
            nc, cc, tt, ct = v
            self.fill_line(r, func, cc, nc, tt, ct, strip=strip)
            r = r + 1
        self.show()

class StackFuncPage(wx.Panel):
    def __init__(self, parent):
        wx.Panel.__init__(self, parent)

        self.list1 = StackFuncList(self)
        self.list2 = StackFuncList(self)
        self.list3 = StackFuncList(self)
        self.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self.show_stack, self.list1)
        self.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self.show_stack, self.list3)

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.list1, 2, wx.EXPAND)
        sizer.Add(self.list2, 0, wx.EXPAND)
        sizer.Add(self.list3, 4, wx.EXPAND)
        self.SetSizer(sizer)

    def set_stats(self, stats):
        self.stats = stats
        self.clear()

    def clear(self):
        self.list1.itemDataMap.clear()
        self.list2.itemDataMap.clear()
        self.list3.itemDataMap.clear()
        self.list1.DeleteAllItems()
        self.list2.DeleteAllItems()
        self.list3.DeleteAllItems()

    def show_stack(self, event):
        global STRIPE_DIR
        func_name = event.EventObject.itemDataMap[event.GetData()][5]
        funcExp = func_name.replace('(', '\(').replace(')', '\)')
        width, list = self.stats.get_print_list([funcExp])
        if len(list) != 1:
            return
        func = list[0]

        self.clear()
        cc, nc, tt, ct, callers = self.stats.stats[func]
        self.list1.fill_rows(callers, STRIPE_DIR)

        self.list2.fill_rows({func:(nc, cc, tt, ct)}, STRIPE_DIR)

        self.stats.calc_callees()
        if func in self.stats.all_callees:
            self.list3.fill_rows(self.stats.all_callees[func], STRIPE_DIR)


########################################################################
class ViewerNotebook(wx.Notebook):
    def __init__(self, parent):
        wx.Notebook.__init__(self, parent, id=wx.ID_ANY, style=wx.BK_DEFAULT )
 
        self.tabOne = OverviewFuncList(self)
        self.AddPage(self.tabOne, "Func List")

        self.tabTow = StackFuncPage(self)
        self.AddPage(self.tabTow, "Call Stacks")

        self.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self.show_stack, self.tabOne)

    def strip_dirs(self, strip=True):
        self.tabOne.strip_dirs(strip)
        self.tabTow.list1.strip_dirs(strip)
        self.tabTow.list2.strip_dirs(strip)
        self.tabTow.list3.strip_dirs(strip)

    def set_stats(self, stat, strip=True):
        self.ChangeSelection(0)
        self.tabOne.set_stats(stat, strip=strip)
        self.tabTow.set_stats(stat)

    def show_stack(self, event):
        self.ChangeSelection(1)
        self.tabTow.show_stack(event)

########################################################################
class Viewer(wx.Frame):
    """
    Frame that holds all other widgets
    """
 
    #----------------------------------------------------------------------
    def __init__(self, name):
        """Constructor"""
        wx.Frame.__init__(self, None, wx.ID_ANY,
                          name,
                          size=(1000,600)
                          )
        panel = wx.Panel(self)

        self.notebook = ViewerNotebook(panel)
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.notebook, 1, wx.ALL|wx.EXPAND, 5)
        panel.SetSizer(sizer)
        self.Layout()

        self.create_menu()
        self.status_bar = self.CreateStatusBar()
 
        self.Show()

    def create_menu(self):
        # Setting up the menu.
        filemenu= wx.Menu()
        menuOpen = filemenu.Append(wx.ID_OPEN, "&Open"," Open a file to edit")
        menuStrip = filemenu.Append(wx.ID_ANY, "&Strip Dir"," Strip leading path")
        menuExit = filemenu.Append(wx.ID_EXIT,"E&xit"," Terminate the program")

        # Creating the menubar.
        menuBar = wx.MenuBar()
        menuBar.Append(filemenu,"&File") # Adding the "filemenu" to the MenuBar
        self.SetMenuBar(menuBar)  # Adding the MenuBar to the Frame content.

        # Events.
        self.Bind(wx.EVT_MENU, self.OnOpen, menuOpen)
        self.Bind(wx.EVT_MENU, self.OnStrip, menuStrip)
        self.Bind(wx.EVT_MENU, self.OnExit, menuExit)

        self.accel_tbl = wx.AcceleratorTable([(wx.ACCEL_CTRL, ord('o'), menuOpen.GetId()),
                                              (wx.ACCEL_CTRL, ord('s'), menuStrip.GetId()),
                                             ])
        self.SetAcceleratorTable(self.accel_tbl)

    def OnExit(self,e):
        self.Close(True)  # Close the frame.

    def OnStrip(self,e):
        global STRIPE_DIR
        STRIPE_DIR = not STRIPE_DIR
        self.notebook.strip_dirs(STRIPE_DIR)

    def OnOpen(self,e):
        """ Open a file"""
        global STRIPE_DIR
        dlg = wx.FileDialog(self, "Choose a file", "", "", "*.*", wx.FD_OPEN)
        if dlg.ShowModal() == wx.ID_OK:
            filename = dlg.GetFilename()
            dirname = dlg.GetDirectory()
            filepath = os.path.join(dirname, filename)
            self.status_bar.SetStatusText(filepath)

            stat = Stats(filepath)
            #stat.strip_dirs()
            stat.sort_stats("cumulative")
            self.notebook.set_stats(stat, STRIPE_DIR)
        dlg.Destroy()

 
#----------------------------------------------------------------------
if __name__ == "__main__":
    name = "Python Profile Viewer"
    if len(sys.argv) > 1:
        name = "%s %s" % (name ,sys.argv[1])
    app = wx.App(False)
    frame = Viewer(name)
    app.MainLoop()