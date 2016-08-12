/**
 *
 */
package cai.flow.packets;

import java.io.File;
import java.io.FileInputStream;
import java.io.FileNotFoundException;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.ObjectInputStream;
import java.io.ObjectOutputStream;
import java.util.Enumeration;
import java.util.Vector;

import cai.flow.packets.v9.OptionFlow;
import cai.flow.packets.v9.OptionTemplate;
import cai.flow.packets.v9.OptionTemplateManager;
import cai.flow.packets.v9.Template;
import cai.flow.packets.v9.TemplateManager;
import cai.flow.struct.Scheme_DataPrefix;
import cai.sql.SQL;
import cai.utils.*;

/**
 * @author CaiMao V9 Flow Packet UDP包的解析，内部包含多个FlowSet DataSet的流对象
 *
 * -------*---------------*------------------------------------------------------* |
 * Bytes | Contents | Description |
 * -------*---------------*------------------------------------------------------* |
 * 0-1 | version | The version of NetFlow records exported 009 |
 * -------*---------------*------------------------------------------------------* |
 * 2-3 | count | Number of flows exported in this packet (1-30) |
 * -------*---------------*------------------------------------------------------* |
 * 4-7 | SysUptime | Current time in milliseconds since the export device | | | |
 * booted |
 * -------*---------------*------------------------------------------------------* |
 * 8-11 | unix_secs | Current count of seconds since 0000 UTC 1970 |
 * -------*---------------*------------------------------------------------------* |
 * 12-15 |PackageSequence| pk id of all flows |
 * -------*---------------*------------------------------------------------------* |
 * 16-19 | Source ID | engine type+engine id |
 * -------*---------------*------------------------------------------------------* |
 * 20- | others | Unused (zero) bytes |
 * -------*---------------*------------------------------------------------------*
 *
 */
public class V9_Packet implements FlowPacket {
    long count;

    String routerIP;

    long SysUptime, unix_secs, packageSequence;

    long sourceId;

    Vector flows = null;

    Vector optionFlows = null;

    public static final int V9_Header_Size = 20;
    public static void main(String[] args) {
//        for (int i = 0; i < 10; i++) {
//            Runnable run = new Runnable() {
//                public void run() {
                    new V9_Packet("127.0.0.0", new byte[] {}, 0);
//                }
//            };
//            Thread t1 = new Thread(run);
//            Thread t2 = new Thread(run);
//            Thread t3 = new Thread(run);
//            t1.start();
//            t2.start();
//            t3.start();
//        }
    }

