
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
#### 系统级参数
脚本选择显示了部分与SQL性能相关的参数。

    ===== SYSTEM PARAMETER =====
    +-------------------------+-----------------+
    | parameter_name          |           value |
    +-------------------------+-----------------+
    | binlog_cache_size       |           1.0 M |
    | bulk_insert_buffer_size |          64.0 M |
    | join_buffer_size        |           8.0 M |
    | key_buffer_size         |         256.0 M |
    | key_cache_block_size    |           1.0 K |
    | max_binlog_cache_size   | 17179869183.0 G |
    | max_binlog_size         |           1.0 G |
    | max_join_size           | 17179869183.0 G |
    | query_cache_size        |             0 B |
    | query_prealloc_size     |           8.0 K |
    | range_alloc_block_size  |           4.0 K |
    | read_buffer_size        |           2.0 M |
    | read_rnd_buffer_size    |           8.0 M |
    | sort_buffer_size        |           2.0 M |
    | thread_cache_size       |            20 B |
    | tmp_table_size          |           1.0 G |
    +-------------------------+-----------------+
    
#### 优化器开关

    ===== OPTIMIZER SWITCH =====
    +-------------------------------------+-------+
    | switch_name                         | value |
    +-------------------------------------+-------+
    | index_merge                         |    on |
    | index_merge_union                   |    on |
    | index_merge_sort_union              |    on |
    | index_merge_intersection            |    on |
    | engine_condition_pushdown           |    on |
    | index_condition_pushdown            |    on |
    | mrr                                 |    on |
    | mrr_cost_based                      |    on |
    | block_nested_loop                   |    on |
    | batched_key_access                  |   off |
    | materialization                     |    on |
    | semijoin                            |    on |
    | loosescan                           |    on |
    | firstmatch                          |    on |
    | duplicateweedout                    |    on |
    | subquery_materialization_cost_based |    on |
    | use_index_extensions                |    on |
    | condition_fanout_filter             |    on |
    | derived_merge                       |    on |
    +-------------------------------------+-------+

#### 执行计划
就是调用explain extended的输出结果。如果结果过长，可能出现显示串行的问题(暂时未解决)。

    ===== SQL PLAN =====
    +----+-------------+-------+------------+-------+---------------+----------------+---------+---------------+------+----------+-------------+
    | id | select_type | table | partitions | type  | possible_keys | key            | key_len | ref           | rows | filtered | Extra       |
    +----+-------------+-------+------------+-------+---------------+----------------+---------+---------------+------+----------+-------------+
    |  1 | SIMPLE      | d     | None       | index | PRIMARY       | idx_dept_dname | 17      | None          | 1000 |    100.0 | Using index |
    |  1 | SIMPLE      | e     | None       | ref   | fk_deptno     | fk_deptno      | 5       | test.d.deptno |  996 |    100.0 | Using index |
    +----+-------------+-------+------------+-------+---------------+----------------+---------+---------------+------+----------+-------------+

#### 优化器改写后的SQL
通过这里可判断优化器是否对SQL进行了某种优化(例如子查询的处理)。

    ===== OPTIMIZER REWRITE SQL =====
    SELECT `test`.`d`.`dname` AS `dname`,
           `test`.`e`.`empno` AS `empno`
    FROM `test`.`big_dept` `d`
    JOIN `test`.`big_emp` `e`
    WHERE (`test`.`e`.`deptno` = `test`.`d`.`deptno`) LIMIT 10
#### 统计信息
相关对象的统计信息(表、索引)。在SQL语句中所有涉及到的表及其索引的统计信息都会在这里显示出来。

    ===== OBJECT STATISTICS =====
    +------------+--------+---------+------------+---------+----------+---------+----------+
    | table_name | engine | format  | table_rows | avg_row | total_mb | data_mb | index_mb |
    +------------+--------+---------+------------+---------+----------+---------+----------+
    | big_dept   | InnoDB | Dynamic |       1000 |      81 |     0.08 |    0.08 |     0.00 |
    +------------+--------+---------+------------+---------+----------+---------+----------+
    +----------------+------------+--------------+-------------+-----------+-------------+----------+------------+
    | index_name     | non_unique | seq_in_index | column_name | collation | cardinality | nullable | index_type |
    +----------------+------------+--------------+-------------+-----------+-------------+----------+------------+
    | idx_dept_dname |          1 |            1 | dname       |     A     |        1000 |      YES | BTREE      |
    | PRIMARY        |          0 |            1 | deptno      |     A     |        1000 |          | BTREE      |
    +----------------+------------+--------------+-------------+-----------+-------------+----------+------------+
    +------------+--------+---------+------------+---------+----------+---------+----------+
    | table_name | engine | format  | table_rows | avg_row | total_mb | data_mb | index_mb |
    +------------+--------+---------+------------+---------+----------+---------+----------+
    | big_emp    | InnoDB | Dynamic |     996293 |      62 |   123.70 |   59.58 |    64.13 |
    +------------+--------+---------+------------+---------+----------+---------+----------+
    +------------+------------+--------------+-------------+-----------+-------------+----------+------------+
    | index_name | non_unique | seq_in_index | column_name | collation | cardinality | nullable | index_type |
    +------------+------------+--------------+-------------+-----------+-------------+----------+------------+
    | fk_deptno  |          1 |            1 | deptno      |     A     |        1000 |      YES | BTREE      |
    | idx_sal    |          1 |            1 | sal         |     A     |       10145 |      YES | BTREE      |
    | PRIMARY    |          0 |            1 | empno       |     A     |      996293 |          | BTREE      |
    +------------+------------+--------------+-------------+-----------+-------------+----------+------------+
