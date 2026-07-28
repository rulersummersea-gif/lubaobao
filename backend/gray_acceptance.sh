#!/bin/sh

set -eu

API_BASE="${API_BASE:-http://127.0.0.1:28080}"
PHOTO_FILE="${PHOTO_FILE:-/tmp/lubaobao-manual-render-8/page-1.png}"
MONTH="${MONTH:-$(date +%Y-%m)}"

if ! command -v jq >/dev/null 2>&1; then
  echo "FAIL: 需要先安装 jq"
  exit 1
fi

if [ ! -f "$PHOTO_FILE" ]; then
  echo "FAIL: 验收图片不存在: $PHOTO_FILE"
  exit 1
fi

step() {
  printf '\n[%s] %s\n' "$1" "$2"
}

api_json() {
  api_method="$1"
  api_path="$2"
  api_token="$3"
  api_body="${4:-}"
  if [ -n "$api_token" ] && [ -n "$api_body" ]; then
    curl -fsS -X "$api_method" "$API_BASE$api_path" \
      -H "Authorization: Bearer $api_token" \
      -H "Content-Type: application/json" \
      -d "$api_body"
  elif [ -n "$api_token" ]; then
    curl -fsS -X "$api_method" "$API_BASE$api_path" \
      -H "Authorization: Bearer $api_token" \
      -H "Content-Type: application/json"
  elif [ -n "$api_body" ]; then
    curl -fsS -X "$api_method" "$API_BASE$api_path" \
      -H "Content-Type: application/json" \
      -d "$api_body"
  else
    curl -fsS -X "$api_method" "$API_BASE$api_path" \
      -H "Content-Type: application/json"
  fi
}

step 1 "检查 API 健康状态"
health="$(api_json GET /health "")"
printf '%s' "$health" | jq -e '.ok == true' >/dev/null

step 2 "登录灰测用户并检查绑定状态"
login="$(api_json POST /auth/wx-login "" '{"code":"h5-pilot"}')"
token="$(printf '%s' "$login" | jq -r '.token')"
printf '%s' "$login" | jq -e '
  .user.id != null and
  .onboarding.canEnterHome == true and
  .onboarding.canInspect == true and
  .onboarding.binding.materialPackId != null
' >/dev/null
boiler_id="$(printf '%s' "$login" | jq -r '.onboarding.binding.boilerId')"
pack_id="$(printf '%s' "$login" | jq -r '.onboarding.binding.materialPackId')"
pack_code="$(printf '%s' "$login" | jq -r '.onboarding.binding.packCode')"

step 3 "检查首页、锅炉和材料包"
dashboard="$(api_json GET /dashboard "$token")"
printf '%s' "$dashboard" | jq -e '.stats != null and .alerts != null' >/dev/null
boilers="$(api_json GET '/boilers?enterpriseId=1' "$token")"
printf '%s' "$boilers" | jq -e --argjson id "$boiler_id" 'any(.[]; .id == $id)' >/dev/null
pack="$(api_json POST /material-packs/verify "$token" "{\"code\":\"$pack_code\"}")"
printf '%s' "$pack" | jq -e --argjson id "$pack_id" '(.pack.id // .id) == $id' >/dev/null

step 4 "创建异常巡检并上传照片"
created="$(api_json POST /inspections "$token" \
  "{\"boilerId\":$boiler_id,\"materialPackId\":$pack_id,\"inspectionType\":\"daily\"}")"
inspection_id="$(printf '%s' "$created" | jq -r '.inspectionId')"
upload="$(curl -fsS -X POST "$API_BASE/inspections/upload-image" \
  -H "Authorization: Bearer $token" \
  -F "inspectionId=$inspection_id" \
  -F "file=@$PHOTO_FILE;type=image/png")"
printf '%s' "$upload" | jq -e '.success == true and .qualityStatus != "reject"' >/dev/null

step 5 "录入六项读数并生成异常诊断"
abnormal_values='{"ph":"9","phosphate":"10","sulfite":"20","alkalinity":"10","chloride":"100","hardness":"1"}'
recognized="$(api_json POST /inspections/recognize "$token" \
  "{\"inspectionId\":$inspection_id,\"values\":$abnormal_values}")"
printf '%s' "$recognized" | jq -e '
  .result.recognitionSource == "manual_gray" and
  (.result.items | length) == 6 and
  (.result.diagnosis | length) > 0 and
  any(.result.items[]; .code == "hardness" and .status == "warning")
