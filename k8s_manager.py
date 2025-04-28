#!/usr/bin/env python3
"""
Kubernetes Resource Manager Script
This script provides a menu-driven interface to manage Kubernetes resources,
specifically for deploying and deleting Prometheus in an EKS cluster.
"""

import os
import sys
import subprocess
import time

# ANSI color codes for better readability
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def print_header(text):
    """Print a formatted header."""
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'=' * 60}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{text.center(60)}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{'=' * 60}{Colors.ENDC}\n")

def print_success(text):
    """Print a success message."""
    print(f"{Colors.GREEN}{Colors.BOLD}✓ {text}{Colors.ENDC}")

def print_error(text):
    """Print an error message."""
    print(f"{Colors.RED}{Colors.BOLD}✗ {text}{Colors.ENDC}")

def print_info(text):
    """Print an info message."""
    print(f"{Colors.BLUE}ℹ {text}{Colors.ENDC}")

def print_warning(text):
    """Print a warning message."""
    print(f"{Colors.YELLOW}⚠ {text}{Colors.ENDC}")

def run_command(command, show_output=True):
    """Run a shell command and return the result."""
    try:
        print_info(f"Running: {command}")
        result = subprocess.run(command, shell=True, check=True,
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                               text=True)
        if show_output and result.stdout:
            print(result.stdout)
        return True, result.stdout
    except subprocess.CalledProcessError as e:
        print_error(f"Command failed with exit code {e.returncode}")
        if e.stderr:
            print_error(f"Error: {e.stderr}")
        if e.stdout and show_output:
            print(e.stdout)
        return False, e.stderr
    except Exception as e:
        print_error(f"An error occurred: {str(e)}")
        return False, str(e)

def connect_to_eks_cluster():
    """Connect to the EKS cluster."""
    print_header("Connecting to EKS Cluster")

    # Set AWS region
    region = input("Enter AWS region (default: us-east-1): ") or "us-east-1"
    success, _ = run_command(f"aws configure set region {region}")
    if not success:
        return False

    # Get cluster name
    cluster_name = input("Enter EKS cluster name (default: shared-eks-cluster): ") or "shared-eks-cluster"

    # Update kubeconfig
    success, _ = run_command(f"aws eks update-kubeconfig --name {cluster_name} --region {region}")
    if success:
        print_success(f"Successfully connected to EKS cluster: {cluster_name}")
        return True
    else:
        print_error(f"Failed to connect to EKS cluster: {cluster_name}")
        return False

def create_namespace():
    """Create a Kubernetes namespace."""
    print_header("Creating Kubernetes Namespace")

    # Get username or identifier
    username = input("Enter your username or identifier (e.g., 'azni'): ")
    if not username:
        print_error("Username cannot be empty")
        return False

    # Get namespace purpose
    purpose = input("Enter namespace purpose (e.g., 'eks', 'prom', 'app'): ")
    if not purpose:
        print_error("Purpose cannot be empty")
        return False

    # Generate namespace name
    namespace = f"{username}-{purpose}"
    print_info(f"Generated namespace name: {namespace}")

    # Confirm namespace creation
    confirm = input(f"Create namespace '{namespace}'? (y/n): ")
    if confirm.lower() != "y":
        print_info("Namespace creation cancelled")
        return False

    # Create namespace
    success, _ = run_command(f"kubectl create namespace {namespace}")
    if success:
        print_success(f"Successfully created namespace: {namespace}")
        return True
    else:
        print_error(f"Failed to create namespace: {namespace}")
        return False

