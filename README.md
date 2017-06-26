# auto_failover

### 主从切换案例

M为主库,read write
S\* 为从库,read only
现在要对M进行硬件维护,提升S1为主库,接管业务读写. M维护完成后作为从库,如下图

![image](https://github.com/Fanduzi/auto_failover/blob/master/image/Snip20170626_32.png)

首先可以进行如下切换 (A) 

![image](https://github.com/Fanduzi/auto_failover/blob/master/image/Snip20170626_33.png)

再进行如下切换(B)

![image](https://github.com/Fanduzi/auto_failover/blob/master/image/Snip20170626_34.png)

#### A切换步骤
首先在S1制造"错误"
```
set session sql_log_bin=0;
create table t_error_maker(id int);
set session sql_log_bin=1;
drop table t_error_maker;
```
通过在session级别关闭写入binlog,建表,开启写入binlog,删表 制造异常, 当S11 S12 S13都执行到drop语句时,会报错停止sql_thread.
通过这种方式,可以让它们停止在同一个位置.
S12
```
show master status 获取File Position
```
S11 S13 
```
stop slave;
change master到S12上
start slave;
```
S12
```
set global sql_slave_skip_counter=1;
start slave sql_thread;
```

#### B切换步骤
M 停止业务写操作
```
set global read_only=on; 此时只有super权限用户能写入
set global super_read_only=on;禁止super权限用户写
#这里没有通过修改用户密码的方式是因为修改用户密码对已经连接上来的用户无效
```
等M S1 S12 跑一致后(File Position相同) 停S12 sql_thread, 将业务写入操作接入S1
最后M
```
set global read_only=off;
set global super_read_only=off;
change master 到S12
start slave
```
S12
```
start slave sql_thread;
```

以上步骤通过脚本完成的话,可以做到对业务造成很小的影响
注释掉了B步骤,因为需要配合切换业务写入操作
