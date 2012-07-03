

def parse(lexer_class, parser_class, parser_state, string):
    tokens = lexer_class().get_tokens_unprocessed(string)
    parsed = parser_class(tokens, parser_state).parse()
    return parsed
