#!/usr/bin/env python

#import all of the wxPython GUI package
from wxPython.wx import *

import core

##################################################################
## view for disassebled memory
##################################################################
class DisView(wxListCtrl):
    def __init__(self, parent, core = None):
        self.core = core
        wxListCtrl.__init__(self, parent, -1, size=(420,250),
                 style=wxLC_REPORT|wxLC_VIRTUAL|wxLC_HRULES|wxLC_VRULES)
        self.InsertColumn(0, "Address")
        self.InsertColumn(1, "Insn")
        self.InsertColumn(2, "cycles")
        self.SetColumnWidth(0, 60)
        self.SetColumnWidth(1, 300)
        self.SetColumnWidth(2, 40)

        self.SetItemCount(0)

        self.attr1 = wxListItemAttr()
        self.attr1.SetFont(wxFont(10, wxMODERN, wxNORMAL, wxNORMAL, 0, 'Courier New'))

        self.attr2 = wxListItemAttr()
        self.attr2.SetBackgroundColour("yellow")
        self.attr2.SetFont(wxFont(10, wxMODERN, wxNORMAL, wxNORMAL, 0, 'Courier New'))

        EVT_LIST_ITEM_SELECTED(self, self.GetId(), self.OnItemSelected)
        EVT_LIST_ITEM_ACTIVATED(self, self.GetId(), self.OnItemActivated)

        self.discache = []

    def OnItemSelected(self, event):
        self.currentItem = event.m_itemIndex

    def OnItemActivated(self, event):
        self.currentItem = event.m_itemIndex

    def getColumnText(self, index, col):
        item = self.GetItem(index, col)
        return item.GetText()

    #---------------------------------------------------
    # These methods are callbacks for implementing the
    # "virtualness" of the list...
    def OnGetItemText(self, item, col):
        try:
            return str(self.discache[item][1+col])
        except IndexError:
            return ''
        #return "Item %d, column %d" % (item, col)

    def OnGetItemImage(self, item):
        return 0

    def OnGetItemAttr(self, item):
        try:
            if self.discache[item][0] == int(self.core.PC):
                return self.attr2
        except IndexError:
            pass
        return self.attr1

    def disasseble(self, address, lines = 0):
        self.discache = []
        linelist = []
        pc = core.PC(self.core, address)
        while lines and len(linelist) < lines or not lines:
            adr = int(pc)
            name, args, execfu, cycles = self.core.disassemble(pc)
            note = "%-6s %s" % (
                '%s%s' % (name, ('','.b')[args[0]]),
                ', '.join(map(str,args[1:]))
            )
            linelist.append( "0x%04x: %s" % (adr, note) )
            self.discache.append( (adr, '0x%04x' % adr, note, cycles) )
            if execfu is None and not lines:
                break
        self.SetItemCount(len(self.discache))
        self.Refresh()
        #self.dis.SetValue('\n'.join(linelist))

##################################################################
## view for memory as hexdump
##################################################################
#table lines represent 16 bytes -> 0x1000 lines for 65k memory

class MemView(wxListCtrl):
    def __init__(self, parent, core=None):
        self.core = core
        wxListCtrl.__init__(self, parent, -1, size=(630,400),
                 style=wxLC_REPORT|wxLC_VIRTUAL|wxLC_HRULES|wxLC_VRULES)
        self.InsertColumn(0, "Address")
        self.InsertColumn(1, "Content")
        self.InsertColumn(2, "ASCII")
        self.SetColumnWidth(0, 60)
        self.SetColumnWidth(1, 400)
        self.SetColumnWidth(2, 150)

        self.SetItemCount(0x1000)

        self.attr1 = wxListItemAttr()
        self.attr1.SetFont(wxFont(10, wxMODERN, wxNORMAL, wxNORMAL, 0, 'Courier New'))

        EVT_LIST_ITEM_SELECTED(self, self.GetId(), self.OnItemSelected)
        EVT_LIST_ITEM_ACTIVATED(self, self.GetId(), self.OnItemActivated)

        self.attrcache = {}

    def OnItemSelected(self, event):
        self.currentItem = event.m_itemIndex

    def OnItemActivated(self, event):
        self.currentItem = event.m_itemIndex

    def getColumnText(self, index, col):
        item = self.GetItem(index, col)
        return item.GetText()

    #---------------------------------------------------
    # These methods are callbacks for implementing the
    # "virtualness" of the list...
    def OnGetItemText(self, item, col):
        if self.core:
            return self.core.memory.hexline(item<<4)[col]   #very inefficient here!
        else:
            return ''
        #return "Item %d, column %d" % (item, col)

    def OnGetItemImage(self, item):
        return 0

    def OnGetItemAttr(self, item):
        #attr = self.attr1
        attr = self.attrcache.get(item, None)
        if not attr:
            attr = wxListItemAttr()
            attr.SetFont(wxFont(10, wxMODERN, wxNORMAL, wxNORMAL, 0, 'Courier New'))
            attr.SetBackgroundColour('#%02x%02x%02x' % self.core.memory[item<<4].color)
            self.attrcache[item] = attr
        return attr