    /**
     * 解析UDP包头，把所有的flows解析存储到内存Vector中
     *
     * @param RouterIP
     * @param buf
     * @param len
     * @throws DoneException
     */
    public V9_Packet(String RouterIP, byte[] buf, int len) throws DoneException {
        if (Params.DEBUG) {
            // 仅仅实验
            /*
//            File tmpFile = new File("D:\\Dev\\netflow\\jnca\\savePacketT_211.98.0.147_256.cache.tmp");
            File tmpFile = new File(
                    "D:\\Dev\\netflow\\jnca\\savePacketT_211.98.0.147_256.cache.tmp");
            if (tmpFile.exists()) {
                try {
                    ObjectInputStream fIn = new ObjectInputStream(
                            new FileInputStream(tmpFile));
                    System.out.println("Directly read from " + fIn);
                    try {
                        buf = (byte[]) fIn.readObject();
                        len = ((Integer) fIn.readObject()).intValue();
                    } catch (ClassNotFoundException e) {
                        e.printStackTrace();
                    }
                    fIn.close();
                } catch (FileNotFoundException e) {
                    e.printStackTrace();
                } catch (IOException e) {
                    e.printStackTrace();
                }
            } else {
                try {
                    ObjectOutputStream fOut;
                    fOut = new ObjectOutputStream(new FileOutputStream(tmpFile));
                    fOut.writeObject(buf);
                    fOut.writeObject(new Integer(len));
                    fOut.flush();
                    fOut.close();
                } catch (FileNotFoundException e) {
                    e.printStackTrace();
                } catch (IOException e1) {
                    e1.printStackTrace();
                }
            }*/
            // 仅仅实验
        }
        if (len < V9_Header_Size) {
            throw new DoneException("    * incomplete header *");
        }

        this.routerIP = RouterIP;
        count = Util.to_number(buf, 2, 2); // 包括template data flowset数目

        SysUptime = Util.to_number(buf, 4, 4);
        Variation vrat = Variation.getInstance();
        vrat.setVary(Util.convertIPS2Long(RouterIP), SysUptime);
        unix_secs = Util.to_number(buf, 8, 4);
        packageSequence = Util.to_number(buf, 12, 4);
        sourceId = Util.to_number(buf, 16, 4);
        
        System.out.println(">>> V9_Packet");
        System.out.println("unix_secs:" + unix_secs);
        System.out.println("packageSequence:" + packageSequence);
        System.out.println("sourceId:" + sourceId);
        System.out.println("count:" + count);

        flows = new Vector((int) count * 30); // Let's first make some space
        optionFlows = new Vector();
        // 链表
        long flowsetLength = 0l;
        // 处理flowset的循环
        for (int flowsetCounter = 0, packetOffset = V9_Header_Size;
                flowsetCounter < count
                && packetOffset < len; flowsetCounter++,
                packetOffset += flowsetLength) {
            // 处理flowset内部
            long flowsetId = Util.to_number(buf, packetOffset, 2);
            flowsetLength = Util.to_number(buf, packetOffset + 2, 2);
            
            System.out.println("flowsetCounter:" + flowsetCounter);
            System.out.println("flowsetId:" + flowsetId);
            System.out.println("flowsetLength:" + flowsetLength);
            
            
            if (flowsetLength == 0) {
                throw new DoneException(
                        "there is a flowset len=0，packet invalid");
            }
            if (flowsetId == 0) {
                // template flowset，这里templateid是一个内容，不像data flowset
                // 处理template flowset
                int thisTemplateOffset = packetOffset + 4;
                do {
                    // 定义一个template
                    long templateId = Util
                                      .to_number(buf, thisTemplateOffset, 2);
                    long fieldCount = Util.to_number(buf,
                            thisTemplateOffset + 2, 2);
                    if (TemplateManager.getTemplateManager().getTemplate(
                            this.routerIP, (int) templateId) == null
                        || Params.v9TemplateOverwrite) {
                        try {
                            TemplateManager.getTemplateManager().acceptTemplate(
                                    this.routerIP, buf, thisTemplateOffset);
                        } catch (Exception e) {
                            if (Params.DEBUG) {
                                e.printStackTrace();
                            }
                            if ((e.toString() != null)
                                && (!e.toString().equals(""))) {
                                if (e.toString().startsWith("savePacket")) {
                                    try {
                                        ObjectOutputStream fOut;
                                        fOut = new ObjectOutputStream(new
                                                FileOutputStream("./" +
                                                e.toString() + ".cache.tmp"));
                                        fOut.writeObject(buf);
                                        fOut.writeObject(new Integer(len));
                                        fOut.flush();
                                        fOut.close();
                                        System.err.println("Saved ");
                                    } catch (FileNotFoundException e2) {
                                        e2.printStackTrace();
                                    } catch (IOException e1) {
                                        e1.printStackTrace();
                                    }
                                } else {
                                    System.err.println("An Error without save:" +
                                            e.toString());
                                }
                            }
                        }

                    }
                    thisTemplateOffset += fieldCount * 4 + 4; //这里似乎有问题
                } while (thisTemplateOffset - packetOffset < flowsetLength);
            } else if (flowsetId == 1) { // options flowset
                continue;
//                int thisOptionTemplateOffset = packetOffset + 4;
//                // bypass flowsetID and flowset length
//                do {
//                    // 定义一个template
//                    long optionTemplateId = Util.to_number(buf,
//                            thisOptionTemplateOffset, 2);
//                    long scopeLen = Util.to_number(buf,
//                            thisOptionTemplateOffset + 2, 2);
//                    long optionLen = Util.to_number(buf,
//                            thisOptionTemplateOffset + 4, 2);
//                    if (OptionTemplateManager.getOptionTemplateManager()
//                        .getOptionTemplate(this.routerIP,
//                                           (int) optionTemplateId) == null
//                        || Params.v9TemplateOverwrite) {
//                        OptionTemplateManager.getOptionTemplateManager()
//                                .acceptOptionTemplate(this.routerIP, buf,
//                                thisOptionTemplateOffset);
//                    }
//                    thisOptionTemplateOffset += scopeLen + optionLen + 6;
//                } while (thisOptionTemplateOffset -
//                         packetOffset < flowsetLength);
            } else if (flowsetId > 255) {
                // data flowset
                // templateId==flowsetId
                Template tOfData = TemplateManager.getTemplateManager()
                                   .getTemplate(this.routerIP, (int) flowsetId); // flowsetId==templateId
                if (tOfData != null) {
                    int dataRecordLen = tOfData.getTypeOffset( -1); // 每个流记录的长度
                    // packetOffset+4 让出flowsetId 和 length空间
                    for (int idx = 0, p = packetOffset + 4;
                                          (p - packetOffset + dataRecordLen) <=
                                          flowsetLength; //consider padding
                                          idx++, p += dataRecordLen) { //+5 makes OK
                        // 对当前IP网络管理，v9的数据仍然仅仅利用其v5就具有的部分
                        V5_Flow f;
                        try {
                            f = new V5_Flow(RouterIP, buf, p, tOfData);
                            flows.add(f); // 加入到Vector中，所有归并就可以起作用了
                        } catch (DoneException e) {
                            if (Params.DEBUG) {
                                e.printStackTrace();
                            }
                            if ((e.toString() != null)
                                && (!e.toString().equals(""))) {
                                if (e.toString().startsWith("savePacket")) {
                                    try {
                                        ObjectOutputStream fOut;
                                        fOut = new ObjectOutputStream(new
                                                FileOutputStream("./" +
                                                e.toString() + ".cache.tmp"));
                                        fOut.writeObject(buf);
                                        fOut.writeObject(new Integer(len));
                                        fOut.flush();
                                        fOut.close();
                                        System.err.println("Saved ");
                                    } catch (FileNotFoundException e2) {
                                        e2.printStackTrace();
                                    } catch (IOException e1) {
                                        e1.printStackTrace();
                                    }
                                } else {
                                    System.err.println(e.toString());
                                }
                            }
                        }
                    }
                } else { //options packet, should refer to option template, not in use now
                    continue;
//                    OptionTemplate otOfData = OptionTemplateManager
//                                              .getOptionTemplateManager().
//                                              getOptionTemplate(
//                            this.routerIP, (int) flowsetId);
//                    if (otOfData != null) {
//                        int dataRecordLen = otOfData.getTypeOffset( -1); // 每个流记录的长度
//                        // packetOffset+4 让出flowsetId 和 length空间
//                        for (int idx = 0, p = packetOffset + 4; p
//                                              - packetOffset < flowsetLength;
//                                              idx++, p += dataRecordLen) {
//                            OptionFlow of;
//                            try {
//                                of = new OptionFlow(RouterIP, buf, p, otOfData);
////                                optionFlows.add(of); // 加入到Vector中，所有归并就可以起作用了
//                            } catch (DoneException e) {
//                                if (Params.DEBUG) {
//                                    e.printStackTrace();
//                                }
//                                System.err.println(e.toString());
//                            }
//                        }
//                    } else {
//                        System.err.println(this.routerIP + "的" + flowsetId
//                                           + "是一个不能识别的template号");
//                    }
                }
            }
        }
    }

