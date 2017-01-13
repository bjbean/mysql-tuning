#!/usr/local/bin/python
import datetime
import getopt
import sys
import pprint
from warnings import filterwarnings
import MySQLdb
import ConfigParser
import sqlparse
import string
from sqlparse.sql import IdentifierList, Identifier
from sqlparse.tokens import Keyword, DML
from prettytable import PrettyTable

filterwarnings('ignore', category = MySQLdb.Warning)

SYS_PARM_FILTER = (
    'BINLOG_CACHE_SIZE',
    'BULK_INSERT_BUFFER_SIZE',
    'HAVE_PARTITION_ENGINE',
    'HAVE_QUERY_CACHE',
    'INTERACTIVE_TIMEOUT',
    'JOIN_BUFFER_SIZE',
    'KEY_BUFFER_SIZE',
    'KEY_CACHE_AGE_THRESHOLD',
    'KEY_CACHE_BLOCK_SIZE',
    'KEY_CACHE_DIVISION_LIMIT',
    'LARGE_PAGES',
    'LOCKED_IN_MEMORY',
    'LONG_QUERY_TIME',
    'MAX_ALLOWED_PACKET',
    'MAX_BINLOG_CACHE_SIZE',
    'MAX_BINLOG_SIZE',
    'MAX_CONNECT_ERRORS',
    'MAX_CONNECTIONS',
    'MAX_JOIN_SIZE',
    'MAX_LENGTH_FOR_SORT_DATA',
    'MAX_SEEKS_FOR_KEY',
    'MAX_SORT_LENGTH',
    'MAX_TMP_TABLES',
    'MAX_USER_CONNECTIONS',
    'OPTIMIZER_PRUNE_LEVEL',
    'OPTIMIZER_SEARCH_DEPTH',
    'QUERY_CACHE_SIZE',
    'QUERY_CACHE_TYPE',
    'QUERY_PREALLOC_SIZE',
    'RANGE_ALLOC_BLOCK_SIZE',
    'READ_BUFFER_SIZE',
    'READ_RND_BUFFER_SIZE',
    'SORT_BUFFER_SIZE',
    'SQL_MODE',
    'TABLE_CACHE',
    'THREAD_CACHE_SIZE',
    'TMP_TABLE_SIZE',
    'WAIT_TIMEOUT'
) 

def print_table(p_title_list,p_data_list,p_align=[]):
    x = PrettyTable(p_title_list)
    x.padding_width = 1
    for i in range(0,len(p_align)): 
        if p_align[i] == "l":
            x.align[p_title_list[i]] = "l"
        elif p_align[i] == "r":
            x.align[p_title_list[i]] = "r"
        else:
            pass
    
    for rec in p_data_list:
        if type(rec)!='list':
            rec = list(rec)            
        x.add_row(rec)
    print x

def is_subselect(parsed):
    if not parsed.is_group():
        return False
    for item in parsed.tokens:
        if item.ttype is DML and item.value.upper() == 'SELECT':
            return True
    return False

def extract_from_part(parsed):
    from_seen = False
    for item in parsed.tokens:
        #print item.ttype,item.value
        if from_seen:
            if is_subselect(item):
                for x in extract_from_part(item):
                    yield x
            elif item.ttype is Keyword:
                raise StopIteration
            else:
                yield item
        elif item.ttype is Keyword and item.value.upper() == 'FROM':
            from_seen = True

def extract_table_identifiers(token_stream):
    for item in token_stream:
        if isinstance(item, IdentifierList):
            for identifier in item.get_identifiers():
                yield identifier.get_real_name()
        elif isinstance(item, Identifier):
            yield item.get_real_name()
        # It's a bug to check for Keyword here, but in the example
        # above some tables names are identified as keywords...
        elif item.ttype is Keyword:
            yield item.value

def extract_tables(p_sqltext):
    stream = extract_from_part(sqlparse.parse(p_sqltext)[0])
    return list(extract_table_identifiers(stream))

def f_find_in_list(myList,value):
    try: 
        for v in range(0,len(myList)): 
            if value==myList[v]: 
                return 1
        return 0
    except: 
        return 0

