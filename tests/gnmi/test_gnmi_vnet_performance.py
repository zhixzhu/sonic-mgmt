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


def create_route_address(first_addr, id):
    address_1 = id % 100
    address_2 = (int(id / 100)) % 100
    address_3 = (int(id / 10000)) % 100
    return "{}.{}.{}.{}/32".format(first_addr, address_3, address_2, address_1)


def create_mapping_address(id):
    address_1 = id % 100
    address_2 = (int(id / 100)) % 100
    address_3 = (int(id / 10000)) % 100
    return "10.{}.{}.{}".format(address_3, address_2, address_1)


def create_appliance(duthost, localhost):
    file_name = "appliance.json"
    update_list = ["/sonic-db:APPL_DB/DASH_APPLIANCE_TABLE/:@%s" % (file_name)]

    # generate config file
    with open(file_name, 'w') as file:
        file.write("{")

        file.write('"123": {')
        file.write('"sip": "10.1.0.32",')
        file.write('"vm_vni": "4321"')
        file.write('}')

        file.write("}")

    ret, msg = gnmi_set(duthost, localhost, [], update_list, [])
    logger.info("gnmi msg: %s", msg)
    assert ret == 0, msg


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


def create_vnet_mapping(duthost, localhost, entry_count):
    file_name = "vnet_mapping.json"
    update_list = ["/sonic-db:APPL_DB/DASH_VNET_MAPPING_TABLE/:@%s" % (file_name)]

    # generate config file
    mapping_count = entry_count
    with open(file_name, 'w') as file:
        file.write("{")

        mapping_id = 1
        while (mapping_id < mapping_count + 1):
            file.write('"Vnet001:{}": {{'.format(create_mapping_address(mapping_id)))
            file.write('"routing_type":"vnet_encap",')
            file.write('"underlay_ip":"101.1.2.3",')
            file.write('"mac_address":"F9-22-83-99-22-A2"')

            if (mapping_id == mapping_count):
                file.write('}')
            else:
                file.write('},')
            mapping_id += 1

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

def create_vnet_route_json(first_addr, entry_count):
    file_name = "vnetroute_{}.json".format(first_addr)

    # generate config file
    route_count = entry_count
    with open(file_name, 'w') as file:
        file.write("{")

        route_id = 1
        while (route_id < route_count + 1):
            file.write('"F4939FEFC47E:{}": {{'.format(create_route_address(first_addr, route_id)))
            file.write('"action_type": "vnet",')
            file.write('"vnet": "Vnet001"')
            if (route_id == route_count):
                file.write('}')
            else:
                file.write('},')
            route_id += 1

        file.write("}")
    
def create_vnet_route(duthost, localhost, first_addr):
    file_name = "vnetroute_{}.json".format(first_addr)
    update_list = ["/sonic-db:APPL_DB/DASH_ROUTE_TABLE/:@%s" % (file_name)]
    ret, msg = gnmi_set(duthost, localhost, [], update_list, [])
    logger.info("gnmi msg: %s", msg)
    assert ret == 0, msg


def test_gnmi_create_vnet_route_performance(duthosts, rand_one_dut_hostname, localhost):
    '''
    Verify GNMI create vnet route performance

    sudo ./run_tests.sh -n vms-kvm-t0 -d vlab-01 -c gnmi/test_gnmi_vnet_performance.py -f vtestbed.csv -i veos_vtb -u  -S 'sub_port_interfaces platform_tests copp show_techport acl everflow drop_packets' -e '--allow_recover --showlocals --assert plain -rav --collect_techsupport=False --deep_clean --sad_case_list=sad_bgp,sad_lag_member,sad_lag,sad_vlan_port'
    '''
    duthost = duthosts[rand_one_dut_hostname]

    create_appliance(duthost, localhost)
    create_vnet(duthost, localhost)

    # wait depency data ready
    time.sleep(10)
    create_vnet_mapping(duthost, localhost, 1)

    create_qos(duthost, localhost)
    create_eni(duthost, localhost)

    # wait depency data ready
    time.sleep(10)

    entry_count = 1000
    batch_count = 100
    first_addr = 1
    while (first_addr <= batch_count):
        create_vnet_route_json(first_addr, entry_count)
        first_addr += 1

    first_addr = 1
    while (first_addr <= batch_count):
        create_vnet_route(duthost, localhost, first_addr)
        first_addr += 1
