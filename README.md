# hasibot
A fairly simple bot that relays messages from HaSi's IRC channel (mapped to a
special MUC on the XMPP server) to the HaSi MUC and Telegram group and vice
versa.

## Installation
The script requires three libraries:

* sleekxmpp (for XMPP stuff, obviously)
* python-telegram-bot (guess what this does)
* pyyaml (for parsing the config file)

## Configuration
The Bot relies on a straight-forward YAML configuration file:

```yaml
jid:      the bot's JID on the server
pw:       the bot's password
irc:      the JID of the MUC that maps to the IRC channel
xmpp:     the JID of the "native" XMPP MUC
tg_chat:  the Telegram group chat's ID
tg_token: the Telegram API token
```

You can find an example configuration in the repository.
