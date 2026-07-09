#!/usr/bin/env python3
import sys

from swiss_ambulatory_grouper_mcp.source_inventory import cli

if __name__ == "__main__":
    raise SystemExit(cli([*sys.argv[1:], "--requirements"]))