##################################################################
## memory viewer
##################################################################
class MemoryFrame(wxFrame, core.Observer):
    #ids for buttons
    TB_ADDRESS  = 2
    TB_GO       = 3
    
    M_EXIT      = 21

    def __init__(self, parent, id, core):
        """init the window."""
        # First, call the base class' __init__ method to create the frame
        wxFrame.__init__(self, parent, id, "Memory - MSP 430 Simulator", wxDefaultPosition, wxDefaultSize)
        self.core = core
        core.attach(self)       #register for updates
        #menu
        menu = wxMenu()
        menu.Append(self.M_EXIT, "Close")
        EVT_MENU(self, self.M_EXIT, self.OnMenuClose)
        menuBar = wxMenuBar()
        menuBar.Append(menu, "&Window");
        self.SetMenuBar(menuBar)
        
        #setup toolbar
        tb = self.tb = self.CreateToolBar(wxTB_HORIZONTAL|wxNO_BORDER|wxTB_FLAT)
        #a text field for a multiple steps
        self.address = wxTextCtrl(tb, self.TB_ADDRESS, "0")
        tb.AddControl(self.address)
        #a button for a multiple steps
        tb.AddControl(wxButton(tb, self.TB_GO, "Show"))
        EVT_BUTTON(self, self.TB_GO, self.OnGoClick)
        #sep----
        tb.AddSeparator()
        #create toolbar
        tb.Realize()
        # create a statusbar some game info
        
        #displays
        self.mem = MemView(self, core)
        
        #init a sizer for the window layout
        self.box = wxBoxSizer(wxVERTICAL)
        self.box.Add(self.mem, 1, wxEXPAND)
        self.box.Fit(self)                   #layout window
        #setup handler for window resize
        self.SetSizer(self.box)
        self.SetAutoLayout(1)
        EVT_CLOSE(self, self.OnCloseWindow)  #register window close handler
        EVT_SIZE(self, self.OnSizeWindow)
        EVT_TEXT_ENTER(self, self.TB_ADDRESS, self.OnGoClick)   #same as go button
        
        self.fastupdate = 0
        #self.update()       #init displays

    #observer pattern
    def update(self, *args):
        """process messages from the model."""
        if not self.fastupdate:
            #update memory in case RAM/peripherals are visible
            self.mem.Refresh()

    def OnMenuClose(self, event=None):
        self.Hide()

    def OnGoClick(self, event=None):
        s = self.address.GetValue()
        if s[0:2] == '0x':
            address = int(s,16)
        else:
            address = int(s)
        self.mem.EnsureVisible(address/16)
        
    def OnSizeWindow(self, event=None):
        self.update()       #init displays
        if event is not None: event.Skip()

    # This method is called when the CLOSE event is
    # sent to this window
    def OnCloseWindow(self, event):
        self.Hide()

##################################################################
## disassembling viewer
##################################################################
class DisFrame(wxFrame, core.Observer):
    #ids for buttons
    TB_ADDRESS  = 2
    TB_GO       = 3
    
    M_EXIT      = 21

    def __init__(self, parent, id, core):
        """init the window."""
        # First, call the base class' __init__ method to create the frame
        wxFrame.__init__(self, parent, id, "Disassembler - MSP 430 Simulator", wxDefaultPosition, wxDefaultSize)
        self.core = core
        core.attach(self)       #register for updates
        #menu
        menu = wxMenu()
        menu.Append(self.M_EXIT, "Close")
        EVT_MENU(self, self.M_EXIT, self.OnMenuClose)
        menuBar = wxMenuBar()
        menuBar.Append(menu, "&Window");
        self.SetMenuBar(menuBar)
        
        #setup toolbar
        tb = self.tb = self.CreateToolBar(wxTB_HORIZONTAL|wxNO_BORDER|wxTB_FLAT)
        #a text field for a multiple steps
        self.address = wxTextCtrl(tb, self.TB_ADDRESS, "0")
        tb.AddControl(self.address)
        #a button for a multiple steps
        tb.AddControl(wxButton(tb, self.TB_GO, "Show"))
        EVT_BUTTON(self, self.TB_GO, self.OnGoClick)
        #sep----
        tb.AddSeparator()
        #create toolbar
        tb.Realize()
        # create a statusbar some game info
        
        #displays
        self.dis = DisView(self, core)
        
        #init a sizer for the window layout
        self.box = wxBoxSizer(wxVERTICAL)
        self.box.Add(self.dis, 1, wxEXPAND)
        self.box.Fit(self)                   #layout window
        #setup handler for window resize
        self.SetSizer(self.box)
        self.SetAutoLayout(1)
        EVT_CLOSE(self, self.OnCloseWindow)  #register window close handler
        EVT_SIZE(self, self.OnSizeWindow)
        EVT_TEXT_ENTER(self, self.TB_ADDRESS, self.OnGoClick)   #same as go button
        
        self.fastupdate = 0
        #self.update()       #init displays

    #observer pattern
    def update(self, *args):
        """process messages from the model."""
        if not self.fastupdate:
            #update , mark PC
            self.dis.Refresh()

    def OnMenuClose(self, event=None):
        self.Hide()

    def OnGoClick(self, event=None):
        s = self.address.GetValue()
        if s[0:2] == '0x':
            address = int(s,16)
        else:
            address = int(s)
        self.dis.disasseble(address)
        #self.mem.EnsureVisible(address/16)
        
    def OnSizeWindow(self, event=None):
        self.update()       #init displays
        if event is not None: event.Skip()

    # This method is called when the CLOSE event is
    # sent to this window
    def OnCloseWindow(self, event):
        self.Hide()

