from bot.formatters import split_long_message


def test_short_message_single_chunk():
    assert split_long_message("hello") == ["hello"]


def test_long_message_is_split():
    text = "\n".join(f"line {i}" for i in range(2000))
    chunks = split_long_message(text, max_len=1000)
    assert len(chunks) > 1
    assert all(len(c) <= 1000 for c in chunks)


def test_split_preserves_all_content_words():
    text = "alpha\nbravo\ncharlie\n" * 500
    chunks = split_long_message(text, max_len=200)
    rejoined = "".join(chunks)
    for word in ("alpha", "bravo", "charlie"):
        assert word in rejoined
