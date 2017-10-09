import cx_Oracle
from tkinter import *
from tkinter.scrolledtext import ScrolledText
from tkinter.messagebox import *
import threading, queue, time
import configparser

cnstNotConnected = 1
cnstConnected = 2
cnstListening = 3

class StatusBar(Frame):
    def __init__(self, parent):
        Frame.__init__(self, parent)
        self._lblConn = Label(self, text='', bd=2, relief=SUNKEN, width=15, anchor = W)
        self._lblConn.pack(side=RIGHT)
        self._lblAppState = Label(self, text='', bd=2, relief=SUNKEN, width=15, anchor = W)
        self._lblAppState.pack(side=RIGHT)
        self._lblBusy = Label(self, text='', bd=2, relief=SUNKEN, width=5, anchor = W)
        self._lblBusy.pack(side=LEFT)
        self._lblDBQuery = Label(self, text='', bd=2, relief=SUNKEN, width=8, anchor = W)
        self._lblDBQuery.pack(side=LEFT)
        self._gui_old_color = 'SystemButtonFace'
    def gui_wait(self):
        self._gui_old_color = self._lblBusy.cget('bg')
        self._lblBusy.config(text = 'Busy', bg = 'yellow')
        self.update()
    def gui_ready(self):
        self._lblBusy.config(text = '', bg = self._gui_old_color)
        self.update()
    def db_wait(self):
        self._lblDBQuery.config(text = 'DB wait...')
        self.update()
    def db_ready(self):
        self._lblDBQuery.config(text = '')
        self.update()
    def app_status(self, s):
        self._lblAppState.config(text = s)
        self.update()
    def conn_status(self, s):
        self._lblConn.config(text = s) 
        self.update()

