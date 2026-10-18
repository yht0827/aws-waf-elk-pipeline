#!/usr/bin/env bash
TARGET_URL="${1:-http://localhost}"

echo "========================================================"
echo "🛡️ AWS WAF Security Verification & Log Generation Script"
echo "Target: ${TARGET_URL}"
echo "========================================================"

run_test() {
    local tc_id="$1"
    local desc="$2"
    local cmd="$3"
    local expected="$4"

    HTTP_CODE=$(eval "$cmd" -o /dev/null -s -w "%{http_code}")
    if [ "$HTTP_CODE" == "$expected" ]; then
        echo "✅ [${tc_id}] ${desc} -> HTTP ${HTTP_CODE} (Expected: ${expected}) [PASS]"
    else
        echo "❌ [${tc_id}] ${desc} -> HTTP ${HTTP_CODE} (Expected: ${expected}) [CHECK]"
    fi
}

run_test "TC-01" "Normal User Request" \
    "curl -A 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)' '${TARGET_URL}/?page=home'" "200"

run_test "TC-02a" "SQLi Auth Bypass" \
    "curl '${TARGET_URL}/login?user=admin%27%20OR%20%271%27%3D%271--'" "403"

run_test "TC-02b" "SQLi UNION Extraction" \
    "curl '${TARGET_URL}/items?id=1%20UNION%20SELECT%20null,username,password%20FROM%20users--'" "403"

run_test "TC-03" "Reflected XSS Payload" \
    "curl '${TARGET_URL}/search?q=%3Cscript%3Ealert%28document.cookie%29%3C%2Fscript%3E'" "403"

run_test "TC-04" "Path Traversal (/etc/passwd)" \
    "curl '${TARGET_URL}/view?file=..%2F..%2F..%2F..%2Fetc%2Fpasswd'" "403"

run_test "TC-05a" "Scanner UA (sqlmap)" \
    "curl -A 'sqlmap/1.7.2#stable (https://sqlmap.org)' '${TARGET_URL}/'" "403"

run_test "TC-05b" "Scanner UA (Nikto)" \
    "curl -A 'Mozilla/5.00 (Nikto/2.1.6)' '${TARGET_URL}/'" "403"

echo "--------------------------------------------------------"
echo "📊 Generating bulk attack logs for ELK Dashboard..."
for i in {1..15}; do
    curl -s -o /dev/null "${TARGET_URL}/login?id=1%27%20OR%201%3D1--"
    curl -s -o /dev/null "${TARGET_URL}/search?q=%3Cscript%3Ealert(1)%3C/script%3E"
    curl -s -o /dev/null -A "sqlmap/1.7" "${TARGET_URL}/admin"
done
echo "✅ Done! Logs generated."
