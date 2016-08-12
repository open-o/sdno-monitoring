package cai.utils;

import java.io.File;
import java.io.IOException;
import java.io.RandomAccessFile;
import java.text.SimpleDateFormat;
import java.util.Date;
import java.util.HashMap;

public class writeFile {

	static HashMap routerIpmap =  new  HashMap();
	static int peroid=60;
	static {
		Resources resources = new Resources("NetFlow");
		peroid = resources.integer("flow.period");
		if (peroid<=0) peroid=60;
		System.out.println("peroid:"+String.valueOf(peroid));
	}
	public static void write(
			String ver,
			String routerIP,
			String srcaddr,
			String dstaddr,
			String nexthop,
			long dpkt,
			long dOctets,
			byte src_mask,
			byte dst_mask,
			int output)
	{
		System.out.println("-----------------------");
		System.out.println("ver:" + ver);
		System.out.println("routerIP:" + routerIP);
		System.out.println("srcaddr:" + srcaddr);
		System.out.println("dstaddr:" + dstaddr);
		System.out.println("nexthop:" + nexthop);
		System.out.println("dpkt:" + dpkt);
		System.out.println("dOctets:" + dOctets);
		System.out.println("src_mask:" + src_mask);
		System.out.println("dst_mask:" + dst_mask);
		System.out.println("output:" + output);
		System.out.println("-----------------------");
		
		if (!existInMap(routerIP)){
			// long start = System.currentTimeMillis();
			routerIpmap.put(routerIP, new mapInfo(routerIP));
			// long stops = System.currentTimeMillis();
			//	System.out.println("ipmap.put:  " + (stops - start));
		}
		long start = System.currentTimeMillis();
		mapInfo m = (mapInfo) routerIpmap.get(routerIP);
		long stops = System.currentTimeMillis();
		//System.out.println("mapinfo.get   " + (stops - start));
		synchronized(m){
			long start2 = System.currentTimeMillis();
			///-cy 未打开文件 则打开并check ,收到流的时候如果已经有文件打开则直接写
			if (! fileOpened(m)){

				openFile(m);
				startCheck(m);
			}
			long stops2 = System.currentTimeMillis();
			//	System.out.println("check::  " + (stops2 - start2));
			long start3 = System.currentTimeMillis();
			writeFile(ver, m, srcaddr, dstaddr, nexthop, dpkt, dOctets, src_mask, dst_mask, output);
			long stops3 = System.currentTimeMillis();
			//System.out.println("writeFile  " + (stops3 - start3));
		}
	}
	private static void startCheck(final mapInfo m) {
		// TODO Auto-generated method stub
		//获取绝对秒

		m.startTime = (new Date()).getTime() ;
		int n=0;
		//启动线程
		if (m.t != null) {
			Thread tmpBlinker = m.t;
			//m.t.stop();
			m.t = null;
			/////--陈云  什么用 alwaystrue??????
			if (tmpBlinker != null) {
				tmpBlinker.interrupt();
			}
		}

		m.t = new Thread() {
			public void run() {
				while (true) {
					long cTime = (new Date()).getTime() ;
					//System.out.println(m.startTime);
					///---陈云 一个周期的时间如果超过了1000*period 则强行关闭 每分钟关闭一次
					if (cTime-m.startTime >1000*peroid){
						long start = System.currentTimeMillis();
						closeFile(m);
						long stops = System.currentTimeMillis();        System.out.println("close_file  " + (stops - start));
						return;
					}

					try {
						Thread.sleep(500);//////--陈云 怎么变成500
					} catch (InterruptedException e) {
						// TODO Auto-generated catch block
						e.printStackTrace();
					}
				}
			}
		};

		m.t.start();
	}

