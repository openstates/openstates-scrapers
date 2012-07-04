import pprint


def parse(lexer_class, parser_class, parser_state, string):
    tokens = list(lexer_class().get_tokens_unprocessed(string))
    pprint.pprint(tokens)
    parsed = parser_class(tokens, parser_state).parse()
    return parsed
