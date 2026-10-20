"""Tests for the AES-ECB JSON protocol, incl. a known-answer vector from the app."""

import base64

from narwal_client import protocol
from narwal_client.protocol import build_app_auth, decode_frame, encode_frame


def test_frame_roundtrip():
    obj = {"request_id": "abc", "machine_id": "11-07-6a-e8", "service": "/pita/info/all", "params": {}}
    frame = encode_frame(obj)
    assert decode_frame(frame) == obj


def test_frame_is_base64_aes_blocks():
    frame = encode_frame({"service": "/pita/info/all", "params": {}})
    raw = base64.b64decode(frame)
    assert len(raw) % 16 == 0  # AES block aligned


def test_known_app_auth_vector():
    # Captured from the live app: plaintext -> this exact ciphertext.
    machine_id = "11-07-6a-e8"
    token = (
        "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9."
        "eyJ1dWlkIjoiYWI5YTAxNDNlMDZmNDE0YTg5YTg3Y2Y3YzUwZWJlODAiLCJkZXZpY2VfaWQiOiIiLCJpYXQiOjE3OTI1MTgyMjF9."
        "H_gqih3nSB37gJL8I17MmnJHrqZBGeZlLdwl-YaieVs"
    )
    expected = (
        "0MAIpIbQDsFJNxn3rwZxZCODBmNEvhMZTmUc0cTAxjLSnNWBZF+Frdg/CRETuJkjT9WBXQd8wrghQAnl4Oqe8Oc34CeutM+R53ChMw7K975"
        "FPFnt+ncCWOAj9TJXsuMKOd78rVrimRMjDhTByNm5P8DlcJcupAnNoY5fyK4ezKhYC/P+NA2ul5auhbljIlp5dS7VbnFbVn2xfxVxjcuJK"
        "wppNd8djf97uGt91TEj/YDLSTcwGkqS5SHSZvF0GMRDi1/LTTDSk4VJvAdfv8qct1kzabo/ssujjm1pEI4c20x4Kr+R0PIPeb0cnDeJl/Yg"
    )
    assert build_app_auth(machine_id, token) == expected


def test_decode_known_status_frame():
    # A real status response frame captured from the app, AES-ECB(key) base64.
    captured = (
        "2VaTTP7QNrtI5/hQBmR6H3+hZtKT7D076H2n1DvQX/9PGqjLLe+p7ind71f7YbZr"
        "G+sQ6VQ4I721wUHearO7TDCU689PKWnWtFaZve6lkkn8O6K0lG001yTabJHuL5/c+fycY5dxrrRCtKY0m1lQEkZEy5fWKK9pzEgA6uJzOh"
        "AHkB0S8M5RSymrf9oMzkjGhGtx9HMqXRri6JX401IvkTRY3eRisFic0DFec4JzAFM="
    )
    obj = decode_frame(captured)
    assert obj["code"] == 0
    assert obj["machine_id"] == "11-07-6a-e8"


def test_build_request_shape():
    req = protocol.build_request("mac", "/pita/info/all", {"x": 1})
    assert req["machine_id"] == "mac"
    assert req["service"] == "/pita/info/all"
    assert req["params"] == {"x": 1}
    assert isinstance(req["request_id"], str) and len(req["request_id"]) >= 8