    protected static String add_raw_sql = null;

    public void process_raw(SQL sql) {
    	
    	System.out.println(">>> Process_RAW: V9_Packet: SQL:" + sql);
        if (add_raw_sql == null) {
           // add_raw_sql = SQL.resources.getAndTrim("SQL.Add.RawV9");
        }

        for (Enumeration flowenum = flows.elements(); flowenum
                                    .hasMoreElements(); ) {
        	System.out.println("Process_RAW: save_raw4v9");
            ((V5_Flow) flowenum.nextElement()).save_raw4v9(SysUptime,
                    unix_secs, packageSequence, sourceId);//, sql.prepareStatement(
                         //   "Prepare INSERT to V9 raw table", add_raw_sql));
        }
        System.out.println("<<< Process_RAW: V9_Packet: SQL:" + sql);
        /*
        for (Enumeration oflowenum = optionFlows.elements(); oflowenum
                                     .hasMoreElements(); ) {
            ((OptionFlow) oflowenum.nextElement()).save_raw(SysUptime,
                    unix_secs, packageSequence, sourceId, sql.prepareStatement(
                            "Prepare INSERT to Option table", SQL.resources
                            .getAndTrim("SQL.Add.OptionsTable")));
        }
        */
    }

    public Vector getSrcASVector() {
        Vector v = new Vector((int) count, (int) count);

        for (Enumeration flowenum = flows.elements(); flowenum
                                    .hasMoreElements(); ) {
            v.add(((V5_Flow) flowenum.nextElement()).getDataSrcAS());
        }

        return v;
    }

