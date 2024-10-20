from __future__ import annotations

import dataclasses
import logging
import shlex
import typing as t

_logger = logging.getLogger(__name__)


def _to_skewer_case(name: str) -> str:
    return name.replace("_", "-")


def _type_check(type_annot: t.Any, obj: t.Any) -> bool:
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


def _type_name(type_annot: t.Any) -> str:
    args = t.get_args(type_annot)
    orig = t.get_origin(type_annot) or type_annot
    if args != () and (orig == t.Union or orig == t.Optional):
        return " | ".join(_type_name(arg) for arg in args)
    elif args != () and orig is list:
        return "list[" + _type_name(args[0])  + "]"
    if type_annot is type(None):
        return "None"
    return type_annot.__name__


def _dataclass_from_dict(cls, data: dict[str, t.Any]):
    kwargs = {}
    used_configs = set()
    for field in dataclasses.fields(cls):
        config_name = _to_skewer_case(field.name)
        for lookup_name in (config_name, field.name):
            try:
                config_value = data[lookup_name]
                break
            except KeyError:
                pass
        else:
            continue
        kwargs[field.name] = config_value
        used_configs.add(lookup_name)
    for unknown_config_key in set(data).difference(used_configs):
        _logger.warning("Ignoring unknown (or duplicate) configuration key %r", unknown_config_key)
    return cls(**kwargs)


class _PostInitTypeCheck:
    def __post_init__(self):
        self_type_hints = t.get_type_hints(type(self))
        for field in dataclasses.fields(self):  # type: ignore
            config_name = _to_skewer_case(field.name)
            config_value = getattr(self, field.name)
            field_type = self_type_hints[field.name]
            if not _type_check(field_type, config_value):
                show_type = _type_name(field_type)
                raise TypeError(f"invalid config {config_name} = {config_value!r}, expected value of type {show_type!r}")


@dataclasses.dataclass
class Config(_PostInitTypeCheck):
    """
    pyproject tool.MY_TOOL_NAME section
    """

    # python_cmd is always a list[str] after normalization
    python_cmd: t.Optional[t.Union[str, t.List[str]]] = None
    use_venv: t.Optional[str] = None
    sanity_check: t.Optional[bool] = None

    from_dict = classmethod(_dataclass_from_dict)

    def __post_init__(self):
        self.python_cmd = self._python_cmd_normalized()
        super().__post_init__()

    def _python_cmd_normalized(self) -> list[str] | None:
        if isinstance(self.python_cmd, str):
            return shlex.split(self.python_cmd)
        return self.python_cmd

    def merge_with(self, other: Config) -> Config:
        "Merge with self taking precedence over other"
        for field in dataclasses.fields(self):
            if getattr(self, field.name) is None:
                setattr(self, field.name, getattr(other, field.name))
        return self
