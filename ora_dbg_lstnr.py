import cx_Oracle
import time

class Lstnr():
    def __init__(self, connect_string, pipe):
        self.connect_string = connect_string
        self.pipe = pipe
    def listen(self):
        sql = """
  declare
        l_message varchar2(4000) := '';
        s varchar2(4000);
        l_status number;
        lf varchar2(2) := chr(10);
  begin
    while true loop
        l_status := dbms_pipe.receive_message('""" + self.pipe + """', 0);
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
        self.con = cx_Oracle.connect(self.connect_string)
        cur = self.con.cursor()
        cur.prepare(sql)
        v = cur.var(cx_Oracle.STRING)
        while True:
            cur.execute(None, p_var = v )
            if not v.getvalue() is None: print(v.getvalue(), end='')
            time.sleep(0.1)
        con.close()

if __name__ == "__main__":
    from optparse import OptionParser
    parser = OptionParser()
    parser.add_option("-c", "--connect", dest="connect", help="Oracle connect string")
    parser.add_option("-p", "--pipe", dest="pipe", help="Oracle pipe name")
    (options, args) = parser.parse_args()
    if not options.connect:
        parser.error("option -c (--connect) should be set")
    if not options.pipe:
        parser.error("option -p (--pipe) should be set")
    Lstnr(options.connect, options.pipe).listen()
