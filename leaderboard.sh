#!/bin/sh

response=$(curl -s -H "Authorization: Bearer $(cat token.txt)" \
     "https://group.us-east-1.api.cloudquest.skillbuilder.aws/v1/codegroup/de14f7ae-9871-4eb7-8805-84cb6a3056fb/leaderboard")

# Check if response contains "UNAUTHORIZED"
if echo "$response" | grep -q '"message": "UNAUTHORIZED"'; then
    echo "❌ Unauthorized request. Skipping output.json update."
    exit 1
fi

# Write to output.json only if authorized
echo "$response" > output.json