##################################################################
## main view of cpu core
##################################################################
class CoreFrame(wxFrame, core.Observer):
    #ids for buttons
    TB_STEP = 1
    TB_COUNT = 2
    TB_MULTISTEP = 3
    
    M_EXIT      = 21
    M_OPEN      = 23
    M_NEW       = 24
    M_MEM       = 25
    M_DIS       = 26
    
    def __init__(self, parent, id):
        """init the window."""
        # First, call the base class' __init__ method to create the frame
        wxFrame.__init__(self, parent, id, "MSP 430 Simulator", wxDefaultPosition, wxDefaultSize)
        #menu
        filemenu = wxMenu()
        filemenu.Append(self.M_NEW, "New")
        filemenu.Append(self.M_OPEN, "Open...")
        filemenu.Append(self.M_EXIT, "Exit")
        EVT_MENU(self, self.M_NEW, self.OnMenuNew)
        EVT_MENU(self, self.M_OPEN, self.OnMenuOpen)
        EVT_MENU(self, self.M_EXIT, self.OnMenuExit)

        viewmenu = wxMenu()
        viewmenu.Append(self.M_MEM, "Memory")
        viewmenu.Append(self.M_DIS, "Disassembler")
        EVT_MENU(self, self.M_MEM, self.OnMenuMem)
        EVT_MENU(self, self.M_DIS, self.OnMenuDis)

        menuBar = wxMenuBar()
        menuBar.Append(filemenu, "&File");
        menuBar.Append(viewmenu, "&View");
        self.SetMenuBar(menuBar)
        
        #setup toolbar
        tb = self.tb = self.CreateToolBar(wxTB_HORIZONTAL|wxNO_BORDER|wxTB_FLAT)
        #a button for a step
        tb.AddControl(wxButton(tb, self.TB_STEP, "SingleStep"))
        EVT_BUTTON(self, self.TB_STEP, self.OnStepClick)
        #sep----
        tb.AddSeparator()
        #a text field for a multiple steps
        self.maxsteps = wxTextCtrl(tb, self.TB_COUNT, "100")
        tb.AddControl(self.maxsteps)
        #a button for a multiple steps
        tb.AddControl(wxButton(tb, self.TB_MULTISTEP, "MultiStep"))
        EVT_BUTTON(self, self.TB_MULTISTEP, self.OnMultiStepClick)
        #sep----
        tb.AddSeparator()
        #create toolbar
        tb.Realize()
        # create a statusbar some game info
        sb = self.CreateStatusBar(1)
        sb.SetStatusWidths([-1])
        #initilaize a timer for elapsed time updates in toolbar
        #self.timer = wxPyTimer(self.tick)
        #self.timer.Start(1000)          #1s steps
        #self.tick()                     #generate first timer event to display status
        
        #displays
        self.panel = wxPanel(self,-1)
        self.dis = DisView(self.panel)
        self.registers = wxTextCtrl(self.panel, 30,'', size=(100, 250), style=wxTE_MULTILINE|wxTE_RICH|wxTE_READONLY )

        self.log = wxTextCtrl(self, 30,'', size=(-1, 150), style=wxTE_MULTILINE)

