def shorten_string(string: str, num_words: int) -> str:
    """
    Truncate a string to the first N words.
    """
    string_list = string.replace(",", "").replace(".", "").replace("$", "").split()

    if len(string_list) <= num_words:
        num_words = len(string_list)

    return " ".join(string_list[:num_words])
