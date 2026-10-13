#!/bin/bash
# Sign Cubegen.app with a Developer ID, notarise it at Apple and staple the ticket - for passing the app on (the
# normal build is signed ad hoc and runs on this Mac only). Run it yourself: it needs your Apple developer account.
#
#   app/notarize.sh [app]          default: ../output/app/Cubegen.app (app/build.sh first)
#
# Needs, once:
#   1. A "Developer ID Application" certificate in the keychain (Apple Developer Program; an "Apple Development"
#      certificate is not enough): `security find-identity -v -p codesigning` lists it.
#   2. A notarytool profile with your credentials, stored in the keychain:
#        xcrun notarytool store-credentials cubegen-notary --apple-id <id> --team-id <team>
#      (asks for an app-specific password; the password stays in the keychain, never in this script)
# Settings (environment):
#   CUBEGEN_SIGN_IDENTITY   the certificate's name (default: the first "Developer ID Application" found)
#   CUBEGEN_NOTARY_PROFILE  the notarytool profile (default: cubegen-notary)
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
APP="${1:-$HERE/../output/app/Cubegen.app}"
PROFILE="${CUBEGEN_NOTARY_PROFILE:-cubegen-notary}"
[ -d "$APP" ] || { echo "no app at $APP - run app/build.sh first"; exit 2; }

IDENTITY="${CUBEGEN_SIGN_IDENTITY:-$(security find-identity -v -p codesigning \
  | sed -n 's/.*"\(Developer ID Application: [^"]*\)".*/\1/p' | head -1)}"
if [ -z "$IDENTITY" ]; then
  echo "no 'Developer ID Application' certificate in the keychain (an 'Apple Development' one cannot notarise)."
  echo "See the comment at the top of $0."
  exit 2
fi

echo "> signing with: $IDENTITY (hardened runtime, timestamp)"
# inside out: the bundled Python package has no binaries; the app's executable gets the hardened runtime
codesign --force --deep --options runtime --timestamp --sign "$IDENTITY" "$APP"
codesign --verify --strict --verbose=2 "$APP"

ZIP="$(mktemp -d)/Cubegen.zip"
ditto -c -k --keepParent "$APP" "$ZIP"
echo "> notarising (profile $PROFILE) - this takes a few minutes"
xcrun notarytool submit "$ZIP" --keychain-profile "$PROFILE" --wait
echo "> stapling the ticket"
xcrun stapler staple "$APP"
spctl --assess --type execute --verbose=2 "$APP"
echo "> done: $APP is notarised"
