__author__ = 'chenhg'

from tornado.testing import *
from base_handler import *
import time
import os
import subprocess
topo_serv_cmd = 'coverage run --parallel-mode topo_serv.py'
test_serv_cmd = 'coverage run --parallel-mode test.py'
fake_openo_serv_cmd = 'coverage run --parallel-mode fake_openo.py'
# topo_server_cmd = 'coverage run --parallel-mode topo_server.py'
# cus_server_cmd = 'coverage run --parallel-mode customer_server.py'
# snmp_server_cmd = 'coverage run --parallel-mode snmp.py' #
# netflow_server_cmd = 'coverage run --parallel-mode netflow.py' #
# os.system(command)

monitoring_prefix_vlinks_uri = r'http://127.0.0.1:8610/openoapi/sdnomonitoring/v1/vlinks'
monitoring_prefix_flow_uri = r'http://127.0.0.1:8610/openoapi/sdnomonitoring/v1/flows'
#node ids
monitoring_node_uri_param = '0'

class Test_Monitoring(AsyncTestCase):
    def setUp(self):
        super(Test_Monitoring,self).setUp()
        pass

    def tearDown(self):
        super(Test_Monitoring,self).tearDown()

    @tornado.testing.gen_test
    def test_b_get_node_flow(self):
        code, resp = yield base_handler.do_json_get(monitoring_prefix_flow_uri + '/' + monitoring_node_uri_param)
        print('test_get_node_flow:')
        self.assertEqual(200, code, 'FAIL:test_get_node_flow error')

    @tornado.testing.gen_test
    def test_a_get_vlinks(self):
        code, resp = yield base_handler.do_json_get(monitoring_prefix_vlinks_uri)
        print('test_get_vlinks:')
        self.assertIn('vlinks', resp, 'FAIL:test_get_vlinks, key \'vlinks\' not found')

if __name__ == '__main__':
    print '---Service Started....'
    # os.system('coverage erase')
    topo_serv = subprocess.Popen(topo_serv_cmd, shell=True)
    test_serv = subprocess.Popen(test_serv_cmd, shell=True)
    fake_serv = subprocess.Popen(fake_openo_serv_cmd, shell=True)
    time.sleep(3)
    suite = unittest.TestLoader().loadTestsFromTestCase(Test_Monitoring)
    unittest.TextTestRunner(verbosity=2).run(suite)
    try:
        print '---Service Terminated...'
        sig = 2 #signal.SIGINT
        topo_serv.send_signal(sig)
        test_serv.send_signal(sig)
        fake_serv.send_signal(sig)
        print '@@@Service Terminated...'
        pass
    except:
        print '*****Service Terminated...'
        traceback.print_exc()
        pass
    # subprocess.Popen('tskill python & tskill python & tskill python', shell=True)
    # os.system('coverage combine & coverage html')
    print '+++Service Terminated...'
