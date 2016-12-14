
### 1.准备条件
#### 模块
  -  模块 - MySQLDB  
  -  模块 - sqlparse  
  -  模块 - prettytable    
  
#### 版本  
  Python版本 >= 2.6 (3.x版本没测试)    
#### 授权    
  grant all on *.* to testuser@'localhost' identified by 'testpwd';    
#### 参数    
  在5.7版本中，需要打开show_compatibility_56参数。    
  set global show_compatibility_56=on;    
  
### 2.调用方法
python mysql_tuning.py -p tuning_sql.ini -s 'select d.dname ,e.empno from big_dep...'    
#### 参数说明     
    -p  指定配置文件名称    
    -s  指定SQL语句    
#### 配置文件    
  共分两节信息，分别是[database]描述数据库连接信息，[option]运行配置信息。  
  
      [database]
      server_ip   = 127.0.0.1
      server_port = 3306
      db_user     = testuser
      db_pwd      = testpwd
      db_name     = test
      [option]
      sys_parm    = ON	//是否显示系统参数
      sql_plan    = ON	//是否显示执行计划
      obj_stat    = ON	//是否显示相关对象(表、索引)统计信息
      ses_status  = ON	//是否显示运行前后状态信息(激活后会真实执行SQL)
      sql_profile = ON	//是否显示PROFILE跟踪信息(激活后会真实执行SQL)
     
         
### 3.输出说明    
#### 标题部分    
   包含运行数据库的地址信息及数据版本信息。    
   
        ===== BASIC INFORMATION =====
        +-----------+-------------+-----------+---------+------------+
        | server_ip | server_port | user_name | db_name | db_version |
        +-----------+-------------+-----------+---------+------------+
        | localhost |     3501    |  testuser |   test  |   5.7.12   |
        +-----------+-------------+-----------+---------+------------+
#### 原始SQL
用户执行输入的SQL，这部分主要是为了后续对比重写SQL时使用。

        ===== ORIGINAL SQL TEXT =====
        SELECT d.dname,
               e.empno
        FROM big_dept d,
             big_emp e
        WHERE d.deptno=e.deptno LIMIT 10
