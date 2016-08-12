package cai.flow.collector;

import java.io.UnsupportedEncodingException;

import cai.flow.packets.v9.TemplateManager;
import cai.sql.SQL;
import cai.utils.DoneException;
import cai.utils.Params;
import cai.utils.Syslog;

import cai.flow.collector.configSever;

public class Run {
    static {
        try {
            Class.forName("cai.flow.collector.Collector");
        } catch (Exception ex) {
            ex.printStackTrace();
        }
    }

    public static void go(String args[]) {
        boolean run_collector = true;

        for (int i = 0; i < args.length; i++) {
            if (args[i].equals("create_db")) {
                new SQL().create_DB();
                run_collector = false;
            } else if (args[i].equals("remove_db")) {
                new SQL().delete_DB();
                run_collector = false;
            } else if (args[i].startsWith("encoding=")) {
                Params.encoding = args[i].substring(9);

                try {
                    String test = "eeeeeee";
                    test.getBytes(Params.encoding);
                } catch (UnsupportedEncodingException e) {
                    System.err.println("RUN: Unsupported encoding: "
                                       + Params.encoding);
                    System.exit(0);
                }
            } else {
                System.err.println("RUN: Unknown argument -- " + args[i]);
                // run_collector = false;
            }
        }

        if (run_collector) { // 如果不是在创库或者删除库的操作
            // 那么进入主要工作
            TemplateManager.getTemplateManager();
         // XXX: auv: Entrance: Call Collector().go()
            new Collector(args).go();
        }
    }

    public static void main(String args[]) throws Throwable {
        try {
        	// XXX: auv: Entrance: Call go(args)
            go(args);
        } catch (DoneException e) {
            if (Syslog.log != null) {
                Syslog.log.print_exception(e);
            } else {
                System.err.println("Run error - " + e.toString());
            }
        } catch (Throwable e) {
            if (Syslog.log != null) {
                Syslog.log.print_exception(e);
            } else {
                throw e;
            }
        }

    }
}
