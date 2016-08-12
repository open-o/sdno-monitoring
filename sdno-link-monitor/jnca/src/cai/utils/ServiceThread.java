package cai.utils;

public abstract class ServiceThread extends Thread {
	protected Object o;

	String start, stop;

	Syslog syslog;

	public ServiceThread(Object o, Syslog syslog, String start, String stop) {
		this.o = o;
		this.syslog = syslog;
		this.start = start;
		this.stop = stop;
	}

	public void run() {
		syslog.syslog(Syslog.LOG_NOTICE, "START: " + getName() + ", " + start);

		try {
			exec();
		} catch (Throwable e) {
			syslog.print_exception(e);
		}

		syslog.syslog(Syslog.LOG_NOTICE, "STOP: " + getName() + ", " + stop);
	}

	public abstract void exec() throws Throwable;
}
