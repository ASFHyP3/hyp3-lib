#!/usr/bin/env bash

# Get our API endpoint
[[ ${CI_PROJECT_URL} =~ ^https?://[^/]+ ]] && GITLAB_API="${BASH_REMATCH[0]}/api/v4/projects"

# Determine latest commit from the merged branch
MERGE_REQUEST_PARENT=$(git log --pretty=%P -n 1 "${CI_COMMIT_SHA}" | awk -F ' ' '{print $2}')

# Find the merge request associated with MERGE_REQUEST_PARENT and get the major/minor/patch tags
BUMP_PART=$(curl -LsS -H "PRIVATE-TOKEN:${GITLAB_TOOLS_BOT_PAK}" \
    "${GITLAB_API}/${CI_PROJECT_ID}/repository/commits/${MERGE_REQUEST_PARENT}/merge_requests" | \
    jq -c --raw-output '.[0].labels[] | select(. == "major" or . == "minor" or . == "patch")' | sort | head -1 \
    )

# Do the bump and make a tag
bump2version --current-version $(git describe --abbrev=0) --tag --tag-message "$(printf "%q" "${CI_COMMIT_MESSAGE}")" "${BUMP_PART}"

# send the tags upstream
git push --tags

echo "Tagged version $(git describe --abbrev=0) and pushed back to repo"