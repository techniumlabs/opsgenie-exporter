import httpx
import json
import time
import base64
import opsgenie_sdk
from prometheus_client import start_http_server
from prometheus_client.core import REGISTRY, GaugeMetricFamily
from dynaconf import settings, LazySettings
settings = LazySettings(ENVVAR_PREFIX_FOR_DYNACONF='OPSGENIE')

class Opsgenie():
    def __init__(self, apikey):
        self.conf = opsgenie_sdk.configuration.Configuration()
        self.conf.api_key['Authorization'] = apikey

        self.api_client = opsgenie_sdk.api_client.ApiClient(configuration=self.conf)
        self.alert_api = opsgenie_sdk.AlertApi(api_client=self.api_client)

    def alerts(self, integration = None):
        if integration == None:
            query = f'status:open and integration.name:{integration}'
        else:
            query = f'status:open and integration.name:{integration}'
        try:
            list_response = self.alert_api.list_alerts(limit=100, offset=0, sort='updatedAt', order='asc', search_identifier_type='name', query=query)
            return list_response
        except ApiException as err:
            print("Exception when calling AlertApi->list_alerts: %s\n" % err)


class OpsgenieCollector():
    def __init__(self, opsgenie, integrations):
        self.opsgenie = opsgenie
        self.integrations = integrations

    def collect(self):
        labels = ['name', 'priority', 'ack_status']
        gauge = GaugeMetricFamily('opsgenie_alerts', "count", value=None, labels=labels)
        for integration in self.integrations:
            alerts = self.opsgenie.alerts(integration)
            for priority in ['P1', 'P2', 'P3', 'P4', 'P5']:
                for ack_status in [False, True]:
                    labelvalues = [integration, priority, str(ack_status)]
                    gauge.add_metric(labelvalues, len(list(filter(lambda elem: elem.acknowledged == ack_status and elem.priority == priority, alerts.data))))
        yield gauge

def setup():
    m = Opsgenie(settings.APIKEY)
    REGISTRY.register(OpsgenieCollector(m, settings.INTEGRATIONS.split(',')))
    start_http_server(8000)

if __name__ == '__main__':
    setup()
    while True:
        time.sleep(1)
