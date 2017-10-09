import cx_Oracle
import time

con = cx_Oracle.connect('xx/yy@zz')
cur = con.cursor()
v = cur.var(cx_Oracle.STRING)
while 1==1:
    cur.execute("""begin
                 :p_var := zxc_dbg.read(0);
               end;""", p_var = v )
    print(v.getvalue())
    time.sleep(0.1);
con.close()