    public Vector getDstASVector() {
        Vector v = new Vector((int) count, (int) count);

        for (Enumeration flowenum = flows.elements(); flowenum
                                    .hasMoreElements(); ) {
            v.add(((V5_Flow) flowenum.nextElement()).getDataDstAS());
        }

        return v;
    }

    public Vector getASMatrixVector() {
        Vector v = new Vector((int) count, (int) count);

        for (Enumeration flowenum = flows.elements(); flowenum
                                    .hasMoreElements(); ) {
            v.add(((V5_Flow) flowenum.nextElement()).getDataASMatrix());
        }

        return v;
    }

    public Vector getSrcNodeVector() {
        Vector v = new Vector((int) count, (int) count);

        for (Enumeration flowenum = flows.elements(); flowenum
                                    .hasMoreElements(); ) {
            v.add(((V5_Flow) flowenum.nextElement()).getDataSrcNode());
        }

        return v;
    }

    public Vector getDstNodeVector() {
        Vector v = new Vector((int) count, (int) count);

        for (Enumeration flowenum = flows.elements(); flowenum
                                    .hasMoreElements(); ) {
            v.add(((V5_Flow) flowenum.nextElement()).getDataDstNode());
        }

        return v;
    }

    public Vector getHostMatrixVector() {
        Vector v = new Vector((int) count, (int) count);

        for (Enumeration flowenum = flows.elements(); flowenum
                                    .hasMoreElements(); ) {
            v.add(((V5_Flow) flowenum.nextElement()).getDataHostMatrix());
        }

        return v;
    }

    public Vector getSrcInterfaceVector() {
        Vector v = new Vector((int) count, (int) count);

        for (Enumeration flowenum = flows.elements(); flowenum
                                    .hasMoreElements(); ) {
            v.add(((V5_Flow) flowenum.nextElement()).getDataSrcInterface());
        }

        return v;
    }

    public Vector getDstInterfaceVector() {
        Vector v = new Vector((int) count, (int) count);

        for (Enumeration flowenum = flows.elements(); flowenum
                                    .hasMoreElements(); ) {
            v.add(((V5_Flow) flowenum.nextElement()).getDataDstInterface());
        }

        return v;
    }

    public Vector getInterfaceMatrixVector() {
        Vector v = new Vector((int) count, (int) count);

        for (Enumeration flowenum = flows.elements(); flowenum
                                    .hasMoreElements(); ) {
            v.add(((V5_Flow) flowenum.nextElement()).getDataInterfaceMatrix());
        }

        return v;
    }

    public Vector getSrcPrefixVector() {
        Vector v = new Vector((int) count, (int) count);

        for (Enumeration flowenum = flows.elements(); flowenum
                                    .hasMoreElements(); ) {
            Scheme_DataPrefix pfx = ((V5_Flow) flowenum.nextElement())
                                    .getDataSrcPrefix();
            if (pfx != null) {
                v.add(pfx);
            }
        }

        return v;
    }

    public Vector getDstPrefixVector() {
        Vector v = new Vector((int) count, (int) count);

        for (Enumeration flowenum = flows.elements(); flowenum
                                    .hasMoreElements(); ) {
            Scheme_DataPrefix dpfx = ((V5_Flow) flowenum.nextElement())
                                     .getDataDstPrefix();
            if (dpfx != null) {
                v.add(dpfx);
            }
        }
        return v;
    }

    public Vector getPrefixMatrixVector() {
        Vector v = new Vector((int) count, (int) count);

        for (Enumeration flowenum = flows.elements(); flowenum
                                    .hasMoreElements(); ) {
            v.add(((V5_Flow) flowenum.nextElement()).getDataPrefixMatrix());
        }

        return v;
    }

    public Vector getProtocolVector() {
        Vector v = new Vector((int) count, (int) count);

        for (Enumeration flowenum = flows.elements(); flowenum
                                    .hasMoreElements(); ) {
            v.add(((V5_Flow) flowenum.nextElement()).getDataProtocol());
        }

        return v;
    }
}
