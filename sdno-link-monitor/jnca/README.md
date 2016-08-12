## install

1. install JDK1.4.2 or above and mysql 4.x. 
1. Create a database named flowdata ('mysql -u root -p[password]' to enter it and 'create database if not exist flowdata')

1. Secondly, uncompress the jnca-beta-0.91.jar and modify the properties files located under etc/ directory
	Add the current directory (i.e the dot "." where etc and cai is located) and mysql-connector-java-3.1.10-bin.jar to ClassPath system variable ( it should contain the rt.jar shipped with JDK as well)
	launch "java cai.flow.collector.Run create_db" to create the tables. e.g in windows, the command line should be similar to "D:\Dev\netflow\jnca>java -classpath %classpath%;.\mysql-connector-java-3.1.10-bin.jar;.;.. cai.flow.collector.Run create_db"
	Carefully read the netflow.properties file under the etc directory, you have to add your router ip to the 
	launch "java cai.flow.collector.Run" as :"D:\Dev\netflow\jnca>java -classpath %classpath%;.\mysql-connector-java-3.1.10-bin.jar;.;.. cai.flow.collector.Run"
	Configure nprobe or cisco/juniper router to export netflow v1 v5 v7 v8 v9 UDP packet to current host:2055 UDP port.
	wait for a couple of minutes, look up the tables to see data.
trouble shooting
	Please contact me thru swingler@126.com or dial (0086-)13880021897 (English or Chinese language could be understood)
Detail info
	Please refer to http://itknowledge.yeah.net or http://jnca.sourceforge.net

运行目录为存储数据文件的目录
v5接收是写文件
其他还是写数据库
运行前注意修改etc目录下的SQL.properties和Netflow.properties
