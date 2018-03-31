from linebot import (
    LineBotApi, WebhookHandler
)
from linebot.exceptions import (
    InvalidSignatureError
)
from linebot.models import (
    MessageEvent, TextMessage, TextSendMessage,
)
import re
import sqlite3


class BotCMD():
    "Enum class for bot command"
    UNKNOWN_CMD = 0
    SEARCH = 1
    LOGIN = 2
    READ_FILE = 3
    WRITE_FILE = 4
    LIST_FILE = 5
    HELP = 6

    CMD_DICT = {
        "search": SEARCH,
        "login": LOGIN,
        "read": READ_FILE,
        "write": WRITE_FILE,
        "list": LIST_FILE,
        "help": HELP
    }

    HELP_MSG = "\n".join([">> Help <<",
                          "search <animal>",
                          "login <user> <password>",
                          "read <file_name>",
                          "write <file_name>",
                          "list",
                          "help"])

    @classmethod
    def parse_command(cls, text):
        command = cls.UNKNOWN_CMD
        if text:
            text = text.strip().lower()
            if text in cls.CMD_DICT:
                command = cls.CMD_DICT[text]
        return command

class TextParser():
    """
    Class for parsing text into several parts
    Support several regexes
    """

    # TODO(M) : Fix reqex to support Thai item and user_name.
    order_regexes = [r"^(\w+)$",
                     r"^(\w+) (.+)$",
                     r"^(\w+) (.+) (.+)$"]
    text_groups = [["cmd"],
                   ["cmd", "param"],
                   ["cmd", "user", "password"]]

    @classmethod
    def parse_text_group(cls, text):
        result = {}
        i = -1
        for order_regex in TextParser.order_regexes:
            i += 1
            m = re.match(order_regex, text)
            if m == None:
                continue
            try:
                j = 0
                for match in TextParser.text_groups[i]:
                    j += 1
                    result[match] = m.group(j)
                return result
            except:
                continue
        return None


class Agent():
    """Chatbot agent for handling incoming message event"""
    ERROR_MSG = "Type \"Help\" to see available commands"
    ERROR_ACC = "You need to Login first"
    ERROR_PARAM = "Missing parameters, type \"Help\" to see parameters"

    SEARCH_CMD = "SELECT desc FROM animals WHERE name = \"%s\""
    SEARCH_NOT_FOUND_MSG = "Not found"

    def __init__(self):
        # Map room_id with order property
        self.conn = sqlite3.connect('myEverything.db')
        self.session = {}

    def __check_access_control(self, user_id, command):
        if "login" in self.session[user_id] and self.session[user_id]["login"] == True:
            return True
        elif command == BotCMD.HELP or \
             command == BotCMD.SEARCH or \
             command == BOTCMD.LOGIN:
                return True
        else:
            return False

    def __handle_new_session(self, userId):
        if userId not in self.session:
            self.session[userId] = {}
            self.session[userId]["login"] = False
            self.session[userId]["write"] = False

    def __handle_search(self, param):
        cmd = self.SEARCH_CMD % (param)
        cursor = self.conn.cursor()
        try:
            cursor.execute(cmd)
            return cursor.fetchone()[0]
        except:
            return self.SEARCH_NOT_FOUND_MSG

    def __handle_read(self, **kwargs):
        return None

    def __handle_write(self, **kwargs):
        return None

    def __handle_list(self, **kwargs):
        return None

    def __handle_help(self):
        return BotCMD.HELP_MSG

    def handle_text_message(self, event):
        "Handle text message event."
        user_id = event.source.user_id
        self.__handle_new_session(user_id)

        group_text = TextParser.parse_text_group(event.message.text)
        if group_text == None:
            return self.ERROR_MSG 

        cmd = BotCMD.parse_command(group_text['cmd'])
        if cmd == BotCMD.UNKNOWN_CMD:
            return self.ERROR_MSG 

        if self.__check_access_control(user_id, cmd) == False:
            return self.ERROR_LOGIN

        if cmd == BotCMD.SEARCH and "param" in group_text:
            return self.__handle_search(group_text["param"])

        if cmd == BotCMD.HELP:
            return self.__handle_help()

        return self.ERROR_MSG

