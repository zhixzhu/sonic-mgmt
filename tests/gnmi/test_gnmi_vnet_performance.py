import json
import logging
import pytest
import re
import uuid
import time

from helper import gnmi_set, apply_cert_config
from tests.common.helpers.assertions import pytest_assert
from tests.common.utilities import wait_until
from tests.common.platform.processes_utils import wait_critical_processes
from tests.common.platform.interface_utils import check_interface_status_of_up_ports

logger = logging.getLogger(__name__)

pytestmark = [
    pytest.mark.topology('any'),
    pytest.mark.disable_loganalyzer
]


def create_route_address(id):
    address_1 = id % 100
    address_2 = (int(id / 100)) % 100
    address_3 = (int(id / 10000)) % 100
    return "10.{}.{}.{}/32".format(address_3, address_2, address_1)


def create_vnet(duthost, localhost):
    file_name = "vnet.json"
    update_list = ["/sonic-db:APPL_DB/DASH_VNET_TABLE/:@%s" % (file_name)]

    # generate config file
    with open(file_name, 'w') as file:
        file.write("{")

        file.write('"Vnet001": {')
        file.write('"guid": "{}",'.format(uuid.uuid4()))
        file.write('"vni": "45654"')
        file.write('}')

        file.write("}")

    ret, msg = gnmi_set(duthost, localhost, [], update_list, [])
    logger.info("gnmi msg: %s", msg)
    assert ret == 0, msg


def create_qos(duthost, localhost):
    file_name = "qos.json"
    update_list = ["/sonic-db:APPL_DB/DASH_QOS_TABLE/:@%s" % (file_name)]

    # generate config file
    with open(file_name, 'w') as file:
        file.write("{")

        file.write('"qos100": {')
        file.write('"qos_id":"100",')
        file.write('"bw":"10000",')
        file.write('"cps":"1000",')
        file.write('"flows":"10"')
        file.write('}')

        file.write("}")

    ret, msg = gnmi_set(duthost, localhost, [], update_list, [])
    logger.info("gnmi msg: %s", msg)
    assert ret == 0, msg


def create_eni(duthost, localhost):
    file_name = "eni.json"
    update_list = ["/sonic-db:APPL_DB/DASH_ENI_TABLE/:@%s" % (file_name)]

    # generate config file
    with open(file_name, 'w') as file:
        file.write("{")

        file.write('"F4939FEFC47E": {')
        file.write('"eni_id":"497f23d7-f0ac-4c99-a98f-59b470e8c7bd",')
        file.write('"mac_address":"F4:93:9F:EF:C4:7E",')
        file.write('"underlay_ip":"25.1.1.1",')
        file.write('"admin_state":"enabled",')
        file.write('"vnet":"Vnet001",')
        file.write('"qos":"qos100"')
        file.write('}')

        file.write("}")

    ret, msg = gnmi_set(duthost, localhost, [], update_list, [])
    logger.info("gnmi msg: %s", msg)
    assert ret == 0, msg

def create_vnet_route(duthost, localhost, entry_count):
    file_name = "vnetroute.json"
    update_list = ["/sonic-db:APPL_DB/DASH_ROUTE_TABLE/:@%s" % (file_name)]

    # generate config file
    route_count = entry_count
    with open(file_name, 'w') as file:
        file.write("{")

        route_id = 1
        while (route_id < route_count + 1):
            file.write('"F4939FEFC47E:{}": {{'.format(create_route_address(route_id)))
            file.write('"action_type": "vnet",')
            file.write('"vnet": "Vnet001"')
            if (route_id == route_count):
                file.write('}')
            else:
                file.write('},')
            route_id += 1

        file.write("}")

    ret, msg = gnmi_set(duthost, localhost, [], update_list, [])
    logger.info("gnmi msg: %s", msg)
    assert ret == 0, msg


def test_gnmi_create_vnet_route_performance(duthosts, rand_one_dut_hostname, localhost):
    '''
    Verify GNMI create vnet route performance

    sudo ./run_tests.sh -n vms-kvm-t0 -d vlab-01 -c gnmi/test_gnmi_vnet_performance.py -f vtestbed.csv -i veos_vtb -u  -S 'sub_port_interfaces platform_tests copp show_techport acl everflow drop_packets' -e '--allow_recover --showlocals --assert plain -rav --collect_techsupport=False --deep_clean --sad_case_list=sad_bgp,sad_lag_member,sad_lag,sad_vlan_port'
    '''
    duthost = duthosts[rand_one_dut_hostname]
    entry_count = 1000

    create_vnet(duthost, localhost)
    create_qos(duthost, localhost)
    create_eni(duthost, localhost)

    # wait depency data ready and start create route
    time.sleep(10)
    create_vnet_route(duthost, localhost, entry_count)
