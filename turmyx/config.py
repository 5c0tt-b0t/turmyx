from typing import List, Union, Dict
from abc import ABC, abstractmethod
import os
from configparser import ConfigParser, ExtendedInterpolation, SectionProxy
from pathlib import Path

import yaml
from turmyx.commands import Command, CommandEntry, CommandDict, CommandDictType

DIR_PATH = os.path.dirname(os.path.realpath(__file__))

CONFIG_FILE = Path(__file__).parent.parent.absolute() / "turmyxconf.ini"
# CONFIG_FILE = Path(__file__).parent.parent.absolute() / "turmyxconf.yml"


class TurmyxConfig(ABC):

    classes_name = {"file-editors": "extensions", "url-openers": "domains"}

    @abstractmethod
    def load(self, config_file: Path = CONFIG_FILE) -> 'TurmyxConfig':
        pass

    @abstractmethod
    def save(self, config_file: Path = CONFIG_FILE):
        pass

    @abstractmethod
    def get_file_editor(self, extension: str) -> Command:
        pass

    @abstractmethod
    def get_url_opener(self, domain: str) -> Command:
        pass

    @abstractmethod
    def set_file_editor(self, command: Union[Command, CommandEntry]) -> 'TurmyxConfig':
        pass

    @abstractmethod
    def set_url_opener(self, command: Union[Command, CommandEntry]) -> 'TurmyxConfig':
        pass

    @abstractmethod
    def remove_file_editor(self, command_name: str) -> 'TurmyxConfig':
        pass

    @abstractmethod
    def remove_url_opener(self, command_name: str) -> 'TurmyxConfig':
        pass


class CfgConfig(ConfigParser, TurmyxConfig):
    def __init__(self):
        self.__config_file_path = None
        super(CfgConfig, self).__init__(interpolation=ExtendedInterpolation())

    def load(self, config_file: Path = CONFIG_FILE) -> 'CfgConfig':
        self.__config_file_path = config_file
        self.read(config_file.as_posix())
        return self

    def save(self, config_file: Path = CONFIG_FILE):
        self.write(config_file.open("w"))

    def __get_section(self, section_kind: str, class_kind: str, class_name: str) -> 'SectionProxy':
        for section in self.sections():
            if "default" not in section and section_kind in section:
                if class_name in self[section][class_kind].split(" "):
                    return self[section]

        return self[f"{section_kind}:default"]

    def __get_command(self, section_kind: str, class_kind: str, class_name: str) -> Command:
        section = self.__get_section(section_kind, class_kind, class_name)
        return Command(
            command=section["command"],
            args=section["args"] if "args" in section else "",
            classes=section[class_kind].split(" ") if class_kind in section else [],
            name=section.name.split(":")[0]
        )

    def get_file_editor(self, extension: str) -> Command:
        return self.__get_command("file-editors", "extensions", extension)

    def get_url_opener(self, domain: str) -> Command:
        return self.__get_command("url-openers", "domains", domain)

    def __set_command(self, command: Union[Command, CommandEntry], kind: str = "file-editors"):
        name = command.name if command.name else Path(command.command).name
        section = f"{kind}:{name}"
        if section not in self:
            self[section] = dict()
        self.set(section, "command", command.command)
        self.set(section, "args", command.args)
        self.set(section, self.classes_name.get(kind), " ".join(command.classes))
        return self

    def set_file_editor(self, command: Union[Command, CommandEntry]) -> 'CfgConfig':
        return self.__set_command(command)

    def set_url_opener(self, command: Union[Command, CommandEntry]) -> 'CfgConfig':
        return self.__set_command(command, kind="opener")

    def __remove_command(self, command_name: str, kind: str = "file-editors") -> 'CfgConfig':
        if self.remove_section(f"{kind}:{command_name}"):
            return self
        else:
            raise ValueError("Command not found in config file.")

    def remove_file_editor(self, command_name: str) -> 'CfgConfig':
        return self.__remove_command(command_name)

    def remove_url_opener(self, command_name: str) -> 'CfgConfig':
        return self.__remove_command(command_name, kind="url-openers")


class YAMLConfig(TurmyxConfig):

    def __init__(self):

        self.file_editors = None
        self.url_openers = None

    def load(self, config_file: Path = CONFIG_FILE) -> 'YAMLConfig':
        with config_file.open() as cf:
            yml_data = yaml.load(cf)

        editors: CommandDictType = yml_data.get("file-editors")
        for d in editors.get("commands").values():
            d["classes"] = d.pop("extensions")

        self.file_editors = CommandDict(editors)

        openers = yml_data.get("url-openers")
        for d in openers.get("commands").values():
            d["classes"] = d.pop("domains")

        self.url_openers = CommandDict(openers)

        return self

    def as_dict(self):
        editors = self.file_editors.as_dict()
        openers = self.url_openers.as_dict()

        for d in editors.get("commands").values():
            d["extensions"] = d.pop("classes")

        for d in openers.get("commands").values():
            d["domains"] = d.pop("classes")

        return dict(file_editors=editors, url_openers=openers)

    def save(self, config_file: Path = CONFIG_FILE):
        yml_data = self.as_dict()
        with config_file.open("w") as cf:
            yaml.dump(yml_data, cf, indent=4, allow_unicode=True)

    @staticmethod
    def __get_command(commands: 'CommandDict', class_name: str) -> 'Command':
        all_classes = set(c for command in commands.values() for c in command.classes)
        if class_name in all_classes:
            for command in commands.values():
                if class_name in command.classes:
                    return Command.from_command(command)
        else:
            return Command.from_command(commands.default)

    def get_file_editor(self, extension: str) -> Command:
        return self.__get_command(self.file_editors, extension)

    def get_url_opener(self, domain: str) -> Command:
        return self.__get_command(self.url_openers, domain)

    def set_file_editor(self, command: Union[Command, CommandEntry]) -> 'TurmyxConfig':
        self.file_editors[command.name] = command

    def set_url_opener(self, command: Union[Command, CommandEntry]) -> 'TurmyxConfig':
        self.url_openers[command.name] = command

    def remove_file_editor(self, command_name: str) -> 'TurmyxConfig':
        self.file_editors.pop(command_name)

    def remove_url_opener(self, command_name: str) -> 'TurmyxConfig':
        self.url_openers.pop(command_name)
