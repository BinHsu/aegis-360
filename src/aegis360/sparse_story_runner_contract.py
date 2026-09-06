"""Pure contracts for the sparse-story isolated adapter runner."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import PurePosixPath
from typing import Mapping, Sequence

from .sparse_story_projection import PROJECTION_SCHEMA, PUBLIC_AUTHORITY, PUBLIC_PRIVACY, ROLES

SHA = re.compile(r"^[0-9a-f]{64}$")
PACKET = re.compile(r"^packet-[0-9a-f]{20}$")
SEGMENT = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
ASSET_SCHEMA = "aegis360.sparse-story-asset-manifest.v1"
POLICY_SCHEMA = "aegis360.sparse-story-runner-policy.v1"
REQUEST_SCHEMA = "aegis360.sparse-story-adapter-request.v1"
CAPABILITY_SCHEMA = "aegis360.sparse-story-isolation-capability.v1"
RECEIPT_SCHEMA = "aegis360.sparse-story-adapter-run-receipt.v1"
CASES_SCHEMA = "aegis360.sparse-story-runner-cases.v1"
CASE_RESULT_SCHEMA = "aegis360.sparse-story-runner-case-result.v1"
RUN_RESULT_SCHEMA = "aegis360.sparse-story-adapter-run-result.v1"
BACKEND_MANIFEST_SCHEMA = "aegis360.sparse-story-seatbelt-backend-manifest.v1"
SEATBELT_RENDERER_VERSION = "aegis360.seatbelt-policy-renderer.v1"
SEATBELT_BACKEND_IDENTITY = "com.apple.sandbox-exec"
SEATBELT_LAUNCHER_IDENTITY = "aegis360.native-process-launcher"
MAX_BACKEND_EXECUTABLE_BYTES = 16 * 1024 ** 3
SEATBELT_DYNAMIC_KEYS = {"runtime_root", "runtime_executable",
    "forbidden_executable", "bundle_root", "model_root", "prompt_root",
    "scratch_root"}
SEATBELT_SYSTEM_RULES = (
    ("file-read*", "subpath", "/System/Library"),
    ("file-read*", "subpath", "/private/var/db/dyld"),
    ("file-read*", "subpath", "/usr/lib"),
    ("file-read-data", "literal", "/"),
    ("file-read-metadata", "literal", "/tmp"))

PRIVACY = {"contains_source_path": False, "contains_pixels": False,
    "contains_audio": False, "contains_identity": False,
    "contains_source_time": False, "contains_free_text": False}
RECEIPT_AUTHORITY = {"isolated_adapter_invocation": True,
    "semantic_observation": False, "exact_boundary": False,
    "chapter_map": False, "camera": False, "reorder": False, "render": False}
RESULT_AUTHORITY = {"isolated_adapter_gate_result": True,
    "semantic_observation": False, "exact_boundary": False,
    "chapter_map": False, "camera": False, "reorder": False, "render": False}
ENVIRONMENT = {"LANG": "C", "LC_ALL": "C", "TZ": "UTC", "NO_COLOR": "1",
    "HOME": "$PRIVATE_HOME", "TMPDIR": "$PRIVATE_TMPDIR"}
MATRIX_KEYS = ("allowed_bundle_read", "allowed_model_read", "allowed_prompt_read",
    "allowed_scratch_write", "denied_repository_read", "denied_protocol_read",
    "denied_neighbor_packet_read", "denied_result_read", "denied_outside_write",
    "denied_process_fork", "denied_process_exec", "denied_ipv4", "denied_ipv6",
    "denied_unix_socket")
RUN_KINDS = {"synthetic_gate": 1, "stage_a_smoke": 1, "stage_a_run_1": 6,
             "stage_a_run_2": 6, "stage_b": 24}
FAILURE_STAGES = {"none", "preflight", "policy_compile", "capability",
                  "invocation", "publication", "cleanup"}
RESULT_ENUM = {"success", "malformed_json", "forbidden_field", "schema_violation",
    "invocation_failure", "isolation_denied", "isolation_allowed", "trust_invalid",
    "replacement_preserved", "exact_rebuild"}
CASE_SPECS = (
    ("argv_literal", "success"), ("environment_exact", "success"),
    ("fd_hygiene", "success"), ("cwd_identity", "success"),
    ("stdout_empty", "invocation_failure"), ("stdout_invalid_utf8", "malformed_json"),
    ("stdout_duplicate_key", "malformed_json"), ("stdout_nan", "malformed_json"),
    ("stdout_trailing_bytes", "malformed_json"),
    ("stdout_forbidden_field", "forbidden_field"),
    ("stdout_extra_field", "forbidden_field"),
    ("stdout_limit_minus_one", "success"), ("stdout_limit_exact", "success"),
    ("stdout_limit_plus_one", "invocation_failure"),
    ("concurrent_pipe_pressure", "success"),
    ("stderr_nonempty", "invocation_failure"),
    ("nonzero_exit", "invocation_failure"), ("signal_exit", "invocation_failure"),
    ("wall_timeout", "invocation_failure"),
    ("term_ignore_kill", "invocation_failure"),
    ("grandchild_containment", "isolation_denied"),
    ("network_ipv4_denied", "isolation_denied"),
    ("network_ipv6_denied", "isolation_denied"),
    ("unix_socket_denied", "isolation_denied"),
    ("repository_read_denied", "isolation_denied"),
    ("protocol_read_denied", "isolation_denied"),
    ("neighbor_packet_read_denied", "isolation_denied"),
    ("result_read_denied", "isolation_denied"),
    ("outside_write_denied", "isolation_denied"),
    ("bundle_read_allowed", "isolation_allowed"),
    ("model_read_allowed", "isolation_allowed"),
    ("prompt_read_allowed", "isolation_allowed"),
    ("scratch_write_allowed", "isolation_allowed"),
    ("bundle_mutation", "trust_invalid"),
    ("replacement_race", "replacement_preserved"),
    ("single_invocation", "exact_rebuild"), ("receipt_rebuild", "exact_rebuild"))


def _canonical(value: Mapping[str, object]) -> bytes:
    if not isinstance(value, Mapping): raise ValueError("canonical value must be an object")
    try: return json.dumps(value, allow_nan=False, ensure_ascii=True, sort_keys=True,
                           separators=(",", ":")).encode()
    except (TypeError, ValueError) as error: raise ValueError("value is not canonical JSON") from error


def canonical_bytes(value): return _canonical(value)
def sha256(value): return hashlib.sha256(_canonical(value)).hexdigest()
class AuthorityUnavailable(ValueError):
    """Raised when a structural codec is asked to manufacture runner authority."""


def canonical_asset_manifest_shape_bytes(value): validate_asset_manifest_shape(value); return _canonical(value)
def canonical_seatbelt_backend_manifest_shape_bytes(value): validate_seatbelt_backend_manifest_shape(value); return _canonical(value)
def canonical_runner_policy_bytes(value, **inputs): validate_runner_policy(value, **inputs); return _canonical(value)
def canonical_adapter_request_shape_bytes(value): validate_adapter_request_shape(value); return _canonical(value)
def canonical_capability_receipt_shape_bytes(value): validate_capability_receipt_shape(value); return _canonical(value)
def canonical_run_receipt_shape_bytes(value): validate_run_receipt_shape(value); return _canonical(value)
def canonical_case_manifest_bytes(value, **inputs): validate_case_manifest(value, **inputs); return _canonical(value)
def canonical_case_result_shape_bytes(value, *, case_manifest): validate_case_result_shape(value, case_manifest=case_manifest); return _canonical(value)
def canonical_run_result_shape_bytes(value): validate_run_result_shape(value); return _canonical(value)


def canonical_asset_manifest_bytes(*args, **kwargs):
    raise AuthorityUnavailable("asset serialization requires retained-FD filesystem proof")


def canonical_seatbelt_backend_manifest_bytes(*args, **kwargs):
    raise AuthorityUnavailable("backend serialization requires coordinator-owned raw proofs")


def derive_seatbelt_backend_manifest(*args, **kwargs):
    raise AuthorityUnavailable("backend derivation requires coordinator-owned raw proofs")


def validate_seatbelt_backend_manifest(*args, **kwargs):
    raise AuthorityUnavailable("backend authority requires coordinator-owned raw proofs")


def canonical_seatbelt_policy_input_bytes(*args, **kwargs):
    raise AuthorityUnavailable("installed policy authority requires coordinator-owned raw proofs")


def canonical_adapter_request_bytes(*args, **kwargs):
    raise AuthorityUnavailable("request serialization requires exact index and retained-root proofs")


def canonical_capability_receipt_bytes(*args, **kwargs):
    raise AuthorityUnavailable("capability serialization requires coordinator-owned raw probe proofs")


def canonical_run_receipt_bytes(*args, **kwargs):
    raise AuthorityUnavailable("run receipt serialization requires an attested capture and coordinator")


def canonical_case_result_bytes(*args, **kwargs):
    raise AuthorityUnavailable("case result serialization requires coordinator-owned execution proofs")


def canonical_run_result_bytes(*args, **kwargs):
    raise AuthorityUnavailable("aggregate serialization requires coordinator-owned raw proofs")
def _is_sha(value): return isinstance(value, str) and SHA.fullmatch(value) is not None


def _safe_path(value: object) -> bool:
    if not isinstance(value, str): return False
    try: encoded = value.encode("utf-8")
    except UnicodeError: return False
    if not 1 <= len(encoded) <= 1024: return False
    path = PurePosixPath(value)
    return (not path.is_absolute() and path.as_posix() == value
            and all(part not in {".", ".."} and SEGMENT.fullmatch(part) for part in path.parts))


def _tree_digest(entries) -> str:
    lines = [f"{entry['sha256']}  {entry['relative_path']}\n" for entry in entries]
    return hashlib.sha256("".join(lines).encode()).hexdigest()


def _closed_token(value, label):
    if (not isinstance(value, str) or not value
            or len(value.encode("utf-8")) > 128
            or re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", value) is None):
        raise ValueError(f"{label} is invalid")
    return value


def _absolute_policy_path(value, label):
    if not isinstance(value, str):
        raise ValueError(f"{label} is invalid")
    try:
        encoded = value.encode("utf-8")
        path = PurePosixPath(value)
    except (UnicodeError, ValueError):
        raise ValueError(f"{label} is invalid") from None
    if (not 1 <= len(encoded) <= 4096 or not path.is_absolute()
            or path == PurePosixPath("/") or path.as_posix() != value
            or any(part in {".", ".."} for part in path.parts)
            or any(ord(character) < 32 or ord(character) == 127 for character in value)):
        raise ValueError(f"{label} is invalid")
    return path


def _beneath(path, root):
    return path != root and root in path.parents


def build_seatbelt_backend_manifest_shape(*, os_build: str, architecture: str,
        backend_executable_sha256: str, backend_executable_size: int,
        launcher_runtime_manifest_sha256: str, system_version_sha256: str):
    _closed_token(os_build, "OS build")
    if (architecture != "arm64" or not _is_sha(backend_executable_sha256)
            or type(backend_executable_size) is not int
            or not 1 <= backend_executable_size <= MAX_BACKEND_EXECUTABLE_BYTES
            or not _is_sha(launcher_runtime_manifest_sha256)
            or not _is_sha(system_version_sha256)):
        raise ValueError("backend host or hashes are invalid")
    return {"schema_version": BACKEND_MANIFEST_SCHEMA,
        "renderer_version": SEATBELT_RENDERER_VERSION,
        "host": {"operating_system": "macOS", "os_build": os_build,
                 "architecture": architecture,
                 "system_version_sha256": system_version_sha256},
        "backend": {"logical_identity": SEATBELT_BACKEND_IDENTITY,
                    "executable_sha256": backend_executable_sha256,
                    "executable_size": backend_executable_size},
        "launcher": {"logical_identity": SEATBELT_LAUNCHER_IDENTITY,
                     "runtime_manifest_sha256": launcher_runtime_manifest_sha256},
        "system_rules": [{"operation": operation, "match": match, "path": path}
                         for operation, match, path in SEATBELT_SYSTEM_RULES]}


def validate_seatbelt_backend_manifest_shape(value):
    if (not isinstance(value, Mapping)
            or set(value) != {"schema_version", "renderer_version", "host",
                              "backend", "launcher", "system_rules"}
            or value.get("schema_version") != BACKEND_MANIFEST_SCHEMA
            or value.get("renderer_version") != SEATBELT_RENDERER_VERSION
            or not isinstance(value.get("host"), Mapping)
            or set(value["host"]) != {"operating_system", "os_build", "architecture",
                                      "system_version_sha256"}
            or value["host"].get("operating_system") != "macOS"
            or not isinstance(value.get("backend"), Mapping)
            or set(value["backend"]) != {"logical_identity", "executable_sha256",
                                         "executable_size"}
            or value["backend"].get("logical_identity") != SEATBELT_BACKEND_IDENTITY
            or not isinstance(value.get("launcher"), Mapping)
            or set(value["launcher"]) != {"logical_identity", "runtime_manifest_sha256"}
            or value["launcher"].get("logical_identity") != SEATBELT_LAUNCHER_IDENTITY):
        raise ValueError("backend manifest shape is invalid")
    rebuilt = build_seatbelt_backend_manifest_shape(
        os_build=value["host"]["os_build"], architecture=value["host"]["architecture"],
        backend_executable_sha256=value["backend"]["executable_sha256"],
        backend_executable_size=value["backend"]["executable_size"],
        launcher_runtime_manifest_sha256=value["launcher"]["runtime_manifest_sha256"],
        system_version_sha256=value["host"]["system_version_sha256"])
    if value != rebuilt:
        raise ValueError("backend manifest must exactly rebuild")


def _sbpl_string(value):
    return json.dumps(value, ensure_ascii=True, separators=(",", ":"))


def render_seatbelt_policy_input_shape_bytes(*,
        backend_manifest: Mapping[str, object], dynamic_roots: Mapping[str, str]):
    """Render deterministic candidate bytes without claiming installation authority."""
    validate_seatbelt_backend_manifest_shape(backend_manifest)
    if not isinstance(dynamic_roots, Mapping) or set(dynamic_roots) != SEATBELT_DYNAMIC_KEYS:
        raise ValueError("Seatbelt dynamic roots are invalid")
    paths = {name: _absolute_policy_path(dynamic_roots[name], name)
             for name in SEATBELT_DYNAMIC_KEYS}
    if len(set(paths.values())) != len(paths):
        raise ValueError("Seatbelt dynamic roots must be distinct")
    if not _beneath(paths["runtime_executable"], paths["runtime_root"]):
        raise ValueError("runtime executable must be beneath runtime root")
    scoped_roots = [paths[name] for name in ("runtime_root", "bundle_root",
        "model_root", "prompt_root", "scratch_root")]
    if any(left == right or left in right.parents or right in left.parents
           for number, left in enumerate(scoped_roots)
           for right in scoped_roots[number + 1:]):
        raise ValueError("Seatbelt roots must not overlap")
    if any(paths["forbidden_executable"] == root
           or root in paths["forbidden_executable"].parents
           or paths["forbidden_executable"] in root.parents
           for root in scoped_roots):
        raise ValueError("forbidden executable overlaps an allowed root")
    runtime = _sbpl_string(str(paths["runtime_executable"]))
    forbidden = _sbpl_string(str(paths["forbidden_executable"]))
    lines = ["(version 1)", "(deny default)",
        f"(allow process-exec (literal {runtime}))", "(deny process-fork)",
        "(allow process-info* (target self))",
        f"(allow file-read* (literal {runtime})", f"  (literal {forbidden})"]
    read_roots = sorted(str(paths[name]) for name in
        ("runtime_root", "bundle_root", "model_root", "prompt_root"))
    lines.extend(f"  (subpath {_sbpl_string(path)})" for path in read_roots)
    lines[-1] += ")"
    for row in backend_manifest["system_rules"]:
        lines.append(f"(allow {row['operation']} ({row['match']} "
                     f"{_sbpl_string(row['path'])}))")
    lines.append(f"(allow file-write* (subpath "
                 f"{_sbpl_string(str(paths['scratch_root']))}))")
    encoded = ("\n".join(lines) + "\n").encode("ascii")
    if b"(allow default)" in encoded:
        raise ValueError("allow-default policy is forbidden")
    return encoded


def build_asset_manifest_shape(*, asset_kind: str, entries: Sequence[Mapping[str, object]],
                         entrypoint: str | None = None):
    if asset_kind not in {"runtime", "model", "prompt_schema", "synthetic_support"}:
        raise ValueError("asset kind is invalid")
    if not isinstance(entries, Sequence) or isinstance(entries, (str, bytes)): raise ValueError("entries are invalid")
    if any(not isinstance(row, Mapping) for row in entries): raise ValueError("entries are invalid")
    rows = [dict(row) for row in entries]
    try: ordered = sorted(rows, key=lambda row: row.get("relative_path", "").encode())
    except (AttributeError, UnicodeError): raise ValueError("entries are invalid") from None
    if rows != ordered: raise ValueError("entries are not bytewise sorted")
    if len({row.get("relative_path") for row in rows}) != len(rows): raise ValueError("entry paths are duplicated")
    for row in rows:
        if (set(row) != {"relative_path", "mode", "size", "sha256"}
                or not _safe_path(row["relative_path"])
                or type(row["mode"]) is not int or type(row["size"]) is not int
                or row["size"] < 0 or not _is_sha(row["sha256"])):
            raise ValueError("asset entry is invalid")
        expected_mode = 0o555 if asset_kind == "runtime" and row["relative_path"] == entrypoint else 0o444
        if row["mode"] != expected_mode: raise ValueError("asset entry mode is invalid")
    if asset_kind == "synthetic_support":
        if entrypoint is not None: raise ValueError("support entrypoint must be null")
    elif not rows: raise ValueError("asset manifest cannot be empty")
    if asset_kind == "runtime":
        if not _safe_path(entrypoint) or entrypoint not in {r["relative_path"] for r in rows}: raise ValueError("runtime entrypoint is invalid")
    elif entrypoint is not None: raise ValueError("non-runtime entrypoint must be null")
    return {"schema_version": ASSET_SCHEMA, "asset_kind": asset_kind,
        "root_tree_sha256": _tree_digest(rows), "entrypoint": entrypoint, "entries": rows}


def validate_asset_manifest_shape(value):
    if not isinstance(value, Mapping) or set(value) != {"schema_version", "asset_kind", "root_tree_sha256", "entrypoint", "entries"} or value.get("schema_version") != ASSET_SCHEMA:
        raise ValueError("asset manifest shape is invalid")
    if value != build_asset_manifest_shape(asset_kind=value["asset_kind"], entries=value["entries"], entrypoint=value["entrypoint"]): raise ValueError("asset manifest shape must exactly rebuild")


def validate_asset_manifest(*args, **kwargs):
    raise AuthorityUnavailable("asset authority requires retained-FD filesystem proof")


def build_runner_policy(*, backend_manifest_sha256: str):
    if not _is_sha(backend_manifest_sha256): raise ValueError("backend manifest hash is invalid")
    return {"schema_version": POLICY_SCHEMA, "backend_manifest_sha256": backend_manifest_sha256,
        "timeout_ns": 120000000000, "termination_grace_ns": 2000000000,
        "stdout_limit_bytes": 65536, "stderr_limit_bytes": 65536,
        "environment_template": dict(ENVIRONMENT),
        "capability_matrix_id": "sparse-story-isolation-matrix-v1"}


def validate_runner_policy(value, *, backend_manifest_sha256):
    if value != build_runner_policy(backend_manifest_sha256=backend_manifest_sha256): raise ValueError("runner policy must exactly rebuild")


def _validate_projection(projection, packet_id):
    if (not isinstance(projection, Mapping)
            or set(projection) != {"schema_version", "packet_id", "rows", "privacy", "authority"}
            or projection.get("schema_version") != PROJECTION_SCHEMA
            or projection.get("packet_id") != packet_id
            or projection.get("privacy") != PUBLIC_PRIVACY
            or projection.get("authority") != PUBLIC_AUTHORITY
            or not isinstance(projection.get("rows"), list) or len(projection["rows"]) != 6):
        raise ValueError("adapter projection is invalid")
    refs = []
    for number, (row, role) in enumerate(zip(projection["rows"], ROLES), 1):
        expected_ref = f"media/{packet_id}/row-{number:02d}.png"
        if (not isinstance(row, Mapping)
                or set(row) != {"row_number", "row_role", "media_ref", "views"}
                or type(row.get("row_number")) is not int
                or row.get("row_number") != number or row.get("row_role") != role
                or row.get("media_ref") != expected_ref
                or row.get("views") != ["view-1", "view-2", "view-3", "view-4"]):
            raise ValueError("projection rows are invalid")
        refs.append(row["media_ref"])
    return refs


def build_adapter_request_shape(*, packet_id: str, projection: Mapping[str, object],
        prompt_schema_manifest: Mapping[str, object], prompt_schema_root_path: str,
        model_manifest: Mapping[str, object], model_root_path: str):
    if not isinstance(packet_id, str) or PACKET.fullmatch(packet_id) is None: raise ValueError("packet id is invalid")
    refs = _validate_projection(projection, packet_id)
    validate_asset_manifest_shape(prompt_schema_manifest); validate_asset_manifest_shape(model_manifest)
    if (prompt_schema_manifest.get("asset_kind") != "prompt_schema"
            or model_manifest.get("asset_kind") != "model"
            or not {"prompt.txt", "raw-observation-schema.json"}.issubset(
                {row["relative_path"] for row in prompt_schema_manifest["entries"]})):
        raise ValueError("request asset manifests are invalid")
    for root in (prompt_schema_root_path, model_root_path):
        path = PurePosixPath(root) if isinstance(root, str) else None
        if (path is None or not path.is_absolute() or path.as_posix() != root
                or any(part in {".", ".."} for part in path.parts)):
            raise ValueError("asset root must be canonical absolute path")
    return {"schema_version": REQUEST_SCHEMA, "packet_id": packet_id,
        "projection": json.loads(_canonical(projection)),
        "media": [{"media_ref": ref, "path": ref} for ref in refs],
        "prompt_schema": {"manifest_sha256": sha256(prompt_schema_manifest),
            "root_path": prompt_schema_root_path, "prompt_path": "prompt.txt",
            "schema_path": "raw-observation-schema.json"},
        "model": {"manifest_sha256": sha256(model_manifest), "root_path": model_root_path}}


def validate_adapter_request_shape(value):
    if not isinstance(value, Mapping) or set(value) != {"schema_version", "packet_id", "projection", "media", "prompt_schema", "model"} or value.get("schema_version") != REQUEST_SCHEMA:
        raise ValueError("adapter request shape is invalid")
    prompt, model = value.get("prompt_schema"), value.get("model")
    if (not isinstance(prompt, Mapping) or set(prompt) != {"manifest_sha256", "root_path", "prompt_path", "schema_path"}
            or prompt.get("prompt_path") != "prompt.txt" or prompt.get("schema_path") != "raw-observation-schema.json"
            or not _is_sha(prompt.get("manifest_sha256"))
            or not isinstance(model, Mapping) or set(model) != {"manifest_sha256", "root_path"}
            or not _is_sha(model.get("manifest_sha256"))): raise ValueError("request asset handles are invalid")
    packet_id = value.get("packet_id"); refs = _validate_projection(value.get("projection"), packet_id)
    if value.get("media") != [{"media_ref": ref, "path": ref} for ref in refs]: raise ValueError("request media order is invalid")
    for root in (prompt.get("root_path"), model.get("root_path")):
        path = PurePosixPath(root) if isinstance(root, str) else None
        if path is None or not path.is_absolute() or path.as_posix() != root or any(part in {".", ".."} for part in path.parts): raise ValueError("request root handle is invalid")


def validate_adapter_request(*args, **kwargs):
    raise AuthorityUnavailable("request authority requires exact one-packet index proof and retained roots")


def validate_capability_receipt_shape(value):
    expected_keys = {"schema_version", "backend_manifest_sha256",
                     "compiled_policy_sha256", "runner_policy_sha256", "matrix"}
    if (not isinstance(value, Mapping) or set(value) != expected_keys
            or value.get("schema_version") != CAPABILITY_SCHEMA
            or not all(_is_sha(value.get(key)) for key in
                ("backend_manifest_sha256", "compiled_policy_sha256", "runner_policy_sha256"))
            or value.get("matrix") != {key: True for key in MATRIX_KEYS}):
        raise ValueError("capability receipt shape is invalid")


def validate_run_receipt_shape(value):
    input_keys = {"adapter_projection_sha256", "sanitized_media_result_sha256",
        "runtime_manifest_sha256", "model_manifest_sha256",
        "prompt_schema_manifest_sha256", "runner_policy_sha256"}
    execution_keys = {"invocation_count", "stdout_present", "stdout_sha256", "invocation_failed"}
    if (not isinstance(value, Mapping)
            or set(value) != {"schema_version", "packet_id", "inputs", "execution", "privacy", "authority"}
            or value.get("schema_version") != RECEIPT_SCHEMA
            or not isinstance(value.get("packet_id"), str) or PACKET.fullmatch(value["packet_id"]) is None
            or not isinstance(value.get("inputs"), Mapping) or set(value["inputs"]) != input_keys
            or not all(_is_sha(item) for item in value["inputs"].values())
            or not isinstance(value.get("execution"), Mapping) or set(value["execution"]) != execution_keys
            or type(value["execution"].get("invocation_count")) is not int
            or value["execution"]["invocation_count"] != 1
            or type(value["execution"].get("stdout_present")) is not bool
            or not _is_sha(value["execution"].get("stdout_sha256"))
            or type(value["execution"].get("invocation_failed")) is not bool
            or value.get("privacy") != PRIVACY or value.get("authority") != RECEIPT_AUTHORITY):
        raise ValueError("run receipt shape is invalid")


def derive_capability_receipt(*args, **kwargs):
    raise AuthorityUnavailable("capability authority requires coordinator-owned raw probe proofs")


def derive_run_receipt(*args, **kwargs):
    raise AuthorityUnavailable("run receipt authority requires an attested capture and coordinator")


def validate_capability_receipt(*args, **kwargs):
    raise AuthorityUnavailable("capability validation requires coordinator-owned raw probe proofs")


def validate_run_receipt(*args, **kwargs):
    raise AuthorityUnavailable("run receipt validation requires an attested capture and coordinator")


def build_case_manifest(*, synthetic_adapter_manifest_sha256: str,
        cases: Sequence[Mapping[str, object]], repeat_packet_id: str):
    if not _is_sha(synthetic_adapter_manifest_sha256) or not isinstance(repeat_packet_id, str) or PACKET.fullmatch(repeat_packet_id) is None: raise ValueError("case manifest inputs are invalid")
    if not isinstance(cases, Sequence) or isinstance(cases, (str, bytes)) or len(cases) != len(CASE_SPECS): raise ValueError("case list is invalid")
    rows = []
    for source, (case_id, expected) in zip(cases, CASE_SPECS):
        if not isinstance(source, Mapping) or set(source) != {"case_id", "expected_result", "stimulus"} or source.get("case_id") != case_id or source.get("expected_result") != expected: raise ValueError("case sequence is invalid")
        stimulus = source["stimulus"]
        if (not isinstance(stimulus, Mapping) or set(stimulus) != {"argv", "stdin_sha256", "support_manifest_sha256"}
                or not isinstance(stimulus["argv"], list) or any(not isinstance(x, str) for x in stimulus["argv"])
                or not _is_sha(stimulus["stdin_sha256"]) or not _is_sha(stimulus["support_manifest_sha256"])): raise ValueError("case stimulus is invalid")
        rows.append({"case_id": case_id, "expected_result": expected,
            "stimulus": {"argv": list(stimulus["argv"]),
                "stdin_sha256": stimulus["stdin_sha256"],
                "support_manifest_sha256": stimulus["support_manifest_sha256"]}})
    return {"schema_version": CASES_SCHEMA,
        "synthetic_adapter_manifest_sha256": synthetic_adapter_manifest_sha256,
        "cases": rows, "repeat_packet_id": repeat_packet_id}


def validate_case_manifest(value, **inputs):
    if value != build_case_manifest(**inputs): raise ValueError("case manifest must exactly rebuild")


def validate_case_result_shape(value, *, case_manifest: Mapping[str, object]):
    validate_case_manifest(case_manifest,
        synthetic_adapter_manifest_sha256=case_manifest.get("synthetic_adapter_manifest_sha256"),
        cases=case_manifest.get("cases"), repeat_packet_id=case_manifest.get("repeat_packet_id"))
    if (not isinstance(value, Mapping)
            or set(value) != {"schema_version", "case_manifest_sha256", "cases", "repeatability"}
            or value.get("schema_version") != CASE_RESULT_SCHEMA
            or value.get("case_manifest_sha256") != sha256(case_manifest)
            or not isinstance(value.get("cases"), list)
            or len(value["cases"]) != len(CASE_SPECS)):
        raise ValueError("case result shape is invalid")
    for row, source in zip(value["cases"], case_manifest["cases"]):
        if (not isinstance(row, Mapping)
                or set(row) != {"case_id", "expected_result", "observed_result", "passed"}
                or row.get("case_id") != source["case_id"]
                or row.get("expected_result") != source["expected_result"]
                or row.get("observed_result") not in RESULT_ENUM
                or type(row.get("passed")) is not bool
                or row["passed"] != (row["observed_result"] == row["expected_result"])):
            raise ValueError("case result row shape is invalid")
    repeat = value.get("repeatability")
    if (not isinstance(repeat, Mapping)
            or set(repeat) != {"packet_id", "first_stdout_sha256", "second_stdout_sha256", "equal"}
            or repeat.get("packet_id") != case_manifest["repeat_packet_id"]
            or not _is_sha(repeat.get("first_stdout_sha256"))
            or not _is_sha(repeat.get("second_stdout_sha256"))
            or type(repeat.get("equal")) is not bool
            or repeat["equal"] != (repeat["first_stdout_sha256"] == repeat["second_stdout_sha256"])):
        raise ValueError("case repeatability shape is invalid")


def derive_case_result(*args, **kwargs):
    raise AuthorityUnavailable("case observations require coordinator-owned execution proofs")


def validate_case_result(*args, **kwargs):
    raise AuthorityUnavailable("case PASS validation requires coordinator-owned execution proofs")


def validate_run_result_shape(value):
    if (not isinstance(value, Mapping)
            or set(value) != {"schema_version", "run_kind", "inputs", "packets", "runner_outcome", "privacy", "authority"}
            or value.get("schema_version") != RUN_RESULT_SCHEMA
            or value.get("run_kind") not in RUN_KINDS
            or value.get("runner_outcome") not in {"invalid", "reject", "pass"}
            or value.get("privacy") != PRIVACY or value.get("authority") != RESULT_AUTHORITY):
        raise ValueError("runner aggregate shape is invalid")
    run_kind = value["run_kind"]; runner_outcome = value["runner_outcome"]
    inputs = value.get("inputs")
    input_keys = {"schedule_sha256", "backend_manifest_sha256", "runner_policy_sha256",
        "compiled_policy_sha256", "capability_receipt_sha256",
        "synthetic_adapter_manifest_sha256", "synthetic_case_manifest_sha256",
        "synthetic_case_result_sha256", "failure_stage"}
    if (not isinstance(inputs, Mapping) or set(inputs) != input_keys
            or not all(_is_sha(inputs.get(key)) for key in
                ("schedule_sha256", "backend_manifest_sha256", "runner_policy_sha256"))
            or inputs.get("failure_stage") not in FAILURE_STAGES):
        raise ValueError("aggregate input shape is invalid")
    nullable_names = ("compiled_policy_sha256", "capability_receipt_sha256",
        "synthetic_adapter_manifest_sha256", "synthetic_case_manifest_sha256",
        "synthetic_case_result_sha256")
    if any(inputs.get(key) is not None and not _is_sha(inputs.get(key)) for key in nullable_names):
        raise ValueError("aggregate nullable hash is invalid")
    failure_stage = inputs["failure_stage"]
    expected_compiled = failure_stage not in {"preflight", "policy_compile"}
    expected_capability = failure_stage not in {"preflight", "policy_compile", "capability"}
    if ((inputs["compiled_policy_sha256"] is not None) != expected_compiled
            or (inputs["capability_receipt_sha256"] is not None) != expected_capability):
        raise ValueError("aggregate lifecycle is inconsistent")
    synthetic_names = nullable_names[2:]
    if run_kind != "synthetic_gate" and any(inputs[key] is not None for key in synthetic_names):
        raise ValueError("non-synthetic aggregate has synthetic hashes")
    if runner_outcome in {"pass", "reject"}:
        if failure_stage != "none" or not all(inputs[key] is not None for key in nullable_names):
            raise ValueError("completed aggregate shape is incomplete")
        if runner_outcome == "reject" and run_kind != "synthetic_gate":
            raise ValueError("only synthetic shape can reject")
    elif failure_stage == "none": raise ValueError("invalid aggregate lacks failure stage")
    packets = value.get("packets")
    if not isinstance(packets, list) or len(packets) != RUN_KINDS[run_kind]:
        raise ValueError("aggregate packet count is invalid")
    packet_ids = set()
    for row in packets:
        if (not isinstance(row, Mapping)
                or set(row) != {"packet_id", "invocation_count", "receipt_sha256", "evidence_sha256"}
                or not isinstance(row.get("packet_id"), str) or PACKET.fullmatch(row["packet_id"]) is None
                or row["packet_id"] in packet_ids
                or type(row.get("invocation_count")) is not int
                or row["invocation_count"] not in {0, 1}):
            raise ValueError("aggregate packet row shape is invalid")
        packet_ids.add(row["packet_id"]); receipt = row.get("receipt_sha256"); evidence = row.get("evidence_sha256")
        if row["invocation_count"] == 0:
            if receipt is not None or evidence is not None: raise ValueError("zero invocation has artifacts")
        elif not ((receipt is None and evidence is None) or (_is_sha(receipt) and _is_sha(evidence))):
            raise ValueError("aggregate artifacts are partial")
        if runner_outcome in {"pass", "reject"} and (row["invocation_count"] != 1 or not _is_sha(receipt) or not _is_sha(evidence)):
            raise ValueError("completed packet shape is incomplete")
    if failure_stage in {"preflight", "policy_compile", "capability"} and any(row["invocation_count"] for row in packets):
        raise ValueError("pre-invocation failure has invocation")


def derive_run_result(*args, **kwargs):
    raise AuthorityUnavailable("aggregate authority requires coordinator-owned raw proofs")


def build_run_result(*args, **kwargs):
    """Compatibility trap: authority-bearing aggregate construction is unavailable."""
    raise AuthorityUnavailable("aggregate construction requires coordinator-owned raw proofs")


def validate_run_result(*args, **inputs):
    raise AuthorityUnavailable("authoritative aggregate validation requires raw proofs")


def derive_runner_outcome(*args, **kwargs):
    raise AuthorityUnavailable("runner outcome requires coordinator-owned raw proofs")


def derive_synthetic_run_result(*args, **kwargs):
    raise AuthorityUnavailable("synthetic outcome requires coordinator-owned case proofs")
