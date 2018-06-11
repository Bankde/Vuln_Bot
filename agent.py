#!/usr/bin/env python

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
    HELP = 6

    CMD_DICT = {
        "search": SEARCH,
        "login": LOGIN,
        "help": HELP
    }

    HELP_MSG = "\n".join([">> Help <<",
                          "This application can search for animal's description.",
                          "search <animal>",
                          "login <user> <password>",
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
    ERROR_PARAM = "Missing parameters, type \"Help\" to see parameters"

    UPDATE_ADMIN_PASS_CMD = "UPDATE users SET password = ? WHERE user = \"admin\"" 

    # We know that hacker can't hack Facebook or Line API.
    SEARCH_CMD = "SELECT desc FROM animals WHERE name = \"%s\""
    SEARCH_NOT_FOUND_MSG = "Not found. Try simple animals like dog or cat !!"

    LOGIN_CMD = "SELECT password FROM users WHERE user = ?"
    LOGIN_SUCCESS = "Password is the flag. Congrats :)"

    def __init__(self, admin_password=None):
        # Map room_id with order property
        self.conn = sqlite3.connect('myEverything.db')
        if admin_password is not None:
            cursor = self.conn.cursor()
            cursor.execute(self.UPDATE_ADMIN_PASS_CMD, [admin_password])

    def __handle_login(self, user_id, params):
        try:
            user, password = params.split(" ")
        except:
            return self.LOGIN_ERROR

        try:
            cursor = self.conn.cursor()
            cursor.execute(self.LOGIN_CMD, [user])

            row = cursor.fetchone()
            if not row:
                return self.LOGIN_ERROR

            db_password = row[0]
            if password == db_password:
                return self.LOGIN_SUCCESS
        except:
            return self.LOGIN_ERROR

        return self.LOGIN_ERROR 

    def __handle_search(self, param):
        cmd = self.SEARCH_CMD % (param)
        cursor = self.conn.cursor()
        try:
            cursor.execute(cmd)
            return cursor.fetchone()[0]
        except:
            return self.SEARCH_NOT_FOUND_MSG

    def __handle_help(self):
        return BotCMD.HELP_MSG

    def handle_text_message(self, event):
        "Handle text message event."
        user_id = event.source.user_id

        group_text = TextParser.parse_text_group(event.message.text)
        if group_text == None:
            return self.ERROR_MSG
        elif "cmd" in group_text:
            cmd = BotCMD.parse_command(group_text["cmd"])
        else:
            return self.ERROR_MSG

        if cmd == BotCMD.UNKNOWN_CMD:
            return self.ERROR_MSG 

        if cmd == BotCMD.SEARCH and "param" in group_text:
            return self.__handle_search(group_text["param"])

        if cmd == BotCMD.HELP:
            return self.__handle_help()

        if cmd == BotCMD.LOGIN and "param" in group_text:
            return self.__handle_login(user_id, group_text["param"])

        return self.ERROR_MSG