def f_get_parm(p_dbinfo):
    conn = MySQLdb.connect(host=p_dbinfo[0], port=string.atoi(p_dbinfo[1]),user=p_dbinfo[2], passwd=p_dbinfo[3],db=p_dbinfo[4])
    cursor = conn.cursor()
    cursor.execute("select lower(variable_name),variable_value from INFORMATION_SCHEMA.GLOBAL_VARIABLES where upper(variable_name) in ('"+"','".join(list(SYS_PARM_FILTER))+"') order by variable_name")
    records = cursor.fetchall()
    cursor.close()
    conn.close()
    return records

def f_print_parm(p_parm_result):
    print "\033[1;31;40m%s\033[0m" % "===== SYSTEM PARAMETER ====="
    v_data = []
    for i in range(0,len(p_parm_result)):
        if 'size' in p_parm_result[i][0]:
            if string.atoi(p_parm_result[i][1])>=1024*1024*1024:
                v_data.append([p_parm_result[i][0],str(round(string.atoi(p_parm_result[i][1])/1024/1024/1024,2))+' G'])
            elif string.atoi(p_parm_result[i][1])>=1024*1024:
                v_data.append([p_parm_result[i][0],str(round(string.atoi(p_parm_result[i][1])/1024/1024,2))+' M'])
            elif string.atoi(p_parm_result[i][1])>=1024:
                v_data.append([p_parm_result[i][0],str(round(string.atoi(p_parm_result[i][1])/1024,2))+' K'])
            else:
                v_data.append([p_parm_result[i][0],p_parm_result[i][1]+' B'])
        else:
            pass
    print_table(['parameter_name','value'],v_data,['l','r'])
    print

def f_get_optimizer_switch(p_dbinfo):
    conn = MySQLdb.connect(host=p_dbinfo[0], port=string.atoi(p_dbinfo[1]),user=p_dbinfo[2], passwd=p_dbinfo[3],db=p_dbinfo[4])
    cursor = conn.cursor()
    cursor.execute("select variable_value from INFORMATION_SCHEMA.GLOBAL_VARIABLES where upper(variable_name)='OPTIMIZER_SWITCH'")
    records = cursor.fetchall()   
    cursor.close()
    conn.close()
    result = []
    for o in str(records[0][0]).split(','):
        result.append([o.split('=')[0],o.split('=')[1]])
    return result

def f_print_optimizer_switch(p_optimizer_switch_result):
    print "\033[1;31;40m%s\033[0m" % "===== OPTIMIZER SWITCH ====="
    print_table(['switch_name','value'],p_optimizer_switch_result,['l','r'])
    print

def f_exec_sql(p_dbinfo,p_sqltext,p_option):
    results={}
    conn = MySQLdb.connect(host=p_dbinfo[0], port=string.atoi(p_dbinfo[1]),user=p_dbinfo[2], passwd=p_dbinfo[3],db=p_dbinfo[4])
    cursor = conn.cursor()

    if f_find_in_list(p_option,'PROFILING'):
        cursor.execute("set profiling=1")
        cursor.execute("select ifnull(max(query_id),0) from INFORMATION_SCHEMA.PROFILING")
        records = cursor.fetchall()
        query_id=records[0][0] +2   #skip next sql

    if f_find_in_list(p_option,'STATUS'):
        #cursor.execute("select concat(upper(left(variable_name,1)),substring(lower(variable_name),2,(length(variable_name)-1))) var_name,variable_value var_value from INFORMATION_SCHEMA.SESSION_STATUS where variable_name in('"+"','".join(tuple(SES_STATUS_ITEM))+"') order by 1")
        cursor.execute("select concat(upper(left(variable_name,1)),substring(lower(variable_name),2,(length(variable_name)-1))) var_name,variable_value var_value from INFORMATION_SCHEMA.SESSION_STATUS order by 1")
        records = cursor.fetchall()
        results['BEFORE_STATUS']=dict(records)

    cursor.execute(p_sqltext)

    if f_find_in_list(p_option,'STATUS'):
        cursor.execute("select concat(upper(left(variable_name,1)),substring(lower(variable_name),2,(length(variable_name)-1))) var_name,variable_value var_value from INFORMATION_SCHEMA.SESSION_STATUS order by 1")
        records = cursor.fetchall()
        results['AFTER_STATUS']=dict(records)

    if f_find_in_list(p_option,'PROFILING'):
        cursor.execute("select STATE,DURATION,CPU_USER,CPU_SYSTEM,BLOCK_OPS_IN,BLOCK_OPS_OUT ,MESSAGES_SENT ,MESSAGES_RECEIVED ,PAGE_FAULTS_MAJOR ,PAGE_FAULTS_MINOR ,SWAPS from INFORMATION_SCHEMA.PROFILING where query_id="+str(query_id)+" order by seq")
        records = cursor.fetchall()
        results['PROFILING_DETAIL']=records

        cursor.execute("SELECT STATE,SUM(DURATION) AS Total_R,ROUND(100*SUM(DURATION)/(SELECT SUM(DURATION) FROM INFORMATION_SCHEMA.PROFILING WHERE QUERY_ID="+str(query_id)+"),2) AS Pct_R,COUNT(*) AS Calls,SUM(DURATION)/COUNT(*) AS R_Call FROM INFORMATION_SCHEMA.PROFILING WHERE QUERY_ID="+str(query_id)+" GROUP BY STATE ORDER BY Total_R DESC")
        records = cursor.fetchall()
        results['PROFILING_SUMMARY']=records

    cursor.close()
    conn.close()
    return results

