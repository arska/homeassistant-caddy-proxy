from kubernetes import client, config
import os
import logging
import requests
import pprint
import re
from datetime import datetime

LOGFORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
logging.basicConfig(level=logging.INFO, format=LOGFORMAT)

namespace = "aarno-srf2spotify"
configmap = "homeassistant-caddy-proxy"
mapkey = "Caddyfile"
deploymentconfig = "caddy"

# Configs can be set in Configuration class directly or using helper utility
config.load_kube_config()
coreapi = client.CoreV1Api()

tunnels = requests.get("http://127.0.0.1:4040/api/tunnels").json()
url = [tunnel["public_url"] for tunnel in tunnels["tunnels"] if tunnel["public_url"].startswith("https")][0]

logging.debug(url)

cfmap = coreapi.read_namespaced_config_map(namespace=namespace, name=configmap)

logging.debug(cfmap)

if not url in cfmap.data[mapkey]:
    logging.info("url not found, updating configmap")
    patch = {"data": {mapkey: re.sub("https://[\w\.]+", url, cfmap.data[mapkey])}}
    api_response = coreapi.patch_namespaced_config_map(namespace=namespace, name=configmap, body=patch)
    logging.debug(api_response)
    print("updating DeploymentConfig to trigger re-deployment and loading of new config")
    customapi = client.CustomObjectsApi()
    patch = {'spec': {'template': {'metadata': {'annotations': {'kubectl.kubernetes.io/restartedAt': datetime.now().isoformat()}}}}}
    api_response = customapi.patch_namespaced_custom_object(namespace=namespace, name=deploymentconfig, group="apps.openshift.io", version="v1", plural="deploymentconfigs", body=patch)
    logging.debug(api_response)
else:
    logging.info("url found in configmap, not updating")

