# Monitoring for Container - Assignment 3.9

This repository contains the implementation for Assignment 3.9 - Monitoring for Container. The assignment focuses on deploying Prometheus to a shared EKS cluster and creating a menu-driven Python script to manage the deployment and monitoring of resources.

## Overview

This project implements a comprehensive monitoring solution for Kubernetes using Prometheus. It includes:

1. A menu-driven Python script for easy deployment and management
2. Prometheus configuration for monitoring Kubernetes resources
3. Ingress configuration for external access
4. Resource status checking functionality

## Prerequisites

- AWS CLI configured with appropriate permissions
- Access to an EKS cluster
- kubectl installed and configured
- Helm 3 installed

## Quick Start

1. Clone this repository:

   ```bash
   git clone <repository-url>
   cd <repository-directory>
   ```

2. Make the script executable:

   ```bash
   chmod +x k8s_manager.py
   ```

3. Run the script:

   ```bash
   ./k8s_manager.py
   ```

4. Follow the interactive prompts to:
   - Connect to the shared EKS cluster (option 1)
   - Create a namespace with your username (option 2)
   - Deploy Prometheus to your namespace (option 3)
   - Check resource status to monitor your deployment (option 4)
   - Delete resources when needed (option 5)

## Features

### 1. EKS Cluster Connection

- Configure AWS region
- Connect to a specified EKS cluster

### 2. Namespace Management

- Create namespaces with a standardized naming convention
- List and delete namespaces

### 3. Prometheus Deployment

- Deploy Prometheus using Helm
- Configure ingress for external access
- Customize deployment parameters

### 4. Resource Status Monitoring

- Check the status of all resources in a namespace
- View detailed information about specific resources:
  - Pods (with logs)
  - Services
  - Deployments
  - Ingresses
  - Helm releases
  - Events (for troubleshooting)

### 5. Resource Cleanup

- Delete Prometheus deployments
- Delete namespaces and associated resources

## Configuration

The Prometheus deployment uses the following configuration:

```yaml
prometheus-node-exporter:
  enabled: false
kube-state-metrics:
  enabled: false
alertmanager:
  enabled: false
serverFiles:
  prometheus.yml:
    scrape_configs:
      - job_name: prometheus
        static_configs:
          - targets:
              - localhost:9090
      - job_name: node-exporter
        static_configs:
          - targets:
              - kube-prometheus-stack-prometheus-node-exporter.monitoring:9100
      - job_name: nginx
        static_configs:
          - targets:
              - ingress-nginx-controller-metrics.ingress-nginx:10254
server:
  persistentVolume:
    enabled: false
  ingress:
    enabled: true
    ingressClassName: nginx
    hosts:
      - <namespace>.sctp-sandbox.com
    annotations:
      external-dns.alpha.kubernetes.io/hostname: "<namespace>.sctp-sandbox.com"
```

## Accessing Prometheus

After deployment, Prometheus will be accessible at:

```
http://<username>-<purpose>.sctp-sandbox.com
```

For example, if you created a namespace called `azni-prom`, Prometheus will be accessible at:

```
http://azni-prom.sctp-sandbox.com
```

Note: It may take a few minutes for DNS to propagate after deployment.

## Troubleshooting

### Common Issues

1. **Connection Issues**

   - Ensure AWS CLI is configured correctly
   - Verify EKS cluster exists and is accessible

2. **Deployment Failures**

   - Check Kubernetes events: `kubectl get events -n <namespace>`
   - View pod logs: `kubectl logs <pod-name> -n <namespace>`

3. **Ingress Issues**

   - Verify ingress controller is running
   - Check DNS configuration

4. **"Could not resolve host" Error**

   - This is usually due to DNS propagation delays
   - DNS changes can take anywhere from a few minutes to 48 hours to propagate
   - Solutions:

     - Wait for DNS propagation (15-30 minutes)
     - Access via the load balancer URL directly:

       ```
       # Get the load balancer URL
       kubectl get ingress -n <namespace>

       # Access via the load balancer URL
       http://<load-balancer-url>
       ```

     - Add an entry to your local hosts file:

       ```
       # Get the load balancer IP
       nslookup <load-balancer-url>

       # Add to hosts file
       <load-balancer-ip> <hostname>
       ```

5. **NGINX 404 Error**

   - This occurs when accessing the load balancer URL directly without the correct host header
   - The NGINX ingress controller uses host-based routing to determine which service to route to
   - Solutions:

     - Add an entry to your hosts file (as described above) and access using the hostname
     - Use curl with the correct host header:

       ```
       curl -H "Host: <hostname>" http://<load-balancer-url>
       ```

     - Use a browser extension like "ModHeader" to set the Host header when accessing the load balancer URL
     - If you're seeing a 404 error when accessing with the correct hostname, check that:
       - The ingress resource is correctly configured
       - The backend service and pods are running
       - The service has endpoints

### Viewing Logs

To view logs for Prometheus pods:

```bash
kubectl logs -f <prometheus-pod-name> -n <namespace>
```

## Extending the Solution

This solution can be extended in several ways:

1. **Add Grafana for Visualization**

   - Deploy Grafana alongside Prometheus
   - Configure dashboards for Kubernetes monitoring

2. **Implement Alerting**

   - Enable AlertManager
   - Configure alert rules and notification channels

3. **Add Custom Exporters**
   - Deploy additional exporters for specific applications
   - Configure Prometheus to scrape these exporters

## Assignment Requirements

This implementation fulfills the following requirements:

1. **Connect to Shared EKS Cluster**

   - Script connects to the shared EKS cluster (`shared-eks-cluster`) in the specified region (`us-east-1`)

2. **Create Custom Namespace**

   - Script prompts for namespace name rather than using defaults
   - Follows the naming convention `<username>-<purpose>`

3. **Deploy Prometheus**

   - Uses Helm to deploy Prometheus
   - Configures ingress for external access
   - Sets up appropriate scrape configurations

4. **Check Resource Status**

   - Added menu option to check the status of provisioned resources
   - Provides detailed information about various resource types

5. **Resource Management**
   - Ability to delete resources when needed
   - Confirmation prompts to prevent accidental deletion

## Author

Azni Osman
