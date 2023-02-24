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


def create_vnet(duthost, localhost, entry_count):
    file_name = "vnet.json"
    update_list = ["/sonic-db:APPL_DB/DASH_VNET_TABLE/:@%s" % (file_name)]

    # generate config file
    route_count = entry_count
    with open(file_name, 'w') as file:
        file.write("{")

        vnet_id = 1
        while (vnet_id < route_count + 1):
            file.write('"Vnet00{}": {{'.format(vnet_id))
            file.write('"guid": "{}",'.format(uuid.uuid4()))
            file.write('"vni": "{}"'.format(vnet_id))

            if (vnet_id == route_count):
                file.write('}')
            else:
                file.write('},')

            vnet_id += 1

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
            file.write('"vnet": "Vnet00{}"'.format(route_id))
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

    create_vnet(duthost, localhost, entry_count)

    # wait depency data ready and start create route
    time.sleep(10)
    create_vnet_route(duthost, localhost, entry_count)
