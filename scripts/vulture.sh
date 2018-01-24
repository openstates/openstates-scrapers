#!/bin/sh

vulture openstates/ --exclude=openstates/ca/models.py \
    | grep -v "unused class" \
    | grep -v "unused attribute" \
    | grep -v "settings" \
    | grep -v "scrapers" \
    | grep -v "ignored_scraped_sessions" \
    | grep -v "get_session_list" \
    | grep -v "get_organizations" \
    | grep -v "handle_list_item" \
    | grep -v "delete_session"
