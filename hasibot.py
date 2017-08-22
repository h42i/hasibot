#!/usr/bin/env python3
"""HaSi Telegram-XMPP-IRC bridge bot.
"""

from argparse import ArgumentParser, RawDescriptionHelpFormatter
import logging
from logging import debug, info, warning
from textwrap import dedent

from yaml import safe_load
from sleekxmpp import ClientXMPP
from telegram.ext import Filters, MessageHandler, Updater

class HaSiBot(ClientXMPP):
    """A fairly simple bot that relays messages from HaSi's IRC channel (mapped to a special MUC on
       the XMPP server) to the HaSi MUC and Telegram group chat and vice versa.
    """

    def __init__(self, config):
        """Initializes the bot.

        Args:
            config      the YAML configuration
        """
        ClientXMPP.__init__(self, config['jid'], config['pw'])
        self.nick = 'hasibot'
        self.irc_room = config['irc']
        self.xmpp_room = config['xmpp']
        self.tg_chat = config['tg_chat']
        self.ignore_list = config['ignore']

        self.add_event_handler("session_start", self.sign_in)
        self.add_event_handler("groupchat_message", self.forward_message)

        self._tg_updater = Updater(config['tg_token'])
        self._tg_dispatcher = self._tg_updater.dispatcher
        self._tg_dispatcher.add_handler(MessageHandler(Filters.text, self.handle_telegram_message))
        self._tg_updater.start_polling()

        # Connect to the XMPP server and start processing XMPP stanzas.
        if self.connect():
            self.process(block=True)
            print("Done")
        else:
            print("Unable to connect.")

    def handle_telegram_message(self, bot, update):
        """Dispatcher handler that forwards messages from the Telegram group chat to IRC and XMPP.
        """
        msg = update.message
        # Ignore messages from other chats than the configured one and other updates
        if msg is None or msg.chat.id != self.tg_chat:
            return
        self._send_xmpp_message(self.irc_room, msg.from_user.name, msg.text)
        self._send_xmpp_message(self.xmpp_room, msg.from_user.name, msg.text)

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
        author = msg['mucnick']
        text = msg['body']

        # Do not bounce forwarded messages back and forth
        if author == self.nick:
            debug('Ignoring message from %s', self.nick)
            return

        for nick in self.ignore_list:
            if author == nick:
                debug('Ignoring message from %s', nick)
                return

        room = msg['from'].jid
        room = room[:room.index('/')]
        if room == self.irc_room:
            info('Relaying message from %s', self.irc_room)
            self._send_xmpp_message(self.xmpp_room, author, text)
        elif room == self.xmpp_room:
            info('Relaying message from %s', self.xmpp_room)
            self._send_xmpp_message(self.irc_room, author, text)
        else:
            warning('Ignoring message from unkown source: %s', room)
            return

        self._tg_updater.bot.send_message(chat_id=self.tg_chat, text=_format_message(author, text))

    def _send_xmpp_message(self, room, author, text):
        body = '<{}> {}'.format(author, text)
        self.send_message(mto=room, mbody=body, mtype='groupchat')


def _format_message(author, text):
    return '<{}> {}'.format(author, text)

def _prepare_argument_parser():
    """Creates and configures the argument parser for the CLI.
    """
    parser = ArgumentParser(description='HaSi Telegram-XMPP-IRC bridge bot.',
                            epilog=dedent("""\
                            The config file must be valid YAML and contain the following items:
                            jid:      the bot's JID on the server
                            pw:       the bot's password
                            irc:      the JID of the MUC that maps to the IRC channel
                            xmpp:     the JID of the "native" XMPP MUC
                            tg_chat:  the Telegram group chat's ID
                            tg_token: the Telegram API token
                            ignore:   a list of IRC nicks to ignore (useful for bots etc.)
                            """),
                            formatter_class=RawDescriptionHelpFormatter,
                            add_help=True)
    parser.add_argument('-c', '--conf', default='hasibot.yaml',
                        help='path to the configuration file')
    parser.add_argument('-l', '--log',
                        help='path to a file to which log messages should go')
    return parser

def main():
    """Well... The main() method. Nuff said.
    """
    args = _prepare_argument_parser().parse_args()
    if args.log:
        logging.basicConfig(filename=args.log, format='%(levelname)-8s %(message)s',
                            level=logging.INFO)
    else:
        logging.basicConfig(format='%(levelname)-8s %(message)s', level=logging.INFO)

    # Read and parse config
    with open(args.conf) as conf_file:
        data = conf_file.read()
        config = safe_load(data)

    HaSiBot(config)

if __name__ == '__main__':
    main()