def deploy_prometheus():
    """Deploy Prometheus using Helm."""
    print_header("Deploying Prometheus")

    # Check if Helm is installed
    success, _ = run_command("helm version", show_output=False)
    if not success:
        print_warning("Helm is not installed. Installing Helm...")
        success, _ = run_command("curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash")
        if not success:
            print_error("Failed to install Helm")
            return False
        print_success("Helm installed successfully")

    # Add Prometheus Helm repository
    success, _ = run_command("helm repo add prometheus-community https://prometheus-community.github.io/helm-charts")
    if not success:
        print_error("Failed to add Prometheus Helm repository")
        return False

    # Update Helm repositories
    success, _ = run_command("helm repo update")
    if not success:
        print_error("Failed to update Helm repositories")
        return False

    # Get available namespaces
    print_info("Fetching available namespaces...")
    success, output = run_command("kubectl get namespaces -o custom-columns=NAME:.metadata.name --no-headers", show_output=False)

    if success and output:
        namespaces = output.strip().split('\n')
        print_info("Available namespaces:")
        for i, ns in enumerate(namespaces, 1):
            print(f"{i}. {ns}")

        # Get namespace selection
        selection = input("\nEnter namespace number or name for Prometheus deployment: ")

        # Check if selection is a number
        if selection.isdigit() and 1 <= int(selection) <= len(namespaces):
            namespace = namespaces[int(selection) - 1]
        else:
            namespace = selection
    else:
        namespace = input("Enter namespace for Prometheus deployment: ")

    if not namespace:
        print_error("Namespace cannot be empty")
        return False

    print_info(f"Using namespace: {namespace}")

    # Get release name
    release_name = input(f"Enter Prometheus release name (default: {namespace}-prom): ") or f"{namespace}-prom"

    # Check if values file exists
    values_file = "prometheus-values.yaml"
    if not os.path.exists(values_file):
        print_warning(f"Values file {values_file} not found. Creating a default values file...")

        # Get hostname for ingress
        hostname = input(f"Enter hostname for Prometheus ingress (default: {namespace}.sctp-sandbox.com): ") or f"{namespace}.sctp-sandbox.com"

        # Create default values file
        with open(values_file, "w") as f:
            f.write(f"""prometheus-node-exporter:
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
      - {hostname}
    annotations:
      external-dns.alpha.kubernetes.io/hostname: "{hostname}"
""")
        print_success(f"Created default values file: {values_file}")
    else:
        # Update hostname in values file
        hostname = input(f"Enter hostname for Prometheus ingress (default: {namespace}.sctp-sandbox.com): ") or f"{namespace}.sctp-sandbox.com"

        # Read the current values file
        with open(values_file, "r") as f:
            content = f.read()

        # Update the hostname
        import re
        content = re.sub(r'hosts:\s*\n\s*- .*', f'hosts:\n      - {hostname}', content)
        content = re.sub(r'external-dns.alpha.kubernetes.io/hostname: ".*"', f'external-dns.alpha.kubernetes.io/hostname: "{hostname}"', content)

        # Write the updated values file
        with open(values_file, "w") as f:
            f.write(content)

        print_success(f"Updated values file with hostname: {hostname}")

    # Deploy Prometheus
    print_info("Deploying Prometheus...")
    success, _ = run_command(f"helm upgrade --install {release_name} prometheus-community/prometheus --version 27.5.1 --values {values_file} --namespace {namespace}")

    if success:
        print_success(f"Successfully deployed Prometheus to namespace: {namespace}")
        print_info(f"Prometheus will be accessible at: http://{hostname}")

        # Check deployment status
        print_info("Checking deployment status...")
        time.sleep(5)  # Give some time for the pods to start
        run_command(f"kubectl get pods -n {namespace}")
        run_command(f"kubectl get svc -n {namespace}")
        run_command(f"kubectl get ingress -n {namespace}")

        return True
    else:
        print_error(f"Failed to deploy Prometheus to namespace: {namespace}")
        return False

