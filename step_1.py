# -*- coding: utf-8 -*-  
#coding=utf-8
import pymysql
import time
from warnings import filterwarnings
from progressive.bar import Bar
error_message=u"Error 'Unknown table 'fandb.t_error_maker'' on query. Default database: 'fandb'. Query: 'DROP TABLE `t_error_maker` /* generated by server */'"

def dec_progressive(func):
	def progess(*args, **kwargs):
		global i
		i += 100/9
		bar.cursor.restore()
		bar.draw(value=i)
		return func(*args, **kwargs)
	return progess

#创建数据库连接函数
@dec_progressive
def get_conn(host,port,user,password,db='performance_schema',charset='utf8'):
    return pymysql.connect(host=host, port=int(port), user=user,password=password,db=db,charset=charset)


#制造复制异常函数
@dec_progressive
def error_maker(host,port,user,password,db,charset):
	conn=get_conn(host=host, port=int(port), user=user,password=password,db=db,charset=charset)
	cursor = conn.cursor()
	cursor.execute("set session sql_log_bin=0;")
	cursor.execute("create table t_error_maker(id int)")
	cursor.execute("set session sql_log_bin=1")
	cursor.execute("drop table t_error_maker")
	cursor.close()
	conn.close()



#获取slave status
def get_slave_statue(conn,sql):
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    cursor.execute("show slave status;")
    result = cursor.fetchone()
    return result
    cursor.close()



#获取master status
@dec_progressive
def get_master_status(conn):
	cursor = conn.cursor(pymysql.cursors.DictCursor)
	cursor.execute("show master status;")
	result = cursor.fetchone()
	return result
	cursor.close()


#执行change master语句
@dec_progressive
def change_master(conn,change_string):
	cursor = conn.cursor()
	cursor.execute("stop slave;")
	cursor.execute(change_string)
	cursor.execute("start slave;")
	cursor.close()


#修复slave错误
@dec_progressive
def repair_slave(conn):
	cursor = conn.cursor()
	cursor.execute("set global sql_slave_skip_counter=1;")
	cursor.execute("start slave sql_thread;")
	cursor.close()	

#设置read only
@dec_progressive
def set_read_only(conn,switch):
	cursor = conn.cursor()
	if switch == 'on':
		cursor.execute("set global read_only=on;")
	elif switch == 'off':
		cursor.execute("set global read_only=off;")
	cursor.close()

#启停 sql_thread
@dec_progressive
def set_sql_thread(conn,switch):
	cursor = conn.cursor()
	if switch == 'off':
		cursor.execute("stop slave sql_thread;")
	elif switch == 'on':
		cursor.execute("start slave sql_thread;")
	cursor.close()

#判断 39 40 41是否都因为drop t_error_maker停止
@dec_progressive
def get_error_status():
	while True:
		Last_SQL_Error_39 = get_slave_statue(conn39,'show slave status;')['Last_SQL_Error']
		Last_SQL_Error_40 = get_slave_statue(conn40,'show slave status;')['Last_SQL_Error']
		Last_SQL_Error_41 = get_slave_statue(conn41,'show slave status;')['Last_SQL_Error']
		if Last_SQL_Error_39 == Last_SQL_Error_40 == Last_SQL_Error_41 == error_message:
			break
		else:
			time.sleep(1)

if __name__ == '__main__':
	MAX_VALUE = 100
	bar = Bar(max_value=MAX_VALUE, fallback=True)
	bar.cursor.clear_lines(2)
	bar.cursor.save()
	i=0

	#不显示MySQL的warning
	filterwarnings('ignore',category=pymysql.Warning)
	#连接3306 制造复制异常函数
	print(u"连接3306 制造复制异常函数")
	error_maker(host='172.16.65.36', port=3306, user='root',password='mysql',db='fandb',charset='utf8')
	conn39 = get_conn('10.0.1.39',3306,'root','mysql')
	conn40 = get_conn('10.0.1.40',3306,'root','mysql')
	conn41 = get_conn('10.0.1.41',3306,'root','mysql')

	#判断 39 40 41是否都因为drop t_error_maker停止
	print(u"判断 39 40 41是否都因为drop t_error_maker停止")
	get_error_status()

	#获取40 master status 以供39 41切换
	print(u"获取40 master status 以供39 41切换")
	master_status_40 = get_master_status(conn40)
	File_40,Position_40 = master_status_40['File'],master_status_40['Position']

	change_string = """
	change master to 
	master_host='10.0.1.40',
	master_port=3306,
	master_user='repl',
	master_password='repl',
	master_log_file='%s',
	master_log_pos=%d;
	""" % (File_40,Position_40)

	#39 41切换到40
	print(u"39,41切换到40")
	change_master(conn39,change_string)
	print(u"39切换到40成功")
	change_master(conn41,change_string)
	print(u"41切换到40成功")
	#修复40 slave
	print(u"修复40 slave")
	if i > 100:
		i = 100
	repair_slave(conn40)

	# conn35 = get_conn('172.16.65.35',3306,'root','mysql')
	# conn36 = get_conn('172.16.65.36',3306,'root','mysql')

	# #35 设置read only
	# set_read_only(conn35,switch='on')

	# #判断35 36 40 是否同步
	# while True:
	# 	res35 = get_slave_statue(conn35,'show master status;')
	# 	res36 = get_slave_statue(conn36,'show slave status;')
	# 	res40 = get_slave_statue(conn40,'show slave status;')
	# 	File_35,Position_35 = res35['File'],res35['Position']
	# 	File_36,Position_36 = res36['Relay_Master_Log_File'],res36['Exec_Master_Log_Pos']
	# 	File_40,Position_40 = res40['Relay_Master_Log_File'],res40['Exec_Master_Log_Pos']
	# 	if File_35 == File_36 == File_40 and Position_35 == Position_36 == Position_40:
	# 		break
	# 	else:
	# 		time.sleep(1)

	# #停40 sql_thread
	# set_sql_thread(conn40,switch='off')

	# #写接入36

	# #35 read_only=off
	# set_read_only(conn35,switch='off')

	# master_status_40 = get_master_status(conn40)
	# File_40,Position_40 = master_status_40['File'],master_status_40['Position']

	# change_string = """
	# change master to 
	# master_host='10.0.1.40',
	# master_port=3306,
	# master_user='repl',
	# master_password='repl',
	# master_log_file='%s',
	# master_log_pos=%d;
	# """ % (File_40,Position_40)

	# change_master(conn35,change_string)

	# #起40 sql_thread
	# set_sql_thread(conn40,switch='on')

	#bar.cursor.restore()
	#bar.draw(value=100)