#### 运行状态信息
在会话级别对比了执行前后的状态(SHOW STATUS)，并将出现变化的部分显示出来。需要注意的是，因为收集状态数据是采用SELECT方式，会造成个别指标的误差(例如Com_select)。

    ===== SESSION STATUS (DIFFERENT) =====
    +----------------------------------+-----------+---------------+---------------+
    | status_name                      |    before |         after |          diff |
    +----------------------------------+-----------+---------------+---------------+
    | Bytes_received                   |       515 |           812 |         297.0 |
    | Bytes_sent                       |       661 |         12002 |       11341.0 |
    | Com_select                       |         2 |             4 |           2.0 |
    | Com_show_warnings                |         2 |             3 |           1.0 |
    | Created_tmp_tables               |         2 |             3 |           1.0 |
    | Handler_commit                   |         0 |             1 |           1.0 |
    | Handler_external_lock            |         0 |             4 |           4.0 |
    | Handler_read_first               |         0 |             1 |           1.0 |
    | Handler_read_key                 |         0 |             2 |           2.0 |
    | Handler_read_next                |         0 |             9 |           9.0 |
    | Handler_read_rnd                 |         0 |           380 |         380.0 |
    | Handler_read_rnd_next            |         6 |           387 |         381.0 |
    | Handler_write                    |       193 |           573 |         380.0 |
    | Innodb_buffer_pool_bytes_data    |  43204608 |      43270144 |       65536.0 |
    | Innodb_buffer_pool_pages_data    |      2637 |          2641 |           4.0 |
    | Innodb_buffer_pool_pages_free    |     30115 |         30111 |          -4.0 |
    | Innodb_buffer_pool_read_requests |  26779348 |      26779357 |           9.0 |
    | Innodb_buffer_pool_reads         |      2565 |          2569 |           4.0 |
    | Innodb_data_read                 |  42095104 |      42160640 |       65536.0 |
    | Innodb_data_reads                |      2595 |          2600 |           5.0 |
    | Innodb_num_open_files            |        23 |            24 |           1.0 |
    | Innodb_pages_read                |      2564 |          2568 |           4.0 |
    | Innodb_rows_read                 |  54637053 |      54637064 |          11.0 |
    | Last_query_cost                  | 10.499000 | 201556.132981 | 201545.633981 |
    | Last_query_partial_plans         |         1 |             3 |           2.0 |
    | Open_tables                      |        54 |            56 |           2.0 |
    | Opened_tables                    |         0 |             2 |           2.0 |
    | Queries                          |   2734384 |       2734387 |           3.0 |
    | Questions                        |         6 |             9 |           3.0 |
    | Select_scan                      |         2 |             4 |           2.0 |
    | Sort_rows                        |         0 |           380 |         380.0 |
    | Sort_scan                        |         0 |             1 |           1.0 |
    | Table_open_cache_misses          |         0 |             2 |           2.0 |
    +----------------------------------+-----------+---------------+---------------+

#### PROFILE详细信息
调用SHOW PROFILE得到的详细信息。

    ===== SQL PROFILING(DETAIL)=====
    +----------------+----------+----------+----------+-------+--------+-------+-------+--------+--------+-------+
    | state          | duration | cpu_user |  cpu_sys | bk_in | bk_out | msg_s | msg_r | p_f_ma | p_f_mi | swaps |
    +----------------+----------+----------+----------+-------+--------+-------+-------+--------+--------+-------+
    | starting       | 0.000079 | 0.000000 | 0.000000 |     0 |      0 |     0 |     0 |      0 |      0 |     0 |
    | query end      | 0.000006 | 0.000000 | 0.000000 |     0 |      0 |     0 |     0 |      0 |      0 |     0 |
    | closing tables | 0.000004 | 0.000000 | 0.000000 |     0 |      0 |     0 |     0 |      0 |      0 |     0 |
    | freeing items  | 0.000010 | 0.000000 | 0.000000 |     0 |      0 |     0 |     0 |      0 |      0 |     0 |
    | cleaning up    | 0.000073 | 0.000000 | 0.000000 |     0 |      0 |     0 |     0 |      0 |      0 |     0 |
    +----------------+----------+----------+----------+-------+--------+-------+-------+--------+--------+-------+
    bk_in:   block_ops_in
    bk_out:  block_ops_out
    msg_s:   message sent
    msg_r:   message received
    p_f_ma:  page_faults_major
    p_f_mi:  page_faults_minor
 
#### PROFILE汇总信息
根据PROFILE的资源消耗情况，显示不同阶段消耗对比情况(TOP N)，直观显示"瓶颈"所在。

    ===== SQL PROFILING(SUMMARY)=====
    +----------------+----------+-------+-------+--------------+
    | state          |  total_r | pct_r | calls |       r/call |
    +----------------+----------+-------+-------+--------------+
    | starting       | 0.000079 | 45.93 |     1 | 0.0000790000 |
    | cleaning up    | 0.000073 | 42.44 |     1 | 0.0000730000 |
    | freeing items  | 0.000010 |  5.81 |     1 | 0.0000100000 |
    | query end      | 0.000006 |  3.49 |     1 | 0.0000060000 |
    | closing tables | 0.000004 |  2.33 |     1 | 0.0000040000 |
    +----------------+----------+-------+-------+--------------+
 
#### 执行时长
实际执行时长。

    ===== EXECUTE TIME =====
    0 day 0 hour 0 minute 0 second 162 microsecond 