def delete_resources():
    """Delete Kubernetes resources."""
    print_header("Deleting Kubernetes Resources")

    # Show menu for deletion options
    print("1. Delete Prometheus deployment")
    print("2. Delete namespace")
    print("3. Back to main menu")

    choice = input("\nEnter your choice (1-3): ")

    if choice == "1":
        # Get available namespaces
        print_info("Fetching available namespaces...")
        success, output = run_command("kubectl get namespaces -o custom-columns=NAME:.metadata.name --no-headers", show_output=False)

        if success and output:
            namespaces = output.strip().split('\n')
            print_info("Available namespaces:")
            for i, ns in enumerate(namespaces, 1):
                print(f"{i}. {ns}")

            # Get namespace selection
            selection = input("\nEnter namespace number or name containing Prometheus deployment: ")

            # Check if selection is a number
            if selection.isdigit() and 1 <= int(selection) <= len(namespaces):
                namespace = namespaces[int(selection) - 1]
            else:
                namespace = selection
        else:
            namespace = input("Enter namespace containing Prometheus deployment: ")

        if not namespace:
            print_error("Namespace cannot be empty")
            return False

        print_info(f"Using namespace: {namespace}")

        # Get Helm releases in the namespace
        print_info(f"Fetching Helm releases in namespace '{namespace}'...")
        success, output = run_command(f"helm list -n {namespace} -o json", show_output=False)

        if success and output and output.strip() != "[]":
            import json
            try:
                releases = json.loads(output)
                print_info("Available Helm releases:")
                for i, release in enumerate(releases, 1):
                    print(f"{i}. {release['name']} (Chart: {release['chart']})")

                # Get release selection
                selection = input("\nEnter release number or name to delete: ")

                # Check if selection is a number
                if selection.isdigit() and 1 <= int(selection) <= len(releases):
                    release_name = releases[int(selection) - 1]['name']
                else:
                    release_name = selection
            except json.JSONDecodeError:
                release_name = input(f"Enter Prometheus release name (default: {namespace}-prom): ") or f"{namespace}-prom"
        else:
            release_name = input(f"Enter Prometheus release name (default: {namespace}-prom): ") or f"{namespace}-prom"

        success, _ = run_command(f"helm uninstall {release_name} --namespace {namespace}")
        if success:
            print_success(f"Successfully deleted Prometheus deployment: {release_name}")
            return True
        else:
            print_error(f"Failed to delete Prometheus deployment: {release_name}")
            return False

    elif choice == "2":
        # Get available namespaces
        print_info("Fetching available namespaces...")
        success, output = run_command("kubectl get namespaces -o custom-columns=NAME:.metadata.name --no-headers", show_output=False)

        if success and output:
            namespaces = output.strip().split('\n')
            print_info("Available namespaces:")
            for i, ns in enumerate(namespaces, 1):
                print(f"{i}. {ns}")

            # Get namespace selection
            selection = input("\nEnter namespace number or name to delete: ")

            # Check if selection is a number
            if selection.isdigit() and 1 <= int(selection) <= len(namespaces):
                namespace = namespaces[int(selection) - 1]
            else:
                namespace = selection
        else:
            namespace = input("Enter namespace to delete: ")

        if not namespace:
            print_error("Namespace cannot be empty")
            return False

        print_info(f"Selected namespace: {namespace}")

        # Show resources in the namespace
        print_info(f"Resources in namespace '{namespace}':")
        run_command(f"kubectl get all -n {namespace}")

        # Confirm deletion
        confirm = input(f"\n{Colors.RED}{Colors.BOLD}WARNING: Are you sure you want to delete namespace '{namespace}'?{Colors.ENDC}\nThis will delete ALL resources in the namespace and CANNOT be undone. (yes/no): ")
        if confirm.lower() != "yes":
            print_info("Namespace deletion cancelled")
            return False

        success, _ = run_command(f"kubectl delete namespace {namespace}")
        if success:
            print_success(f"Successfully deleted namespace: {namespace}")
            return True
        else:
            print_error(f"Failed to delete namespace: {namespace}")
            return False

    elif choice == "3":
        return True

    else:
        print_error("Invalid choice")
        return False

