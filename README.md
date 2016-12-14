
###1.准备条件
####模块
  -  模块 - MySQLDB  
  模块 - sqlparse  
  模块 - prettytable  
####版本
  Python版本 >= 2.6 (3.x版本没测试)
####授权
  grant all on *.* to testuser@'localhost' identified by 'testpwd';
####参数
  在5.7版本中，需要打开show_compatibility_56参数。
  set global show_compatibility_56=on;
  
(2).调用方法
python mysql_tuning.pyc -p tuning_sql.ini -s 'select d.dname ,e.empno from big_dept d,big_emp e where d.deptno=e.deptno limit 10'
参数说明
-p  指定配置文件名称
-s  指定SQL语句
