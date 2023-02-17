import json
import logging
import pytest
import re

from helper import gnmi_set, gnmi_get, gnoi_reboot
from tests.common.helpers.assertions import pytest_assert
from tests.common.utilities import wait_until
from tests.common.platform.processes_utils import wait_critical_processes
from tests.common.platform.interface_utils import check_interface_status_of_up_ports

logger = logging.getLogger(__name__)

pytestmark = [
    pytest.mark.topology('any'),
    pytest.mark.disable_loganalyzer
]

def test_gnmi_create_vnet_route_performance(duthosts, rand_one_dut_hostname, localhost):
    '''
    Verify GNMI create vnet route performance
    '''
    duthost = duthosts[rand_one_dut_hostname]
    file_name = "vnetroute.json"
    update_list = ["/sonic-db:APPL_DB/DASH_ROUTE_TABLE/：@%s" % (file_name)]

    ret, msg = gnmi_set(duthost, localhost, [], update_list, [])
    assert ret == 0, msg

