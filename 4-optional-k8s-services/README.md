**WIP**
Zipkin - installed by default with dapr - access in http://localhost:9411 
# we need to create a zipkin configuration for each namespace
# namespaces mut be created in advance
# otherwise daprd and zipking does not work fine together

# https://docs.dapr.io/operations/observability/tracing/tracing-overview/
# see https://docs.dapr.io/operations/observability/tracing/zipkin/
# https://zipkin.io/


Prometheus  https://docs.dapr.io/operations/observability/metrics/prometheus/


helm install dapr-prom prometheus-community/prometheus -f values.yaml -n dapr-monitoring --create-namespace
NAME: dapr-prom
LAST DEPLOYED: Tue Aug 12 18:09:45 2025
NAMESPACE: dapr-monitoring
STATUS: deployed
REVISION: 1
TEST SUITE: None
NOTES:
The Prometheus server can be accessed via port 80 on the following DNS name from within your cluster:
dapr-prom-prometheus-server.dapr-monitoring.svc.cluster.local


Get the Prometheus server URL by running these commands in the same shell:
  export POD_NAME=$(kubectl get pods --namespace dapr-monitoring -l "app.kubernetes.io/name=prometheus,app.kubernetes.io/instance=dapr-prom" -o jsonpath="{.items[0].metadata.name}")
  kubectl --namespace dapr-monitoring port-forward $POD_NAME 9090
#################################################################################
######   WARNING: Persistence is disabled!!! You will lose your data when   #####
######            the Server pod is terminated.                             #####
#################################################################################


The Prometheus alertmanager can be accessed via port 9093 on the following DNS name from within your cluster:
dapr-prom-alertmanager.dapr-monitoring.svc.cluster.local


Get the Alertmanager URL by running these commands in the same shell:
  export POD_NAME=$(kubectl get pods --namespace dapr-monitoring -l "app.kubernetes.io/name=alertmanager,app.kubernetes.io/instance=dapr-prom" -o jsonpath="{.items[0].metadata.name}")
  kubectl --namespace dapr-monitoring port-forward $POD_NAME 9093
#################################################################################
######   WARNING: Persistence is disabled!!! You will lose your data when   #####
######            the AlertManager pod is terminated.                       #####
#################################################################################
#################################################################################
######   WARNING: Pod Security Policy has been disabled by default since    #####
######            it deprecated after k8s 1.25+. use                        #####
######            (index .Values "prometheus-node-exporter" "rbac"          #####
###### .          "pspEnabled") with (index .Values                         #####
######            "prometheus-node-exporter" "rbac" "pspAnnotations")       #####
######            in case you still need it.                                #####
#################################################################################


The Prometheus PushGateway can be accessed via port 9091 on the following DNS name from within your cluster:
dapr-prom-prometheus-pushgateway.dapr-monitoring.svc.cluster.local


Get the PushGateway URL by running these commands in the same shell:
  export POD_NAME=$(kubectl get pods --namespace dapr-monitoring -l "app=prometheus-pushgateway,component=pushgateway" -o jsonpath="{.items[0].metadata.name}")
  kubectl --namespace dapr-monitoring port-forward $POD_NAME 9091

For more information on running Prometheus, visit:
https://prometheus.io/



GitOps ArgoCD
**WIP**