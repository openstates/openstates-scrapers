from .bills import split_columns

# Trimmed from https://www.scstatehouse.gov/votehistory.php?KEY=27657 (S 830,
# 05/07/2026). "Henderson-Myers,, Rosalyn D., Ph.D." is wide enough to leave a
# single space before the next column.
PAGE = [
    "            Hartnett, Thomas F., Jr.            Hartz, Charles V.                Hayes, Jackie E.",
    "            Henderson-Myers,, Rosalyn D., Ph.D. Herbkersman, William G.          Hewitt, Lee",
    "            Hiott, David R.                     Hixon, William M.                Holman, Harriet A.",
]


def test_long_name_does_not_swallow_the_next_column():
    names = list(split_columns([PAGE]))
    assert len(names) == 9
    assert names[3:6] == [
        "Henderson-Myers,, Rosalyn D., Ph.D.",
        "Herbkersman, William G.",
        "Hewitt, Lee",
    ]


def test_each_page_uses_its_own_columns():
    # a section split across two pages, laid out differently on each
    page_two = [
        "          Pedalino, Fawn M.     Pope, Thomas E.",
        "          Waters, Courtney S.",
    ]
    names = list(split_columns([PAGE, page_two]))
    assert names[-3:] == ["Pedalino, Fawn M.", "Pope, Thomas E.", "Waters, Courtney S."]
