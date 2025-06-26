#!/bin/bash

# Test script to create and manage a companion through the Guardian CLI
echo "Creating test companion..."
python3 guardian/cli/guardianctl.py build-companion << EOF
1
1
1
1
John,Sarah,Max
1
s
test_user
EOF

echo -e "\nListing companions..."
python3 guardian/cli/guardianctl.py list-companions

echo -e "\nDeploying companion..."
python3 guardian/cli/guardianctl.py deploy-companion test_user

echo -e "\nListing companions again to verify active status..."
python3 guardian/cli/guardianctl.py list-companions

echo -e "\nDeleting companion..."
python3 guardian/cli/guardianctl.py delete-companion test_user

echo -e "\nVerifying deletion..."
python3 guardian/cli/guardianctl.py list-companions
