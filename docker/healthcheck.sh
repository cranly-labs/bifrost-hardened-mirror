#!/bin/sh
set -eu
exec wget -q -O /dev/null "http://127.0.0.1:${APP_PORT:-8080}/health"