class OraPipeViewer(Frame):
    def __init__(self, parent=None):
        Frame.__init__(self, parent)
        self.pack(side=TOP, fill=BOTH, expand=YES)
        self.dataQueue = queue.Queue()
        self.iniCtrls()
        self.con = None
        self.connectUser = ""
        self.connectPwd = ""
        self.connectServer = ""
        self.oraPipe = ""
        self.state = cnstNotConnected
        self.IsProducerWorking = False
        self.setCntrlState()
        self.bind("<Destroy>", self.onDestroy)
        self.LoadConfig()
    def iniCtrls(self):
        frmTop = Frame(self)
        frmTop.pack(side=TOP, fill=X)
        
        frmMiddle = Frame(self)
        frmMiddle.pack(fill=BOTH, expand=YES)

        frmBottom = Frame(self)
        frmBottom.pack(side=BOTTOM, fill=X)
        frmBottom.config(bd=2, relief=SUNKEN)

        self.status_bar = StatusBar(self)
        self.status_bar.pack(side=BOTTOM, fill=X)
        self.status_bar.config(bd=2, relief=SUNKEN)

        Label(frmTop, text='Oracle user:').pack(side=LEFT)
        self.entUser = Entry(frmTop, width=5)
        self.entUser.pack(side=LEFT)

        Label(frmTop, text='pwd:').pack(side=LEFT)
        self.entPwd = Entry(frmTop, width=5)
        self.entPwd.config(show="*")
        self.entPwd.pack(side=LEFT)

        Label(frmTop, text='Server:').pack(side=LEFT)
        self.entServer = Entry(frmTop, width=15)
        self.entServer.pack(side=LEFT)

        self.btnConnect = Button(frmTop, text='Connect',  command=self.onConnect)
        self.btnConnect.pack(side=LEFT, padx=5, pady=5)
        self.btnDisconnect = Button(frmTop, text='Disconnect',  command=self.onDisconnect)
        self.btnDisconnect.pack(side=LEFT, padx=5, pady=5)
        self.btnDisconnect.config(state=DISABLED)

        Label(frmTop, text='Pipe:').pack(side=LEFT)
        self.entPipe = Entry(frmTop, width=15)
        self.entPipe.pack(side=LEFT)

        self.btnStartListen = Button(frmTop, text='Start listen',  command=self.onStartListen)
        self.btnStartListen.pack(side=LEFT, padx=5, pady=5)
        self.btnStartListen.config(state=DISABLED)
        self.btnStopListen = Button(frmTop, text='Stop listen',  command=self.onStopListen)
        self.btnStopListen.pack(side=LEFT, padx=5, pady=5)
        self.btnStopListen.config(state=DISABLED)

        Button(frmTop, text='Clear',  command=self.onClear).pack(side=RIGHT, padx=5, pady=5)
        
        self.st = ScrolledText(frmMiddle, font=('courier', 9, 'normal'))
        self.st.pack(side=TOP, fill=BOTH, expand=YES)
        
    def setCntrlState(self):
        if self.state == cnstNotConnected:
            self.btnConnect.config(state=NORMAL)
            self.btnDisconnect.config(state=DISABLED)
            self.entPipe.config(state=DISABLED)
            self.btnStartListen.config(state=DISABLED)
            self.btnStopListen.config(state=DISABLED)
            self.status_bar.app_status('Not connected')
            self.status_bar.conn_status('')
        elif self.state == cnstConnected:
            self.btnConnect.config(state=DISABLED)
            self.btnDisconnect.config(state=NORMAL)
            self.entPipe.config(state=NORMAL)
            self.btnStartListen.config(state=NORMAL)
            self.btnStopListen.config(state=DISABLED)
            self.status_bar.app_status('Connected')
            self.status_bar.conn_status(self.connectUser + "@" + self.connectServer)
        elif self.state == cnstListening:
            self.btnConnect.config(state=DISABLED)
            self.btnDisconnect.config(state=NORMAL)
            self.entPipe.config(state=DISABLED)
            self.btnStartListen.config(state=DISABLED)
            self.btnStopListen.config(state=NORMAL)
            self.status_bar.app_status('Listening')
            self.status_bar.conn_status(self.connectUser + "@" + self.connectServer)
        self.update()
    def gui_wait(self):
        self.config(cursor = 'circle')
        self.status_bar.gui_wait()
    def gui_ready(self):
        self.config(cursor = 'arrow')
        self.status_bar.gui_ready()
    def onConnect(self):
        if self.state != cnstNotConnected:
            return
        if self.entUser.get() == "":
            showwarning("No user", "Fill the user name, please!")
            return
        if self.entPwd.get() == "":
            showwarning("No pwd", "Fill the password, please!")
            return
        if self.entServer.get() == "":
            showwarning("No server", "Fill the server, please!")
            return

        self.gui_wait()

        if not self.con is None:
            self.con.close()

        try:
            self.con = cx_Oracle.connect(self.entUser.get() + '/' + self.entPwd.get() + '@' + self.entServer.get())
        except cx_Oracle.DatabaseError:
            showwarning("Not connected", str(sys.exc_info()[1]))
            self.gui_ready()
            return

        self.state = cnstConnected
        self.connectUser = self.entUser.get()
        self.connectPwd = self.entPwd.get()
        self.connectServer = self.entServer.get()
        self.oraPipe = self.entPipe.get()
        self.setCntrlState()
        self.SaveConfig()
        self.gui_ready()
    def SaveConfig(self):
        config = configparser.RawConfigParser()
        config.add_section('Params')
        config.set('Params', 'User', self.connectUser)
        config.set('Params', 'Server', self.connectServer)
        config.set('Params', 'Pipe', self.oraPipe)
        with open('orapipelstnr.cfg', 'w') as configfile:
            config.write(configfile)
    def LoadConfig(self):
        config = configparser.RawConfigParser()
        config.read('orapipelstnr.cfg')
        try:
            self.entUser.insert(0, config.get('Params', 'User'))
            self.entServer.insert(0, config.get('Params', 'Server'))

            t = self.entPipe.cget('state')
            self.entPipe.config(state=NORMAL)
            self.entPipe.insert(0, config.get('Params', 'Pipe'))
            self.entPipe.config(state=t)

        except (configparser.NoSectionError, configparser.NoOptionError):
            pass
    def onDisconnect(self):
        if self.state == cnstNotConnected:
            return
        self.gui_wait()
        self.state = cnstNotConnected
        while self.IsProducerWorking: # Дождёмся завершения работы нити
            time.sleep(0.1)
        if not self.con is None:
            try:
                self.con.close()
            except (cx_Oracle.OperationalError, cx_Oracle.DatabaseError): # Если на коннекте активный запрос, вываливается с исключением
                pass
            self.con = None
        self.connectUser = ""
        self.connectPwd = ""
        self.connectServer = ""
        self.oraPipe = ""
        self.setCntrlState()
        self.consumer(perEvent = 10)
        self.gui_ready()
    def onClear(self):
        self.st.delete('1.0', END)
    def onStartListen(self):
        if self.state == cnstNotConnected or self.state == cnstListening:
            return
        if self.entPipe.get() == "":
            showwarning("No pipe name", "Fill the oracle pipe name, please!")
            return
        self.oraPipe = self.entPipe.get()
        self.SaveConfig()
        self.gui_wait()
        self.state = cnstListening
        self.setCntrlState()
        threading.Thread(target=self.producer).start()
        self.consumer()
        self.gui_ready()
    def onStopListen(self):
        if self.state != cnstListening:
            return
        self.gui_wait()
        self.state = cnstConnected
        while self.IsProducerWorking: # Дождёмся завершения работы нити
            time.sleep(0.1)
        self.setCntrlState()
        self.consumer(perEvent = 10)
        self.gui_ready()
    def add_msg(self, msg):
        self.st.insert(END, msg)
        self.st.see('end')
    def consumer(self, delayMsecs = 100, perEvent = 1):
        for i in range(perEvent):
            try:
                (callback, args) = self.dataQueue.get(block = False)
            except queue.Empty:
                pass
            else:
                #if self.state == cnstListening:
                    #print(callback)
                    #print(args)
                callback(*args)
        if self.state == cnstListening or self.IsProducerWorking:
            self.after(100, lambda: self.consumer(delayMsecs, perEvent)) 

    def producer(self):
        sql = """
  declare
        l_message varchar2(4000) := '';
        s varchar2(4000);
        l_status number;
        lf varchar2(2) := chr(10);
  begin
    while true loop
        l_status := dbms_pipe.receive_message('""" + self.oraPipe + """', 0);
        exit when l_status != 0;
        dbms_pipe.unpack_message(s);
        if length(s) + length(l_message) > 4000 then
            raise_application_error(-20005, 'The debug message is too large!');
        end if;
        l_message := l_message || s || lf;
        exit when length(l_message) > 3500;
        lf := chr(10);
    end loop;
    :p_var := l_message;
  end;
"""
        self.IsProducerWorking = True

        # Parsing
        self.dataQueue.put((self.status_bar.db_wait, []))
        cur = self.con.cursor()
        v = cur.var(cx_Oracle.STRING)
        try:
            cur.prepare(sql)
        except cx_Oracle.DatabaseError:
            s = str(sys.exc_info()[1])
            self.dataQueue.put((self.add_msg, (s,)))
        else:
            self.dataQueue.put((self.status_bar.db_ready, []))

            # Fetching
            while self.state == cnstListening:
                self.dataQueue.put((self.status_bar.db_wait, []))
                try:
                    cur.execute(None, p_var = v)
                    s = v.getvalue()
                except cx_Oracle.DatabaseError:
                    s = str(sys.exc_info()[1])
                self.dataQueue.put((self.status_bar.db_ready, []))
                if not s is None:
                    self.dataQueue.put((self.add_msg, (s,)))
                time.sleep(1)
        
        self.dataQueue.put((self.status_bar.db_ready, []))
        self.IsProducerWorking = False
    def onDestroy(self, event):
        self.state = cnstNotConnected

if __name__ == '__main__':
    root = Tk()
    root.title("Oracle pipe listener")
    OraPipeViewer(root)
    root.mainloop()
