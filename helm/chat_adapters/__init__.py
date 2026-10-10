"""Chat apps that talk to RAPR through the shared router (helm/chat_router.py).

Each app module is imported only when its token is set, so the libraries it
needs (discord.py, slack-bolt) are optional installs.
"""
