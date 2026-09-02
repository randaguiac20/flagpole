"""Entry point. Spec: 004-flagpole-mcp FR-012; research D6.

On stdio transport stdout *is* the protocol, so logging goes to stderr explicitly. One stray line on
stdout corrupts the stream and the session's connection dies with an unhelpful parse error.
"""

import asyncio
import logging
import sys

from flagpole_mcp.client import FlagServiceClient
from flagpole_mcp.config import Settings, get_settings
from flagpole_mcp.server import build_server
from flagpole_mcp.tokens import ServiceTokenSigner


def build_client(settings: Settings) -> FlagServiceClient:
    """Reads the signing key once, at startup: a bad path must fail loudly, not per call."""
    signer = ServiceTokenSigner(
        private_key_pem=settings.read_private_key(),
        issuer=settings.mcp_service_issuer,
        audience=settings.mcp_service_audience,
        env=settings.mcp_env,
    )
    return FlagServiceClient(settings=settings, signer=signer)


def main() -> None:
    logging.basicConfig(stream=sys.stderr, level=logging.INFO, format="%(levelname)s %(message)s")
    settings = get_settings()
    asyncio.run(build_server(build_client(settings)).run_stdio_async())


if __name__ == "__main__":
    main()
