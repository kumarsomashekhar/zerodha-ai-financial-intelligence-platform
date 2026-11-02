"""Talks to Zerodha Kite. Keeps the daily access token in memory."""
import os

from kiteconnect import KiteConnect

_access_token = None


def _kite() -> KiteConnect:
    return KiteConnect(api_key=os.getenv("KITE_API_KEY"))


def login_url() -> str:
    """The Zerodha page where you log in each day."""
    return _kite().login_url()


def complete_login(request_token: str) -> None:
    """Swap the one-time code from Zerodha for today's access token."""
    global _access_token
    session = _kite().generate_session(
        request_token, api_secret=os.getenv("KITE_API_SECRET")
    )
    _access_token = session["access_token"]


def is_logged_in() -> bool:
    return _access_token is not None

def get_holdings() -> list:
    """Your current stock holdings, straight from Zerodha."""
    kite = _kite()
    kite.set_access_token(_access_token)
    return kite.holdings()