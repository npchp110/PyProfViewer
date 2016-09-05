import wx
import wx.lib.mixins.listctrl as listmix

from pstats import Stats, f8, func_std_string
import os
import locale

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
            cmpVal = cmp(item1, item2)
        #---

        # If the items are equal then pick something else to make the sort value unique
        if cmpVal == 0:
            cmpVal = cmp(*self.GetSecondarySortValues(col, key1, key2))

        if ascending:
            return cmpVal
        else:
            return -cmpVal

class PageOne(wx.ListCtrl, CustColumnSorterMixin):
    def __init__(self, parent):
        wx.ListCtrl.__init__(self, parent, style=wx.LC_REPORT|wx.BORDER_SUNKEN)
        self.InsertColumn(0, 'Name', width=300)
        self.InsertColumn(1, 'Call Count', width=130)
        self.InsertColumn(2, 'Internal Time', width=130)
        self.InsertColumn(3, 'I per Call', width=130)
        self.InsertColumn(4, 'Cumulative Time', width=130)
        self.InsertColumn(5, 'C per Call', width=130)
        CustColumnSorterMixin.__init__(self, 6)
        self.itemDataMap = {}

    def GetListCtrl(self):
        return self

    def show(self):
        self.DeleteAllItems()
        r = 0
        for k, v in self.itemDataMap.iteritems():
            self.InsertStringItem(r, v[0])
            self.SetStringItem(r,1, v[1])
            self.SetStringItem(r,2,f8(v[2]))
            self.SetStringItem(r,3,f8(v[3]))
            self.SetStringItem(r,4,f8(v[4]))
            self.SetStringItem(r,5,f8(v[5]))
            self.SetItemData(r, r)
            r = r + 1
        self.SetItemCount(len(self.itemDataMap))


    def set_stats(self, stats):
        self.stats = stats
        self.itemDataMap = {}
        width, list = self.stats.get_print_list({})
        r = 0
        if list:
            for func in list:
                cc, nc, tt, ct, callers = self.stats.stats[func]
                name = func_std_string(func)
                c = str(nc)
                if nc != cc:
                    c = c + '/' + str(cc)
                self.itemDataMap[r] = (name, c, tt, float(tt)/nc, ct, float(ct)/cc)
                self.SetItemData(r, r)
                r += 1
        self.show()

class FuncList(wx.ListCtrl, CustColumnSorterMixin):
    def __init__(self, parent):
        wx.ListCtrl.__init__(self, parent, style=wx.LC_REPORT|wx.BORDER_SUNKEN, size=(-1,100))
        self.InsertColumn(0, 'Name', width=300)
        self.InsertColumn(1, 'Call Count', width=130)
        self.InsertColumn(2, 'Internal Time', width=130)
        self.InsertColumn(3, 'Cumulative Time', width=130)
        CustColumnSorterMixin.__init__(self, 4)

        self.itemDataMap = {}

    def GetListCtrl(self):
        return self

    def show(self):
        self.DeleteAllItems()
        r = 0
        for k, v in self.itemDataMap.iteritems():
            self.InsertStringItem(r, v[0])
            self.SetStringItem(r,1, v[1])
            self.SetStringItem(r,2,f8(v[2]))
            self.SetStringItem(r,3,f8(v[3]))
            self.SetItemData(r, r)
            r = r + 1
        self.SetItemCount(len(self.itemDataMap))
        self.SortListItems(3, 0)

    def fill_rows(self, call_dict):
        r = self.GetItemCount()
        for func, v in call_dict.iteritems():
            name = func_std_string(func)
            if isinstance(v, tuple):
                nc, cc, tt, ct = v
                c = str(nc)
                if nc != cc:
                    c = c + '/' + str(cc)
                self.itemDataMap[r] = (name, c, tt, ct)
            else:
                self.itemDataMap[r] = ('%s(%r)' % (name, v), self.stats[func][3], 0, 0)
            r = r + 1
        self.show()