	static class mapInfo{
		public String ip;
		public int c; //计数器,表示第几个文件将要产生
		public String fname; //文件名
		public RandomAccessFile f; //文件流，打开则不为空
		public int n; //本次写文件的次数
		public long  startTime;
		public Thread t;
		static public String all_s;
		public mapInfo(String addr){
			ip = addr;
			f = null;
			all_s="";
			c = n = 0;
			startTime = 0L;
			fname = null;
			t= null;
		}
	};
	static boolean existInMap(String ip){
		//若已经存在，返回true。
		return routerIpmap.containsKey(ip);
	}
	static boolean fileOpened(mapInfo m){
		//文件是否打开
		if (existInMap(m.ip)){
			return m.f!=null;
		}
		return false;
	}
	static boolean openFile(mapInfo m){
		SimpleDateFormat df = new SimpleDateFormat("_yyyyMMdd_HHmmss");//设置日期格式
		String ctime = df.format(new Date());// new Date()为获取当前系统时间
		m.fname = m.ip+ ctime ;
		try {
			// 打开一个随机访问文件流，按读写方式  
			m.f  = new RandomAccessFile(m.fname, "rws");
			return true;

		} catch (IOException e) {
			e.printStackTrace();
		}
		return false;
	}
	static boolean closeFile(mapInfo m){
		synchronized(m){
			try {
				m.f.writeBytes(m.all_s);
				m.all_s="";
				// 打开一个随机访问文件流，按读写方式
				m.f.close();
				m.f=null;
				SimpleDateFormat df = new SimpleDateFormat("yyyy-MM-dd_HH:mm:ss");//设置日期格式
				String ctime = df.format(new Date());// new Date()为获取当前系统时间
				String s = String.format("[%s] %s file created. fileNo:%d, write:%d", ctime,m.fname,m.c,m.n);
				System.out.println(s);
				//////////////////rename 没啥地用
				renameFile(m.fname,m.fname+".txt");
				//////////////////////////////
				m.fname = null;
				m.c ++;
				m.n = 0;
				m.t = null;
				return true;

			} catch (IOException e) {
				e.printStackTrace();
			}
		}
		return false;
	}
	/** *//**文件重命名
	 * @param oldname  原来的文件名
	 * @param newname 新文件名
	 */
	static public void renameFile(String oldname,String newname)
	{
		String path=".";
		if(!oldname.equals(newname)){//新的文件名和以前文件名不同时,才有必要进行重命名
			File oldfile=new File(path+"/"+oldname);
			File newfile=new File(path+"/"+newname);
			if(!oldfile.exists()){
				return;//重命名文件不存在
			}
			if(newfile.exists())//若在该目录下已经有一个文件和新文件名相同，则不允许重命名
				System.out.println(newname+"已经存在！");
			else{
				oldfile.renameTo(newfile);
			}
		}else{
			System.out.println("新文件名和旧文件名相同...");
		}
	}
	static boolean writeFile(String ver, mapInfo m, String srcaddr, String dstaddr, String nexthop, long dpkt, long dOctets, byte src_mask, byte dst_mask, int output){
		try {
			System.out.println("-----------------------");
            System.out.println("ver:" + ver);
            System.out.println("routerIP:" + m.ip);
            System.out.println("srcaddr:" + srcaddr);
            System.out.println("dstaddr:" + dstaddr);
            System.out.println("nexthop:" + nexthop);
            System.out.println("dpkt:" + dpkt);
            System.out.println("dOctets:" + dOctets);
            System.out.println("src_mask:" + src_mask);
            System.out.println("dst_mask:" + dst_mask);
            System.out.println("output:" + output);
            System.out.println("-----------------------");
	

            
			long start = System.currentTimeMillis();
			m.n++;
			//m.startTime = (new Date()).getTime() ;
			SimpleDateFormat df = new SimpleDateFormat("yyyy-MM-dd HH:mm:ss");//设置日期格式
			String ctime = df.format(new Date());// new Date()为获取当前系统时间
			if (nexthop.length()<=1) nexthop="0.0.0.0";
			String s=m.ip + "," + ctime + "," + srcaddr + "," + dstaddr + "," + nexthop;
			String s1=String.format(",%d,%d,%d,%d,%d,%s",dpkt,dOctets,src_mask, dst_mask,output,ver);
			s += s1 + "\r\n";
			////没用???
			//char[] chars = s.toCharArray(); //把字符中转换为字符数组 
			//char [] charss = new char [chars.length/2];
			//for(int i=1,j=0;i<chars.length;i+=2,j++){//输出结果
			//	charss[j]=chars[i];
			//}
			long stops = System.currentTimeMillis();
			//System.out.println("write_file__1  " + (stops - start));
			/////////////
			long start2 = System.currentTimeMillis();
			////////////////////////////////////////////////////raw_process的90%的时间
			m.all_s=m.all_s.concat(s);
			//m.f.writeBytes(s);
			////////////////////////////////////////////////////////
			long stops2 = System.currentTimeMillis();
			//System.out.println("write_file__2  " + (stops2 - start2));
			//System.out.println("     "+String.valueOf(m.startTime));

			return true;

		} catch (Exception e) {
			e.printStackTrace();
		}
		return false;
	}
}
