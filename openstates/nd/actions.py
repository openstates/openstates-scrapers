from billy.scrape.actions import Rule, BaseCategorizer

# These are regex patterns that map to action categories.
_categorizer_rules = (
    # pass
)


class NDCategorizer(BaseCategorizer):
    rules = _categorizer_rules
