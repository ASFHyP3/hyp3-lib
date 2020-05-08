#!/usr/bin/env bash

# Get our API endpoint
[[ ${CI_PROJECT_URL} =~ ^https?://[^/]+ ]] && GITLAB_API="${BASH_REMATCH[0]}/api/v4/projects"

# Get the default branch as our MR target
TARGET_BRANCH=$(curl --silent "${GITLAB_API}/${CI_PROJECT_ID}" --header "PRIVATE-TOKEN:${GITLAB_TOOLS_BOT_PAK}" | \
    jq -c --raw-output '.default_branch' \
    )

MR_TITLE="\"Bring ${CI_COMMIT_REF_NAME} into ${TARGET_BRANCH}\""

MR_DATA="{
        \"id\": ${CI_PROJECT_ID},
        \"source_branch\": \"${CI_COMMIT_REF_NAME}\",
        \"target_branch\": \"${TARGET_BRANCH}\",
        \"remove_source_branch\": false,
        \"title\": ${MR_TITLE},
        \"assignee_id\":\"${GITLAB_USER_ID}\"
    }"

# Open the MR
curl -X POST "${GITLAB_API}/${CI_PROJECT_ID}/merge_requests" \
    --header "PRIVATE-TOKEN:${GITLAB_TOOLS_BOT_PAK}" \
    --header "Content-Type: application/json" \
    --data "${MR_DATA}"

echo "Opened Merge Request ${MR_TITLE} and assigned it to ${GITLAB_USER_NAME}"