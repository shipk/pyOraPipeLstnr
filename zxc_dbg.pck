create or replace package zxc_dbg as
  procedure write(p_message varchar2, timeout in number := 0);
  procedure read(timeout in number :=0);
  function read(timeout in number :=0) return varchar2;
end zxc_dbg;
/
create or replace package body zxc_dbg as

    pipename varchar2(30) := 'zxc_dbg';
    maxpipesize number := 1024;

    procedure write(p_message varchar2, timeout in number := 0) is
        l_status  number;
    begin
        dbms_pipe.pack_message(to_char(systimestamp,'yymmdd hh24:mi:ss.FF2') || ' : ' || p_message);
        l_status := dbms_pipe.send_message(pipename, timeout, maxpipesize);
        if l_status != 0 then
            raise_application_error(-20005, 'error sending message: ' || l_status);
        end if;
    end write;

    procedure read(timeout in number :=0) is
        l_message varchar2(8192);
        l_status number;
    begin
        dbms_output.enable(1000000);
        dbms_output.put_line('-- debug messages ------------------------------------');
        loop
            l_status := dbms_pipe.receive_message(pipename, timeout);
            exit when l_status != 0;
            loop
                l_status := dbms_pipe.next_item_type;
                exit when l_status = 0;
                if l_status = 9 then
                    dbms_pipe.unpack_message(l_message);
                    dbms_output.put_line(l_message);
                else
                    dbms_output.put_line('!!! unsupported message type ' || l_status);
                    begin
                        dbms_pipe.unpack_message(l_message);
                        dbms_output.put_line(l_message);
                    exception
                    when others then
                        null;
                    end;
                end if;
            end loop;
        end loop;
        dbms_output.put_line ('-- end of debug messages ----------------------------');
    end read;

  function read(timeout in number :=0) return varchar2 is
        l_message varchar2(4000) := '';
        s varchar2(4000);
        l_status number;
        lf varchar2(2) := chr(10);
  begin
    while true loop
        l_status := dbms_pipe.receive_message(pipename, timeout);
        exit when l_status != 0;
        dbms_pipe.unpack_message(s);
        if length(s) + length(l_message) > 4000 then
            raise_application_error(-20005, 'The debug message is too large!');
        end if;
        l_message := l_message || s || lf;
        exit when length(l_message) > 3500;
        lf := chr(10);
    end loop;
    return l_message;
  end;
end zxc_dbg;
/
