import enum
import re
import tempfile
from pathlib import Path
from typing import Optional

import black
import isort

INDENT = "    "


class HTTPResponse(enum.IntEnum):
    OK = 200
    CREATED = 201
    ACCEPTED = 202
    NO_CONTENT = 204
    RESET_CONTENT = 205
    PARTIAL_CONTENT = 206
    MULTI_STATUS = 207
    ALREADY_REPORTED = 208
    IM_USED = 226
    MULTIPLE_CHOICES = 300
    MOVED_PERMANENTLY = 301
    FOUND = 302
    SEE_OTHER = 303
    NOT_MODIFIED = 304
    USE_PROXY = 305
    TEMPORARY_REDIRECT = 307
    PERMANENT_REDIRECT = 308
    BAD_REQUEST = 400
    UNAUTHORIZED = 401
    FORBIDDEN = 403
    NOT_FOUND = 404
    METHOD_NOT_ALLOWED = 405
    NOT_ACCEPTABLE = 406
    PROXY_AUTHENTICATION_REQUIRED = 407
    REQUEST_TIMEOUT = 408
    CONFLICT = 409
    GONE = 410
    LENGTH_REQUIRED = 411
    PRECONDITION_FAILED = 412
    REQUEST_ENTITY_TOO_LARGE = 413
    REQUEST_URI_TOO_LONG = 414
    UNSUPPORTED_MEDIA_TYPE = 415
    REQUESTED_RANGE_NOT_SATISFIABLE = 416
    EXPECTATION_FAILED = 417
    IM_A_TEAPOT = 418
    MISDIRECTED_REQUEST = 421
    UNPROCESSABLE_ENTITY = 422
    LOCKED = 423
    FAILED_DEPENDENCY = 424
    UPGRADE_REQUIRED = 426
    PRECONDITION_REQUIRED = 428
    TOO_MANY_REQUESTS = 429
    REQUEST_HEADER_FIELDS_TOO_LARGE = 431
    UNAVAILABLE_FOR_LEGAL_REASONS = 451
    INTERNAL_SERVER_ERROR = 500
    NOT_IMPLEMENTED = 501
    BAD_GATEWAY = 502
    SERVICE_UNAVAILABLE = 503
    GATEWAY_TIMEOUT = 504
    HTTP_VERSION_NOT_SUPPORTED = 505
    VARIANT_ALSO_NEGOTIATES = 506
    INSUFFICIENT_STORAGE = 507
    LOOP_DETECTED = 508
    NOT_EXTENDED = 510
    NETWORK_AUTHENTICATION_REQUIRED = 511


invalid_chars = re.compile(r"\W")


def convert_camel_case_to_snake_case(txt: str) -> str:
    if not txt:
        return txt

    parts = []
    for char in txt:
        if invalid_chars.match(char) is not None:
            continue
        if char.isupper():
            parts.append("_")

        parts.append(char.lower())
    return "".join(parts)


def to_class_name(txt: str) -> str:
    return txt[0].upper() + txt[1:]


def write_data_to_file(
    data,
    *,
    import_statements: list[str],
    file_name: str,
    export_folder: Optional[Path] = None,
    use_tempdir: bool = False,
):
    if use_tempdir:
        tmp_file = tempfile.NamedTemporaryFile("w", suffix=f"_{file_name}.py", delete_on_close=False)
        tmp_file.close()
        view_file = Path(tmp_file.name)
    else:
        view_file = export_folder / f"{file_name}.py" if export_folder else Path(__file__).parent / f"{file_name}.py"

    with view_file.open("w") as fp:
        fp.write("\n".join(import_statements))
        fp.write("\n\n\n")
        fp.write("\n\n\n".join(data))

    isort.api.sort_file(view_file)
    black.format_file_in_place(view_file, mode=black.Mode(), fast=False, write_back=black.WriteBack.YES)

    if use_tempdir:
        with view_file.open("r") as fp:
            for line in fp.readlines():
                print(line)


def operation_id_to_function_name(operation_id: str) -> str:
    try:
        camel_idx = re.search(r"[A-Z]", operation_id).start()
    except AttributeError:
        return operation_id
    chars = [obj for obj in operation_id]
    chars[camel_idx] = f"_{operation_id[camel_idx].lower()}"
    return operation_id_to_function_name("".join(chars))


def function_like_name_to_class_name(val: str, /):
    def to_title(val_: str):
        if val_[0].isupper():
            return val_
        else:
            return val_.title()

    return "".join([to_title(obj) for obj in val.split("_")])


TYPE_CONVERTION = {
    "integer": "int",
    "number": "float",
    "string": "str",
    "object": "dict",
    "array": "list",
    "boolean": "bool",
}

STR_FORMAT = {
    "date": "date",
    "date-time": "datetime",
    "byte": "bytes",
}


class Concurrency(enum.IntEnum):
    SYNC = 0
    ASYNC = 1

    @classmethod
    def from_str(cls, val: str):
        match val.lower():
            case "sync":
                return cls.SYNC
            case "async":
                return cls.ASYNC
            case _:
                raise ValueError("Invalid concurrency value")
