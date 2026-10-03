"""Write the UTCP manual, or check that the committed one is current.

    python -m manualgen --schema schemas/3.6/schema.json --allowlist manualgen/allowlist.yaml \
        --out utcp_juju/data/juju.utcp.json [--check]
"""

import argparse
import logging
from pathlib import Path

from manualgen.allowlist import Allowlist
from manualgen.facade_schema import parse_facades
from manualgen.generator import render


def main() -> None:
    """Command-line entry point."""
    parser = argparse.ArgumentParser(
        prog='python -m manualgen', description=__doc__.split('\n')[0]
    )
    parser.add_argument('--schema', type=Path, required=True, help="Juju's schema.json")
    parser.add_argument('--allowlist', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True, help='manual file to write or check')
    parser.add_argument('--check', action='store_true', help='fail if --out is out of date')
    args = parser.parse_args()
    # UTCP logs every plugin it registers at INFO; that is noise here.
    logging.getLogger('utcp').setLevel(logging.WARNING)

    allowlist = Allowlist.from_yaml(args.allowlist.read_text())
    text = render(parse_facades(args.schema.read_bytes()), allowlist)
    if args.check:
        if not args.out.exists() or args.out.read_text() != text:
            raise SystemExit(f'{args.out} is out of date; run `just gen-manual`')
        print(f'{args.out} is up to date')
        return
    args.out.write_text(text)
    print(f'wrote {args.out}')


if __name__ == '__main__':
    main()