##        sty = wxTextAttr(wxBLACK, wxWHITE,
##            wxFont(8, wxMODERN, wxNORMAL, wxNORMAL, 0, 'Courier New'))

        #create cpu core
        ##TODO: isolate this    ##$$$$$$$
        self.core = core.Core(self)
        self.core.memory.append(core.ExtendedPorts(self.log))
        self.core.memory.append(core.Flash(self.log))
        self.core.memory.append(core.RAM(self.log))
        self.core.memory.append(core.Multiplier(self.log))
        
        self.core.attach(self)     #register as observer
        self.dis.core = self.core

        self.hbox = wxBoxSizer(wxHORIZONTAL)
        self.hbox.Add(self.dis, 1, wxEXPAND)
        self.hbox.Add(self.registers, 0, wxALIGN_TOP)
        self.panel.SetSizer(self.hbox)
        self.panel.SetAutoLayout(1)
        self.hbox.Fit(self.panel)                   #layout window
        
        #init a sizer for the window layout
        self.box = wxBoxSizer(wxVERTICAL)
        self.box.Add(self.panel, 1, wxEXPAND)
        self.box.Add(self.log, 0, wxEXPAND)
        self.box.Fit(self)                   #layout window
        #setup handler for window resize
        self.SetSizer(self.box)
        self.SetAutoLayout(1)
        EVT_KEY_DOWN(self, self.OnKey)
        EVT_CLOSE(self, self.OnCloseWindow)  #register window close handler
        EVT_SIZE(self, self.OnSizeWindow)

        self.mem = None
        self.disframe = None

        self.loglines = []
        self.fastupdate = 0
        self.lastpath = '.'
        #self.update()       #init displays
        #self.OnScrollMem()  #init scollbar
        #self.disasseble(0)

    #observer pattern
    def update(self, *args):
        """process messages from the model."""
        if not self.fastupdate:
            regs = ''
            for r in self.core.R:
                regs += '%r\n' % r
            self.registers.SetValue(regs)
            self.dis.disasseble(self.core.PC.get(), lines = 20) #update lockahead
            #update text in statusbar
            self.SetStatusText('%r' % (args,), 0)
            self.log.SetValue(''.join(self.loglines))

    #for logger
    def write(self, s):
        #self.log.AppendText(s)
        self.loglines.append(s)
        self.loglines = self.loglines[-50:]
        #self.log.SetValue(s)
        #print s

    def OnMenuNew(self, event=None):
        self.core.reset()
        self.dis.Refresh()
        self.Refresh()
        
    def OnMenuOpen(self, event=None):
        dlg = wxFileDialog(self,
                "Choose a ihex file",
                ".",
                "",
                "Intel HEX (*.a43)|*.a43|TI Text(*.txt)|*.txt",
                wxOPEN
        )
        dlg.SetDirectory(self.lastpath)
        if dlg.ShowModal() == wxID_OK:
            self.lastpath = dlg.GetDirectory()
            self.core.memory.load(dlg.GetPath())
            self.core.PC.set(self.core.memory.get(0xfffe)) ##DEBUG !!!!!!!!!!!
            self.update()
        dlg.Destroy()

    def OnMenuExit(self, event=None):
        self.Destroy()

    def OnMenuMem(self, event=None):
        if self.mem is None:
            self.mem = MemoryFrame(self, -1, self.core)
        self.mem.Show()
        self.mem.SetFocus()

    def OnMenuDis(self, event=None):
        if self.disframe is None:
            self.disframe = DisFrame(self, -1, self.core)
        self.disframe.Show()
        self.disframe.SetFocus()

    #def tick(self):
    #    """show elapsed time in the right side of the statusbar."""

    #def OnToolClick(self, event):
    #    id = event.GetId()
    #    #if id == TB_NEW:
    #    #    self.run_bg(zent.zif.on)

    def OnStepClick(self, event=None):
        self.core.step()

    def OnMultiStepClick(self, event=None):
        steps = int(self.maxsteps.GetValue())
        self.fastupdate = 1
        try:
            for i in range(steps):
                self.core.step()
        finally:
            self.fastupdate = 0
            self.update()
        
    def OnSizeWindow(self, event=None):
        self.update()       #init displays
        if event is not None: event.Skip()

    # This method is called when the CLOSE event is
    # sent to this window
    def OnCloseWindow(self, event):
        self.Destroy()          #then exit

    def OnKey(self, event):
        code = event.GetKeyCode()
        #if code == WXK_BACK:
        print code

#application....
if __name__ == '__main__':
    # Every wxWindows application must have a class derived from wxApp
    class MyApp(wxApp):
        # wxWindows calls this method to initialize the application
        def OnInit(self):
            # Create an instance of our customized Frame class
            self.frame = CoreFrame(NULL, -1)
            self.frame.Show(true)
            # Tell wxWindows that this is our main window
            self.SetTopWindow(self.frame)
            # Return a success flag
            return true
    
    wxInitAllImageHandlers()    #init wx stuff
    app = MyApp(0)              #Create an instance of the application class
    app.MainLoop()              #Tell it to start processing events
