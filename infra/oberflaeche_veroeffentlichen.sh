#!/usr/bin/env bash
# Veröffentlicht die Oberfläche nach S3/CloudFront und schreibt konfiguration.js
# mit den Stack-Ausgaben. Aufruf: infra/oberflaeche_veroeffentlichen.sh <stack-name> [region]
set -euo pipefail
STACK="${1:?Stack-Name fehlt}"
REGION="${2:-eu-central-1}"
HIER="$(cd "$(dirname "$0")" && pwd)"
STATISCH="$HIER/../jusperfect/static"

ausgabe() { aws cloudformation describe-stacks --region "$REGION" --stack-name "$STACK" \
  --query "Stacks[0].Outputs[?OutputKey=='$1'].OutputValue" --output text; }

BUCKET="$(ausgabe OberflaecheBucket)"
API="$(ausgabe ApiUrl)"
COGNITO="$(ausgabe CognitoDomaene)"
CLIENT="$(ausgabe CognitoClientId)"
URL="$(ausgabe OberflaecheUrl)"

ZIEL="$(mktemp -d)"
cp "$STATISCH"/index.html "$STATISCH"/app.js "$STATISCH"/styles.css "$ZIEL"/
# Die Oberfläche liegt in S3 unter /, nicht unter /static/.
sed -i 's#/static/#/#g' "$ZIEL/index.html"
cat > "$ZIEL/konfiguration.js" <<JS
window.JUSPERFECT_KONFIGURATION = {
  betriebsart: "aws",
  apiBasis: "$API",
  cognitoDomaene: "$COGNITO",
  clientId: "$CLIENT"
};
JS
aws s3 sync "$ZIEL" "s3://$BUCKET/" --region "$REGION" --delete --cache-control "no-cache"
rm -rf "$ZIEL"
echo "Oberfläche veröffentlicht: $URL"
echo "Hinweis: Beim ersten Deploy den Parameter OberflaecheUrl auf $URL setzen und erneut deployen (Cognito-Callback, CORS)."