' >/dev/null
submitted="$(api_json POST /inspections/submit "" \
  "{\"inspectionId\":$inspection_id,\"remark\":\"本地灰测自动验收：异常巡检\"}")"
printf '%s' "$submitted" | jq -e '.status == "submitted"' >/dev/null

step 6 "后台写入专业处理意见"
tasks="$(api_json GET '/retest-tasks?enterpriseId=1&status=pending' "$token")"
task_id="$(printf '%s' "$tasks" | jq -r --argjson inspection "$inspection_id" '
  [.[] | select(.inspectionId == $inspection)] | first | .id // empty
')"
if [ -z "$task_id" ]; then
  echo "FAIL: 异常巡检未生成复测任务"
  exit 1
fi
admin_login="$(api_json POST /auth/admin-login "" '{"username":"admin","password":"Admin@123"}')"
admin_token="$(printf '%s' "$admin_login" | jq -r '.token')"
advice="$(api_json POST "/retest-tasks/$task_id/service-advice" "$admin_token" \
  '{"serviceAdvice":"本地验收意见：检查软水器运行状态，按现场方案处理后复测。"}')"
printf '%s' "$advice" | jq -e '.serviceAdvice | length > 0' >/dev/null

step 7 "创建正常复测并回填原任务"
retest_created="$(api_json POST /inspections "$token" \
  "{\"boilerId\":$boiler_id,\"materialPackId\":$pack_id,\"inspectionType\":\"retest\",\"retestTaskId\":$task_id}")"
retest_id="$(printf '%s' "$retest_created" | jq -r '.inspectionId')"
retest_upload="$(curl -fsS -X POST "$API_BASE/inspections/upload-image" \
  -H "Authorization: Bearer $token" \
  -F "inspectionId=$retest_id" \
  -F "file=@$PHOTO_FILE;type=image/png")"
printf '%s' "$retest_upload" | jq -e '.success == true and .qualityStatus != "reject"' >/dev/null
normal_values='{"ph":"9","phosphate":"10","sulfite":"20","alkalinity":"10","chloride":"100","hardness":"0.01"}'
retest_result="$(api_json POST /inspections/recognize "$token" \
  "{\"inspectionId\":$retest_id,\"values\":$normal_values}")"
printf '%s' "$retest_result" | jq -e '
  (.result.items | length) == 6 and
  all(.result.items[]; .status == "normal")
' >/dev/null
api_json POST /inspections/submit "" \
  "{\"inspectionId\":$retest_id,\"remark\":\"本地灰测自动验收：正常复测\"}" >/dev/null
closed_tasks="$(api_json GET '/retest-tasks?enterpriseId=1&status=retested' "$token")"
printf '%s' "$closed_tasks" | jq -e --argjson task "$task_id" --argjson retest "$retest_id" '
  any(.[]; .id == $task and .retestInspectionId == $retest and .resolutionType == "retest")
' >/dev/null

step 8 "检查历史详情、样本和月报"
record="$(api_json GET "/records/$retest_id" "$token")"
printf '%s' "$record" | jq -e --argjson id "$retest_id" '
  (.id // .inspectionId) == $id and (.items | length) == 6
' >/dev/null
samples="$(api_json GET '/inspection-samples?labelStatus=pending' "$admin_token")"
printf '%s' "$samples" | jq -e --argjson id "$inspection_id" 'any(.[]; .inspectionId == $id)' >/dev/null
report="$(api_json GET "/reports/monthly?enterpriseId=1&month=$MONTH" "$token")"
printf '%s' "$report" | jq -e --arg month "$MONTH" '
  .month == $month and .inspectionCount >= 2 and (.suggestions | length) > 0
' >/dev/null
empty_report="$(api_json GET '/reports/monthly?enterpriseId=1&month=1900-01' "$token")"
printf '%s' "$empty_report" | jq -e '
  .month == "1900-01" and .inspectionCount == 0 and .score == 0 and (.suggestions | length) > 0
' >/dev/null

printf '\nPASS: 灰测闭环验收通过\n'
printf '异常巡检 ID: %s\n' "$inspection_id"
printf '复测任务 ID: %s\n' "$task_id"
printf '复测巡检 ID: %s\n' "$retest_id"
