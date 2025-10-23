#!/bin/bash
set -e

# Test script to create and manage a companion through the Guardian CLI
echo "Creating test companion..."
poetry run guardianctl build-companion << EOF
1
1
1
1
John,Sarah,Max
1
test_companion
s
test_user
EOF

echo -e "\nListing companions..."
poetry run guardianctl list-companions

echo -e "\nDeploying companion..."
poetry run guardianctl deploy-companion test_user

echo -e "\nListing companions again to verify active status..."
poetry run guardianctl list-companions

echo -e "\nDeleting companion..."
poetry run guardianctl delete-companion test_user

echo -e "\nVerifying deletion..."
poetry run guardianctl list-companions
