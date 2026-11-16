"""Generate a LUMI member bearer token and its server-side SHA-256 hash."""

import argparse
import hashlib
import json
import re
import secrets


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate a personal LUMI MCP token for one team member."
    )
    parser.add_argument(
        "member_id",
        help="Short unique ID, e.g. alice or member_02",
    )
    args = parser.parse_args()

    if not re.fullmatch(r"[A-Za-z0-9_.-]{1,64}", args.member_id):
        parser.error("member_id may contain only letters, numbers, _, ., and - (max 64).")

    token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()

    print(f"Member ID: {args.member_id}")
    print()
    print("Send this token privately to the member; store it in their local .env:")
    print(f"LUMI_MCP_TOKEN={token}")
    print()
    print("Add this hash entry to Render's MCP_TOKENS_JSON object:")
    print(json.dumps({args.member_id: token_hash}, ensure_ascii=False))


if __name__ == "__main__":
    main()
