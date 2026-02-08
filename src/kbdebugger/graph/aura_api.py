"""
Aura API helper utilities to detect paused instances and resume them.

This prevents Neo4j driver failures like:
- socket.gaierror: [Errno -2] Name or service not known
- Cannot resolve address <dbid>.databases.neo4j.io:7687

Those typically happen when AuraDB Free is auto-paused and the bolt hostname
stops resolving.
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass
from typing import Any, Optional

import requests
import rich

@dataclass(frozen=True)
class AuraCredentials:
    """OAuth client credentials for the Neo4j Aura API."""
    client_id: str
    client_secret: str


class AuraAPIError(RuntimeError):
    """Raised when Aura API interactions fail."""


class AuraAPI:
    """
    Minimal Aura API client for:
    - fetching an OAuth bearer token
    - reading instance status
    - resuming an instance if paused

    Docs:
      - Base URL: https://api.neo4j.io
      - Token endpoint: POST https://api.neo4j.io/oauth/token
    """

    def __init__(
            self, 
            creds: AuraCredentials, 
            *, 
            base_url: str = "https://api.neo4j.io"
        ) -> None:
        self._creds = creds
        self._base_url = base_url.rstrip("/") # remove trailing slash if provided
        self._token: Optional[str] = None
        self._token_expires_at: float = 0.0

    def _get_token(self) -> str:
        """
        Fetch and cache a bearer token (client_credentials flow).

        The Aura docs specify:
          POST https://api.neo4j.io/oauth/token
          grant_type=client_credentials
          Basic auth: <client_id>:<client_secret>
        """
        now = time.time()
        if self._token and now < self._token_expires_at - 30:
            return self._token

        resp = requests.post(
            f"{self._base_url}/oauth/token",
            auth=(self._creds.client_id, self._creds.client_secret),
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            data={"grant_type": "client_credentials"},
            timeout=30,
        )
        if resp.status_code >= 400:
            raise AuraAPIError(f"Failed to obtain Aura API token: {resp.status_code} {resp.text}")

        payload = resp.json()
        access_token = payload["access_token"]
        expires_in = float(payload.get("expires_in", 3600))

        self._token = access_token
        self._token_expires_at = now + expires_in
        return access_token

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self._get_token()}"}

    def get_instance(self, instance_id: str) -> dict[str, Any]:
        """
        Get instance details (includes status).

        NOTE: Endpoint path may evolve across Aura API versions.
        If your tenant uses a different path, adjust according to the API spec.
        """
        url = f"{self._base_url}/v1/instances/{instance_id}"
        resp = requests.get(url, headers=self._headers(), timeout=30)
        if resp.status_code >= 400:
            raise AuraAPIError(f"Failed to get instance {instance_id}: {resp.status_code} {resp.text}")
        return resp.json()
    
    def get_instance_status(self, instance_id: str) -> str:
        """
        Get the status of an Aura instance.

        Expected values (observed):
            - "running"
            - "paused"
            - "resuming"
            - "provisioning"

        Returns
        -------
        str
            Lowercased status string.

        Raises
        ------
        AuraAPIError
            If the response does not contain a status field.
        """
        info = self.get_instance(instance_id)

        try:
            status = info["data"]["status"]
        except KeyError as e:
            raise AuraAPIError(
                f"Unexpected Aura API response shape; missing status.\n"
                f"Response keys: {list(info.keys())}\n"
                f"Full response: {info}"
            ) from e
        
        return str(status).lower()

    def resume_instance(self, instance_id: str) -> None:
        """
        Trigger a resume of a paused instance.

        NOTE: Endpoint path may evolve across Aura API versions.
        Adjust according to the API spec if needed.
        """
        url = f"{self._base_url}/v1/instances/{instance_id}/resume"
        resp = requests.post(url, headers=self._headers(), timeout=30)
        resp = requests.post(
            url,
            headers={
                **self._headers(),
                "Content-Type": "application/json", # needed here
            },
            json={},          # optional but helps make intent explicit
            timeout=30,
        )
        if resp.status_code >= 400:
            raise AuraAPIError(f"Failed to resume instance {instance_id}: {resp.status_code} {resp.text}")

    def ensure_running(
        self,
        instance_id: str,
        *,
        poll_seconds: float = 5.0, # time to wait between status checks while polling
        timeout_seconds: float = 180.0,
        verbose: bool = True,
    ) -> None:
        """
        If instance is paused, resume it and wait until status is Running.

        This is intended to run BEFORE creating a Neo4j driver session.
        """
        start = time.time()

        status = self.get_instance_status(instance_id)

        if verbose:
            rich.print(f"💧 [kbdebugger] Aura instance {instance_id}: status={status!r}")

        if "paused" in status:
            if verbose:
                rich.print(f"⚠️ [kbdebugger] Aura instance {instance_id} is paused → resuming via Aura API...")
            self.resume_instance(instance_id)

        # Poll until running (or timeout)
        while True:
            if time.time() - start > timeout_seconds:
                raise AuraAPIError(
                    f"🛑☹️ Timed out waiting for Aura instance {instance_id} to become running "
                    f"(waited {timeout_seconds}s)."
                )

            status = self.get_instance_status(instance_id)

            if "running" in status:
                if verbose:
                    rich.print(f"🏃💧 [kbdebugger] Aura instance {instance_id} is running.")
                return

            if verbose:
                rich.print(f"[kbdebugger] Aura instance {instance_id} not running yet (status={status!r}); polling...")
            time.sleep(poll_seconds)


def ensure_aura_running_from_env(*, verbose: bool = True) -> None:
    """
    Convenience entrypoint: uses env vars to ensure the Aura instance is running.

    Required env vars:
      - AURA_API_CLIENT_ID
      - AURA_API_CLIENT_SECRET
      - AURA_INSTANCE_ID
    """
    client_id = os.getenv("AURA_API_CLIENT_ID", "").strip()
    client_secret = os.getenv("AURA_API_CLIENT_SECRET", "").strip()
    instance_id = os.getenv("AURA_INSTANCE_ID", "").strip()

    if not (client_id and client_secret and instance_id):
        # If you want this to be mandatory, raise instead of returning.
        if verbose:
            rich.print("⚠️ [kbdebugger] Aura auto-resume is not configured; skipping (missing env vars).")
        return

    api = AuraAPI(
        AuraCredentials(client_id=client_id, client_secret=client_secret)
    )
    api.ensure_running(instance_id, verbose=verbose)
