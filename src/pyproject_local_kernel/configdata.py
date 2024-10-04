from __future__ import annotations

import dataclasses
import logging
import shlex
import typing as t

_logger = logging.getLogger(__name__)


def _to_skewer_case(name: str):
    return name.replace("_", "-")


def _type_check(type_annot, obj):
    """
    Yes I know, ad-hoc type check of type annotations.
    Supports List, Union, Optional as needed.
    """
    args = t.get_args(type_annot)
    orig = t.get_origin(type_annot) or type_annot
    if args != () and (orig == t.Union or orig == t.Optional):
        return any(_type_check(arg, obj) for arg in args)
    elif args != () and orig is list:
        return _type_check(list, obj) and all(_type_check(args[0], elt) for elt in obj)
    ret = isinstance(obj, orig)
    return ret


@dataclasses.dataclass
class TypeCheckedFromDict:
    """
    Add from_dict constructor which checks the types of fields;
    enforces skewer case `like-this` for fields like `like_this`.
    """
    @classmethod
    def from_dict(cls, data: dict[str, t.Any]):
        kwargs = {}
        used_configs = set()
        self_type_hints = t.get_type_hints(cls)
        for field in dataclasses.fields(cls):
            config_name = _to_skewer_case(field.name)
            try:
                config_value = data[config_name]
            except KeyError:
                continue
            field_type = self_type_hints[field.name]
            if not _type_check(field_type, config_value):
                raise TypeError(f"invalid config {config_name} = {config_value!r}, expected value of type {field.type}")
            kwargs[field.name] = config_value
            used_configs.add(config_name)
        for unknown_config_key in set(data).difference(used_configs):
            _logger.warning("Ignoring unknown configuration key %r", unknown_config_key)
        return cls(**kwargs)


@dataclasses.dataclass
class Config(TypeCheckedFromDict):
    """
    pyproject tool.MY_TOOL_NAME section
    """

    python_cmd: t.Optional[t.Union[str, t.List[str]]] = None
    use_venv: t.Optional[str] = None

    def python_cmd_normalized(self) -> t.Optional[t.List[str]]:
        if isinstance(self.python_cmd, str):
            return shlex.split(self.python_cmd)
        return self.python_cmd

    def merge_with(self, other: Config) -> Config:
        "Merge with self taking precedence over other"
        return Config(python_cmd=self.python_cmd or other.python_cmd, use_venv=self.use_venv or other.use_venv)
