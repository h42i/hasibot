#!/usr/bin/env python3
"""HaSi XMPP-to-IRC bridge bot.
"""

from argparse import ArgumentParser, RawDescriptionHelpFormatter
import logging
from logging import debug, info, warning
from re import match
from textwrap import dedent

from yaml import safe_load
from sleekxmpp import ClientXMPP

class HaSiBot(ClientXMPP):
    """A fairly simple bot that relays messages from HaSi's IRC channel (mapped
    to a special MUC on the XMPP server) to the HaSi MUC and vice versa.
    """

    def __init__(self, jid, password, irc_room, xmpp_room):
        """Initializes the bot.
        """
        ClientXMPP.__init__(self, jid, password)
        self.nick = 'hasibot'
        self.irc_room = irc_room
        self.xmpp_room = xmpp_room

        self.add_event_handler("session_start", self.sign_in)
        self.add_event_handler("groupchat_message", self.forward_message)

        # Connect to the XMPP server and start processing XMPP stanzas.
        if self.connect():
            self.process(block=True)
            print("Done")
        else:
            print("Unable to connect.")

    def sign_in(self, event):
        """
        Process the session_start event.

        Typical actions for the session_start event are requesting the roster and broadcasting an
        initial presence stanza.

        Arguments:
            event An empty dictionary. The session_start event does not provide any additional data.
        """
        self.send_presence()
        self.register_plugin('xep_0045')
        self.plugin['xep_0045'].joinMUC(self.irc_room, self.nick)
        self.plugin['xep_0045'].joinMUC(self.xmpp_room, self.nick)

    def forward_message(self, msg):
        """
        Process incoming message stanzas. Be aware that this also
        includes MUC messages and error messages. It is usually
        a good idea to check the messages's type before processing
        or sending replies.

        Arguments:
            msg -- The received message stanza. See the documentation
                   for stanza objects and the Message stanza to see
                   how it may be used.
        """
        # Do not bounce forwarded messages back and forth
        if msg['mucnick'] == self.nick:
            debug('Ignoring message from %s', self.nick)
            return

        room = msg['from'].jid
        room = room[:room.index('/')]
        body = '<{}> {}'.format(msg['mucnick'], msg['body'])
        if room == self.irc_room:
            info('Relaying message from %s', self.irc_room)
            # Remove tag from telegram bot
            if match(r'<\W*shurely\d*>', body):
                body = body[body.index('>')+2:]
            self.send_message(mto=self.xmpp_room, mbody=body, mtype='groupchat')
        elif room == self.xmpp_room:
            info('Relaying message from %s', self.xmpp_room)
            self.send_message(mto=self.irc_room, mbody=body, mtype='groupchat')
        else:
            warning('Ignoring message from unkown source: %s', room)
            return

def prepare_argument_parser():
    """Creates and configures the argument parser for the CLI.
    """
    parser = ArgumentParser(description='HaSi XMPP-to-IRC bridge bot.',
                            epilog=dedent("""\
                            The config file must be valid YAML and contain the following items:
                            jid:    the bot's JID on the server
                            pw:     the bot's password
                            irc:    the JID of the MUC that maps to the IRC channel
                            xmpp:   the JID of the "native" XMPP MUC
                            """),
                            formatter_class=RawDescriptionHelpFormatter,
                            add_help=True)
    parser.add_argument('-c', '--conf', default='hasibot.yaml',
                        help='path to the configuration file')
    parser.add_argument('-l', '--log',
                        help='path to the configuration file')
    return parser

def main():
    """Well... The main() method. Nuff said.
    """
    args = prepare_argument_parser().parse_args()
    if args.log:
        logging.basicConfig(filename=args.log, format='%(levelname)-8s %(message)s',
                            level=logging.INFO)
    else:
        logging.basicConfig(format='%(levelname)-8s %(message)s', level=logging.INFO)

    # Read and parse config
    with open(args.conf) as conf_file:
        data = conf_file.read()
        config = safe_load(data)

    HaSiBot(config['jid'], config['pw'], config['irc'], config['xmpp'])

if __name__ == '__main__':
    main()
