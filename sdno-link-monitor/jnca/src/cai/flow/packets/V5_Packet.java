package cai.flow.packets;

import java.util.Vector;

import cai.flow.packets.FlowPacket;
import cai.utils.DoneException;
import cai.sql.SQL;
import cai.utils.Util;

public class V5_Packet implements FlowPacket {
	long count;
	String RouterIP;
	long SysUptime, unix_secs, unix_nsecs, flow_sequence;
	long engine_type, engine_id;
	Vector flows;
	public static final int V5_Header_Size = 24;
	public static final int V5_Flow_Size = 48;
	/**
	 * ����UDP��ͷ�������е�flows�����洢���ڴ�Vector��
	 *
	 * @param RouterIP
	 * @param buf
	 * @param len
	 * @throws DoneException
	 */
	public V5_Packet(String RouterIP, byte[] buf, int len) throws DoneException {
 
		if (len < V5_Header_Size)
			throw new DoneException("    * incomplete header *");
		this.RouterIP = RouterIP;
		count = Util.to_number(buf, 2, 2);
		if (count <= 0 || len != V5_Header_Size + count * V5_Flow_Size)
			throw new DoneException( "* corrupted packet *");
		SysUptime = Util.to_number(buf, 4, 4);
		unix_secs = Util.to_number(buf, 8, 4);
		unix_nsecs = Util.to_number(buf, 12, 4);
		flow_sequence = Util.to_number(buf, 16, 4);
		engine_type = buf[20];
		engine_id = buf[21];
		flows = new Vector((int) count);
		for (int i = 0, p = V5_Header_Size; i < count; i++, p += V5_Flow_Size) {
			V5_Flow f;
			try {
				f = new V5_Flow(RouterIP, buf, p);
				// ��ַû�б��ų�
				if (f.srcaddr != null && f.dstaddr != null) {
					flows.add(f);
				} 
			}
			finally {
			}
		}
	}
	
	public void process_raw(SQL sql) {
		// TODO Auto-generated method stub
		
	}
	public Vector getSrcASVector() {
		// TODO Auto-generated method stub
		return null;
	}
	public Vector getDstASVector() {
		// TODO Auto-generated method stub
		return null;
	}
	public Vector getASMatrixVector() {
		// TODO Auto-generated method stub
		return null;
	}
	public Vector getSrcNodeVector() {
		// TODO Auto-generated method stub
		return null;
	}
	public Vector getDstNodeVector() {
		// TODO Auto-generated method stub
		return null;
	}
	public Vector getHostMatrixVector() {
		// TODO Auto-generated method stub
		return null;
	}
	public Vector getSrcInterfaceVector() {
		// TODO Auto-generated method stub
		return null;
	}
	public Vector getDstInterfaceVector() {
		// TODO Auto-generated method stub
		return null;
	}
	public Vector getInterfaceMatrixVector() {
		// TODO Auto-generated method stub
		return null;
	}
	public Vector getSrcPrefixVector() {
		// TODO Auto-generated method stub
		return null;
	}
	public Vector getDstPrefixVector() {
		// TODO Auto-generated method stub
		return null;
	}
	public Vector getPrefixMatrixVector() {
		// TODO Auto-generated method stub
		return null;
	}
	public Vector getProtocolVector() {
		// TODO Auto-generated method stub
		return null;
	}
}

