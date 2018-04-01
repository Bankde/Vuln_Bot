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

import subprocess

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
                     r"^(\w+) (.+)$"]
    text_groups = [["cmd"],
                   ["cmd", "param"]]

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
    ERROR_ACCESS_CONTROL = "You need to login as admin to use this function"

    UPDATE_ADMIN_PASS_CMD = "UPDATE users SET password = ? WHERE user = \"admin\"" 

    # This is ok, it's just SEARCH function and Line API shouldn't have SQL injection right ?
    SEARCH_CMD = "SELECT desc FROM animals WHERE name = \"%s\""
    SEARCH_NOT_FOUND_MSG = "Not found"

    LOGIN_CMD = "SELECT password FROM users WHERE user = ?"
    ERROR_LOGIN = "Wrong username or password"
    LOGIN_SUCCESS = "User login successfully."

    ERROR_FILE_READ_MSG = "Unable to read that file"

    INFO_WRITE_INIT = "Start writing file. Please enter data in your next message"
    INFO_WRITE_DONE = "Finish writing to file."

    def __init__(self, admin_password=None):
        # Map room_id with order property
        self.conn = sqlite3.connect('myEverything.db')
        self.session = {}
        if admin_password is not None:
            cursor = self.conn.cursor()
            cursor.execute(self.UPDATE_ADMIN_PASS_CMD, [admin_password])

    def __check_access_control(self, user_id, command):
        if "login" in self.session[user_id] and self.session[user_id]["login"] == True:
            return True
        elif command == BotCMD.HELP or \
             command == BotCMD.SEARCH or \
             command == BotCMD.LOGIN:
                return True
        else:
            return False

    def __handle_login(self, user_id, params):
        try:
            user, password = params.split(" ")
        except:
            return self.ERROR_LOGIN

        try:
            cursor = self.conn.cursor()
            cursor.execute(self.LOGIN_CMD, [user])

            row = cursor.fetchone()
            if not row:
                return self.ERROR_LOGIN

            db_password = row[0]
            if password == db_password:
                self.session[user_id]["login"] = True
                return self.LOGIN_SUCCESS
        except:
            return self.ERROR_LOGIN

        return self.ERROR_LOGIN 

    def __handle_new_session(self, userId):
        if userId not in self.session:
            self.session[userId] = {}
            self.session[userId]["login"] = None 
            self.session[userId]["write"] = None 

    def __handle_search(self, param):
        cmd = self.SEARCH_CMD % (param)
        cursor = self.conn.cursor()
        try:
            cursor.execute(cmd)
            return cursor.fetchone()[0]
        except:
            return self.SEARCH_NOT_FOUND_MSG

    def __handle_read(self, filePath):
        try:
            f = open(filePath, "r")
        except:
            return self.ERROR_FILE_READ_MSG

        content = f.read()
        f.close()
        return content

    # We do not have to validate the filePath. Even user can overwrite something, they cannot execute them anyway. This is docker image so we can everything run as root right ?
    def __handle_write_init(self, user_id, filePath):
        self.session[user_id]["write"] = filePath 
        return self.INFO_WRITE_INIT 

    def __handle_write_exec(self, user_id, data):
        filePath = self.session[user_id]["write"]
        self.session[user_id]["write"] = None
        with open(filePath, "w+") as f:
            f.write(data)
        return self.INFO_WRITE_DONE 

    def __handle_list(self):
        return subprocess.Popen("ls", stdout=subprocess.PIPE).stdout.read()

    def __handle_help(self):
        return BotCMD.HELP_MSG

    def handle_text_message(self, event):
        "Handle text message event."
        user_id = event.source.user_id
        self.__handle_new_session(user_id)

        if self.session[user_id]["write"]:
            cmd = BotCMD.WRITE_FILE
            data = event.message.text
            return self.__handle_write_exec(user_id, data)

        group_text = TextParser.parse_text_group(event.message.text)
        if group_text == None:
            return self.ERROR_MSG
        elif "cmd" in group_text:
            cmd = BotCMD.parse_command(group_text["cmd"])
        else:
            return self.ERROR_MSG

        if cmd == BotCMD.UNKNOWN_CMD:
            return self.ERROR_MSG 

        if self.__check_access_control(user_id, cmd) == False:
            return self.ERROR_ACCESS_CONTROL

        if cmd == BotCMD.SEARCH and "param" in group_text:
            return self.__handle_search(group_text["param"])

        if cmd == BotCMD.HELP:
            return self.__handle_help()

        if cmd == BotCMD.LOGIN and "param" in group_text:
            return self.__handle_login(user_id, group_text["param"])

        if cmd == BotCMD.READ_FILE and "param" in group_text:
            return self.__handle_read(group_text["param"])

        if cmd == BotCMD.WRITE_FILE:
            if "write" in self.session[user_id] and self.session[user_id]["write"]== None:
                return self.__handle_write_init(user_id, group_text["param"])

        if cmd == BotCMD.LIST_FILE:
            return self.__handle_list()

        return self.ERROR_MSG

