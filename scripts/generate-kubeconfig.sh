#!/bin/bash

################################################################################
# Script: generate_kubeconfig.sh
#
# Description:
#   This script exports the current OpenShift or Kubernetes user's kubeconfig
#   context to a separate file named "kubeconfig.yaml" in the current directory.
#   It is useful for generating a minimal kubeconfig suitable for sharing with
#   other tools, such as Krkn-AI or for use in CI/CD pipelines. The script prints
#   the details of the exported configuration (cluster, user, and context) for verification.
#
# Usage:
#   Run the script in your terminal:
#     ./scripts/generate_kubeconfig.sh
#
#   This requires:
#     - OpenShift CLI (oc) or compatible Kubernetes CLI in PATH.
#     - Access to a current, logged-in kubeconfig context.
#
# Output:
#   - kubeconfig.yaml: A minimal kubeconfig file for the current context, in the current directory.
#   - Prints the current cluster, user, and context information.
################################################################################

# Output kubeconfig path
OUTPUT_KUBECONFIG="kubeconfig.yaml"

# Get current kubeconfig context details
CURRENT_USER=$(oc whoami)
CURRENT_CLUSTER=$(oc config view --minify -o jsonpath='{.clusters[0].name}')
CURRENT_CONTEXT=$(oc config current-context)

# Export kubeconfig to a new file
oc config view --minify --flatten > "$OUTPUT_KUBECONFIG"

echo "Kubeconfig exported to $OUTPUT_KUBECONFIG"
echo "Cluster: $CURRENT_CLUSTER"
echo "User: $CURRENT_USER"
echo "Context: $CURRENT_CONTEXT"
