import os

from env_file import load_env_file, read_env_file


def test_reads_key_value_lines(tmp_path):
    f = tmp_path / ".env"
    f.write_text("# comment\n\nA=1\nB = two\nC='quoted'\nD=\"double\"\nE=\nnot a pair\n")
    assert read_env_file(f) == {"A": "1", "B": "two", "C": "quoted", "D": "double"}


def test_missing_file_gives_nothing(tmp_path):
    assert read_env_file(tmp_path / "absent") == {}


def test_values_are_loaded_into_the_environment(tmp_path, monkeypatch):
    monkeypatch.delenv("TEST_ENV_FILE_VALUE", raising=False)
    f = tmp_path / ".env"
    f.write_text("TEST_ENV_FILE_VALUE=from_file\n")
    load_env_file(f)
    assert os.environ["TEST_ENV_FILE_VALUE"] == "from_file"


def test_real_environment_variable_wins_over_the_file(tmp_path, monkeypatch):
    monkeypatch.setenv("TEST_ENV_FILE_VALUE", "from_shell")
    f = tmp_path / ".env"
    f.write_text("TEST_ENV_FILE_VALUE=from_file\n")
    load_env_file(f)
    assert os.environ["TEST_ENV_FILE_VALUE"] == "from_shell"