def f_calc_status(p_before_status,p_after_status):
    results = []
    for key in sorted(p_before_status.keys()):
        if p_before_status[key]<>p_after_status[key]:
            results.append([key,p_before_status[key],p_after_status[key],str(float(p_after_status[key])-float(p_before_status[key]))])
    return results

def f_print_status(p_status_data):
    print "\033[1;31;40m%s\033[0m" % "===== SESSION STATUS (DIFFERENT) ====="
    print_table(['status_name','before','after','diff'],p_status_data,['l','r','r','r'])
    print

def f_print_time(p_starttime,p_endtime):
    print "\033[1;31;40m%s\033[0m" % "===== EXECUTE TIME ====="
    print timediff(p_starttime,p_endtime)
    print

def f_print_profiling(p_profiling_detail,p_profiling_summary):
    print "\033[1;31;40m%s\033[0m" % "===== SQL PROFILING(DETAIL)====="
    print_table(['state','duration','cpu_user','cpu_sys','bk_in','bk_out','msg_s','msg_r','p_f_ma','p_f_mi','swaps'],p_profiling_detail,['l','r','r','r','r','r','r','r','r','r','r'])
    print 'bk_in:   block_ops_in'
    print 'bk_out:  block_ops_out'
    print 'msg_s:   message sent'
    print 'msg_r:   message received'
    print 'p_f_ma:  page_faults_major'
    print 'p_f_mi:  page_faults_minor'
    print

    print "\033[1;31;40m%s\033[0m" % "===== SQL PROFILING(SUMMARY)====="
    print_table(['state','total_r','pct_r','calls','r/call'],p_profiling_summary,['l','r','r','r','r'])    
    print

def f_get_sqlplan(p_dbinfo,p_sqltext):
    results={}

    db = MySQLdb.connect(host=p_dbinfo[0], port=string.atoi(p_dbinfo[1]),user=p_dbinfo[2], passwd=p_dbinfo[3],db=p_dbinfo[4])
    cursor = db.cursor()
    cursor.execute("explain extended "+p_sqltext)
    records = cursor.fetchall()
    results['SQLPLAN']=records
    cursor.execute("show warnings")
    records = cursor.fetchall()
    results['WARNING']=records
    cursor.close()
    db.close()
    return results

def f_null(p_value):
    if not p_value:
        return ''

def f_print_sqlplan(p_sqlplan,p_warning,p_mysql_version):
    plan_title=('id','select_type','table','type','possible_keys','key','key_len','ref','rows','filtered','Extra')

    print "\033[1;31;40m%s\033[0m" % "===== SQL PLAN ====="
    
    if p_mysql_version.split('.')[1] == '7':  #5.7
        print_table(['id','select_type','table','partitions','type','possible_keys','key','key_len','ref','rows','filtered','Extra'],p_sqlplan,['r','l','l','l','l','l','l','l','l','r','r','l'])
    else:
        print_table(['id','select_type','table','type','possible_keys','key','key_len','ref','rows','filtered','Extra'],p_sqlplan,['r','l','l','l','l','l','l','l','r','r','l'])
    print

    print "\033[1;31;40m%s\033[0m" % "===== OPTIMIZER REWRITE SQL ====="
    for row in p_warning:
        print sqlparse.format(row[2],reindent=True, keyword_case='upper',strip_comments=True)
    print

