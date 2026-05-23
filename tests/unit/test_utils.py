import json
import os
import stat
import pytest

from xrpld_lab.utils import sha512_half, write_file, write_executable, read_json


class TestSha512Half:
    def test_sha512_half_deterministic(self):
        hex_input = "deadbeef"
        result1 = sha512_half(hex_input)
        result2 = sha512_half(hex_input)
        assert result1 == result2

    def test_sha512_half_correct_length(self):
        hex_input = "deadbeef"
        result = sha512_half(hex_input)
        # SHA-512 produces 128 hex chars; half is 64
        assert len(result) == 64

    def test_sha512_half_uppercase(self):
        result = sha512_half("00")
        assert result == result.upper()


class TestWriteFile:
    def test_write_file(self, tmp_path):
        path = str(tmp_path / "test.txt")
        write_file(path, "hello world")
        with open(path) as f:
            assert f.read() == "hello world"


class TestWriteExecutable:
    def test_write_executable(self, tmp_path):
        path = str(tmp_path / "run.sh")
        write_executable(path, "#!/bin/bash\necho hi")
        assert os.path.exists(path)
        file_stat = os.stat(path)
        assert file_stat.st_mode & stat.S_IXUSR  # owner execute bit
        assert file_stat.st_mode & stat.S_IXGRP  # group execute bit
        assert file_stat.st_mode & stat.S_IXOTH  # other execute bit


class TestReadJson:
    def test_read_json(self, tmp_path):
        path = str(tmp_path / "data.json")
        data = {"key": "value", "count": 42}
        with open(path, "w") as f:
            json.dump(data, f)
        result = read_json(path)
        assert result == data

    def test_read_json_nested(self, tmp_path):
        path = str(tmp_path / "nested.json")
        data = {"outer": {"inner": [1, 2, 3]}}
        with open(path, "w") as f:
            json.dump(data, f)
        result = read_json(path)
        assert result["outer"]["inner"] == [1, 2, 3]