class PageTwo(wx.Panel):
    def __init__(self, parent):
        wx.Panel.__init__(self, parent)

        self.list1 = FuncList(self)
        self.list2 = FuncList(self)
        self.list3 = FuncList(self)
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
        self.list1.DeleteAllItems()
        self.list2.DeleteAllItems()
        self.list3.DeleteAllItems()

    def show_stack(self, event):
        self.clear()
        funcExp = event.GetText().replace('(', '\(').replace(')', '\)')
        width, list = self.stats.get_print_list([funcExp])
        if len(list) != 1:
            return
        func = list[0]

        cc, nc, tt, ct, callers = self.stats.stats[func]
        self.list1.fill_rows(callers)

        self.list2.fill_rows({func:(nc, cc, tt, ct)})

        self.stats.calc_callees()
        if func in self.stats.all_callees:
            self.list3.fill_rows(self.stats.all_callees[func])


########################################################################
class ViewerNotebook(wx.Notebook):
    def __init__(self, parent):
        wx.Notebook.__init__(self, parent, id=wx.ID_ANY, style=wx.BK_DEFAULT )
 
        self.tabOne = PageOne(self)
        self.AddPage(self.tabOne, "Func List")

        self.tabTow = PageTwo(self)
        self.AddPage(self.tabTow, "Call Stacks")

        self.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self.show_stack, self.tabOne)


    def open_stats(self):
        """ Open a file"""
        dlg = wx.FileDialog(self, "Choose a file", "", "", "*.*", wx.OPEN)
        if dlg.ShowModal() == wx.ID_OK:
            self.filename = dlg.GetFilename()
            self.dirname = dlg.GetDirectory()
            stat = Stats(os.path.join(self.dirname, self.filename))
            stat.strip_dirs()
            stat.sort_stats("cumulative")
            self.tabOne.set_stats(stat)
            self.tabTow.set_stats(stat)
        dlg.Destroy()

    def show_stack(self, event):
        self.ChangeSelection(1)
        self.tabTow.show_stack(event)

########################################################################
class Viewer(wx.Frame):
    """
    Frame that holds all other widgets
    """
 
    #----------------------------------------------------------------------
    def __init__(self):
        """Constructor"""
        wx.Frame.__init__(self, None, wx.ID_ANY,
                          "Python Profile Viewer",
                          size=(1000,600)
                          )
        panel = wx.Panel(self)

        self.notebook = ViewerNotebook(panel)
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.notebook, 1, wx.ALL|wx.EXPAND, 5)
        panel.SetSizer(sizer)
        self.Layout()

        self.create_menu()
        self.CreateStatusBar()
 
        self.Show()

    def create_menu(self):
        # Setting up the menu.
        filemenu= wx.Menu()
        menuOpen = filemenu.Append(wx.ID_OPEN, "&Open"," Open a file to edit")
        menuExit = filemenu.Append(wx.ID_EXIT,"E&xit"," Terminate the program")

        # Creating the menubar.
        menuBar = wx.MenuBar()
        menuBar.Append(filemenu,"&File") # Adding the "filemenu" to the MenuBar
        self.SetMenuBar(menuBar)  # Adding the MenuBar to the Frame content.

        # Events.
        self.Bind(wx.EVT_MENU, self.OnOpen, menuOpen)
        self.Bind(wx.EVT_MENU, self.OnExit, menuExit)

        self.accel_tbl = wx.AcceleratorTable([(wx.ACCEL_CTRL, ord('o'), menuOpen.GetId()),
                                             ])
        self.SetAcceleratorTable(self.accel_tbl)

    def OnExit(self,e):
        self.Close(True)  # Close the frame.

    def OnOpen(self,e):
        self.notebook.open_stats()
 
#----------------------------------------------------------------------
if __name__ == "__main__":
    app = wx.App(False)
    frame = Viewer()
    app.MainLoop()