def f_get_table(p_dbinfo,p_sqltext):
    r_tables=[]
    db = MySQLdb.connect(host=p_dbinfo[0], port=string.atoi(p_dbinfo[1]),user=p_dbinfo[2], passwd=p_dbinfo[3],db=p_dbinfo[4])
    cursor = db.cursor()
    cursor.execute("explain "+p_sqltext)
    rows = cursor.fetchall ()
    for row in rows:
        table_name = row[2]
        if '<' in table_name:
            continue
        if len(r_tables)==0:
            r_tables.append(table_name)
        elif f_find_in_list(r_tables,table_name) == -1:
            r_tables.append(table_name)
    cursor.close()
    db.close()
    return r_tables

def f_get_tableinfo(p_dbinfo,p_tablename):
    db = MySQLdb.connect(host=p_dbinfo[0], port=string.atoi(p_dbinfo[1]),user=p_dbinfo[2], passwd=p_dbinfo[3],db=p_dbinfo[4])
    cursor = db.cursor()
    #cursor.execute("select table_name,engine,row_format as format,table_rows,avg_row_length as avg_row,round((data_length+index_length)/1024/1024,2) as total_mb,round((data_length)/1024/1024,2) as data_mb,round((index_length)/1024/1024,2) as index_mb from information_schema.tables where table_schema='"+p_dbinfo[4]+"' and table_name='"+p_tablename+"'")
    cursor.execute("select a.table_name,a.engine,a.row_format as format,a.table_rows,a.avg_row_length as avg_row,round((a.data_length+a.index_length)/1024/1024,2) as total_mb,round((a.data_length)/1024/1024,2) as data_mb,round((a.index_length)/1024/1024,2) as index_mb,a.create_time,b.last_update last_analyzed from information_schema.tables a ,mysql.innodb_table_stats b where a.table_schema=b.database_name and a.table_name=b.table_name and a.table_schema='"+p_dbinfo[4]+"' and a.table_name='"+p_tablename+"'")
    records = cursor.fetchall ()
    cursor.close()
    db.close()
    return records

def f_print_tableinfo(p_table_stat):
    print_table(['table_name','engine','format','table_rows','avg_row','total_mb','data_mb','index_mb','create_time','last_analyzed'],p_table_stat,['l','l','l','r','r','r','r','r','c','c'])

def f_get_indexinfo(p_dbinfo,p_tablename):
    db = MySQLdb.connect(host=p_dbinfo[0], port=string.atoi(p_dbinfo[1]),user=p_dbinfo[2], passwd=p_dbinfo[3],db=p_dbinfo[4])
    cursor = db.cursor()
    cursor.execute("select index_name,non_unique,seq_in_index,column_name,collation,cardinality,nullable,index_type from information_schema.statistics where table_schema='"+p_dbinfo[4]+"' and table_name='"+p_tablename+"' order by 1,3")
    records = cursor.fetchall ()
    cursor.close()
    db.close()
    return records

def f_print_indexinfo(p_index_info):
    if len(p_index_info)>0:
        print_table(['index_name','non_unique','seq_in_index','column_name','collation','cardinality','nullable','index_type'],p_index_info,['l','r','r','l','','r','r','l'])

def f_get_indexstat(p_dbinfo,p_tablename):
    db = MySQLdb.connect(host=p_dbinfo[0], port=string.atoi(p_dbinfo[1]),user=p_dbinfo[2], passwd=p_dbinfo[3],db=p_dbinfo[4])
    cursor = db.cursor()
    cursor.execute("select index_name,last_update last_analyzed,stat_name,stat_value,sample_size,stat_description from mysql.innodb_index_stats a where database_name='"+p_dbinfo[4]+"' and table_name='"+p_tablename+"' order by index_name,stat_name")
    records = cursor.fetchall ()
    cursor.close()
    db.close()
    return records

def f_print_indexstat(p_index_stat):
    if len(p_index_stat)>0:
        print_table(['index_name','last_analyzed','stat_name','stat_value','sample_size','stat_description'],p_index_stat,['l','c','l','r','r','l'])

