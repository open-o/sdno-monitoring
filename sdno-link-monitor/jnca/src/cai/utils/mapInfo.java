package cai.utils;

import java.io.RandomAccessFile;

class mapInfo{
	public String ip;
	public int c; //������,��ʾ�ڼ����ļ���Ҫ����
	public String fname; //�ļ���
	public RandomAccessFile f; //�ļ���������Ϊ��
	public int n; //����д�ļ��Ĵ���
	public long  startTime;
	public Thread t;
	public String all_s;
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