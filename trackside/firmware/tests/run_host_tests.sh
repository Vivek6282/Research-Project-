#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SHARED_DIR="$SCRIPT_DIR/../shared"

echo "Building protocol security tests with g++..."
g++ -std=c++11 -Wall -Wextra -Werror -I"$SHARED_DIR" "$SCRIPT_DIR/test_protocol.cpp" -o "$SCRIPT_DIR/test_protocol"

echo "Executing host protocol tests..."
"$SCRIPT_DIR/test_protocol"