def f_get_mysql_version(p_dbinfo):    
    db = MySQLdb.connect(host=p_dbinfo[0], port=string.atoi(p_dbinfo[1]),user=p_dbinfo[2], passwd=p_dbinfo[3],db=p_dbinfo[4])
    cursor = db.cursor()
    cursor.execute("select @@version")
    records = cursor.fetchall ()
    cursor.close()
    db.close()
    return records[0][0]

def f_print_title(p_dbinfo,p_mysql_version,p_sqltext):
    print
    print '*'*100
    print '*','MySQL SQL Tuning Tools v2.0 (by hanfeng)'.center(96),'*'
    print '*'*100
    print 

    print "\033[1;31;40m%s\033[0m" % "===== BASIC INFORMATION ====="
    print_table(['server_ip','server_port','user_name','db_name','db_version'],[[p_dbinfo[0],p_dbinfo[1],p_dbinfo[2],p_dbinfo[4],p_mysql_version]])
    print

    print "\033[1;31;40m%s\033[0m" % "===== ORIGINAL SQL TEXT ====="
    print sqlparse.format(p_sqltext,reindent=True, keyword_case='upper')
    print

def timediff(timestart, timestop):
        t  = (timestop-timestart)
        time_day = t.days
        s_time = t.seconds
        ms_time = t.microseconds / 1000000
        usedtime = int(s_time + ms_time)
        time_hour = usedtime / 60 / 60
        time_minute = (usedtime - time_hour * 3600 ) / 60
        time_second =  usedtime - time_hour * 3600 - time_minute * 60
        time_micsecond = (t.microseconds - t.microseconds / 1000000) / 1000

        retstr = "%d day %d hour %d minute %d second %d microsecond "  %(time_day, time_hour, time_minute, time_second, time_micsecond)
        return retstr

if __name__=="__main__":
    dbinfo=["","","","",""]  #dbhost,dbport,dbuser,dbpwd,dbname
    sqltext=""
    option=[]
    config_file=""
    mysql_version=""

    opts, args = getopt.getopt(sys.argv[1:], "p:s:")
    for o,v in opts:
        if o == "-p":
            config_file = v
        elif o == "-s":
            sqltext = v
    
    config = ConfigParser.ConfigParser()
    config.readfp(open(config_file,"rb"))
    dbinfo[0] = config.get("database","server_ip")
    dbinfo[1] = config.get("database","server_port")
    dbinfo[2] = config.get("database","db_user")
    dbinfo[3] = config.get("database","db_pwd")
    dbinfo[4] = config.get("database","db_name")

    mysql_version = f_get_mysql_version(dbinfo).split('-')[0]

    f_print_title(dbinfo,mysql_version,sqltext)
    
    if config.get("option","sys_parm")=='ON':
        parm_result = f_get_parm(dbinfo)
        optimizer_switch_result = f_get_optimizer_switch(dbinfo)
        f_print_parm(parm_result)
        f_print_optimizer_switch(optimizer_switch_result)
    
    if config.get("option","sql_plan")=='ON':
        sqlplan_result = f_get_sqlplan(dbinfo,sqltext)
        f_print_sqlplan(sqlplan_result['SQLPLAN'],sqlplan_result['WARNING'],mysql_version)

    if config.get("option","obj_stat")=='ON':
        print "\033[1;31;40m%s\033[0m" % "===== OBJECT STATISTICS ====="
        for table_name in extract_tables(sqltext):
            f_print_tableinfo(f_get_tableinfo(dbinfo,table_name))
            f_print_indexinfo(f_get_indexinfo(dbinfo,table_name))
            f_print_indexstat(f_get_indexstat(dbinfo,table_name))
        print
    
    if config.get("option","ses_status")=='ON':
        option.append('STATUS')

    if config.get("option","sql_profile")=='ON':
        option.append('PROFILING')

    if config.get("option","ses_status")=='ON' or config.get("option","sql_profile")=='ON':
        starttime = datetime.datetime.now()
        exec_result = f_exec_sql(dbinfo,sqltext,option)
        endtime = datetime.datetime.now()

        if config.get("option","ses_status")=='ON':
            f_print_status(f_calc_status(exec_result['BEFORE_STATUS'],exec_result['AFTER_STATUS']))

        if config.get("option","sql_profile")=='ON':
            f_print_profiling(exec_result['PROFILING_DETAIL'],exec_result['PROFILING_SUMMARY'])

        f_print_time(starttime,endtime)