def check_resource_status():
    """Check the status of provisioned resources."""
    print_header("Resource Status Check")

    # Get available namespaces
    print_info("Fetching available namespaces...")
    success, output = run_command("kubectl get namespaces -o custom-columns=NAME:.metadata.name --no-headers", show_output=False)

    if success and output:
        namespaces = output.strip().split('\n')
        print_info("Available namespaces:")
        for i, ns in enumerate(namespaces, 1):
            print(f"{i}. {ns}")

        # Get namespace selection
        selection = input("\nEnter namespace number or name to check: ")

        # Check if selection is a number
        if selection.isdigit() and 1 <= int(selection) <= len(namespaces):
            namespace = namespaces[int(selection) - 1]
        else:
            namespace = selection
    else:
        namespace = input("Enter namespace to check: ")

    if not namespace:
        print_error("Namespace cannot be empty")
        return False

    print_info(f"Checking resources in namespace: {namespace}")

    # Show menu for resource types
    print("\nSelect resource type to check:")
    print("1. All resources (summary)")
    print("2. Pods")
    print("3. Services")
    print("4. Deployments")
    print("5. Ingresses")
    print("6. Helm releases")
    print("7. Events (useful for troubleshooting)")

    resource_choice = input("\nEnter your choice (1-7): ")

    if resource_choice == "1":
        print_info(f"All resources in namespace '{namespace}':")
        run_command(f"kubectl get all -n {namespace}")
        run_command(f"kubectl get ingress -n {namespace}")
        run_command(f"helm list -n {namespace}")
    elif resource_choice == "2":
        print_info(f"Pods in namespace '{namespace}':")
        run_command(f"kubectl get pods -n {namespace}")

        # Ask if user wants to see details of a specific pod
        pod_details = input("\nEnter pod name to see details (or press Enter to skip): ")
        if pod_details:
            run_command(f"kubectl describe pod {pod_details} -n {namespace}")

            # Ask if user wants to see logs
            show_logs = input("\nDo you want to see logs for this pod? (y/n): ")
            if show_logs.lower() == "y":
                run_command(f"kubectl logs {pod_details} -n {namespace}")
    elif resource_choice == "3":
        print_info(f"Services in namespace '{namespace}':")
        run_command(f"kubectl get svc -n {namespace}")

        # Ask if user wants to see details of a specific service
        svc_details = input("\nEnter service name to see details (or press Enter to skip): ")
        if svc_details:
            run_command(f"kubectl describe svc {svc_details} -n {namespace}")
    elif resource_choice == "4":
        print_info(f"Deployments in namespace '{namespace}':")
        run_command(f"kubectl get deployments -n {namespace}")

        # Ask if user wants to see details of a specific deployment
        deploy_details = input("\nEnter deployment name to see details (or press Enter to skip): ")
        if deploy_details:
            run_command(f"kubectl describe deployment {deploy_details} -n {namespace}")
    elif resource_choice == "5":
        print_info(f"Ingresses in namespace '{namespace}':")
        run_command(f"kubectl get ingress -n {namespace}")

        # Ask if user wants to see details of a specific ingress
        ing_details = input("\nEnter ingress name to see details (or press Enter to skip): ")
        if ing_details:
            run_command(f"kubectl describe ingress {ing_details} -n {namespace}")
    elif resource_choice == "6":
        print_info(f"Helm releases in namespace '{namespace}':")
        run_command(f"helm list -n {namespace}")

        # Ask if user wants to see details of a specific release
        release_details = input("\nEnter release name to see details (or press Enter to skip): ")
        if release_details:
            run_command(f"helm status {release_details} -n {namespace}")
    elif resource_choice == "7":
        print_info(f"Events in namespace '{namespace}' (most recent first):")
        run_command(f"kubectl get events --sort-by=.metadata.creationTimestamp -n {namespace}")
    else:
        print_error("Invalid choice")

    return True

def main_menu():
    """Display the main menu and handle user input."""
    while True:
        print_header("Kubernetes Resource Manager")

        print("1. Connect to EKS Cluster")
        print("2. Create Namespace")
        print("3. Deploy Prometheus")
        print("4. Check Resource Status")
        print("5. Delete Resources")
        print("6. Exit")

        choice = input("\nEnter your choice (1-6): ")

        if choice == "1":
            connect_to_eks_cluster()
        elif choice == "2":
            create_namespace()
        elif choice == "3":
            deploy_prometheus()
        elif choice == "4":
            check_resource_status()
        elif choice == "5":
            delete_resources()
        elif choice == "6":
            print_info("Exiting...")
            sys.exit(0)
        else:
            print_error("Invalid choice")

        input("\nPress Enter to continue...")

if __name__ == "__main__":
    try:
        main_menu()
    except KeyboardInterrupt:
        print("\n")
        print_info("Operation cancelled by user")
        sys.exit(0)
