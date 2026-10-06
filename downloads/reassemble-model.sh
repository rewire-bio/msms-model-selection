#!/bin/sh
# Reassemble and verify the trained DreaMS + Morgan model bundle for the
# msms-shortlist companion (rewire.it, "An MS/MS Shortlist Is Not an Identification").
#
# The 45,138,751-byte archive is published as three byte-for-byte parts
# (the hosting limit is 25 MiB per file). This script:
#   1. optionally downloads the three parts from BASE_URL,
#   2. checks each part's SHA-256,
#   3. joins them in order (part01, part02, part03),
#   4. checks the joined file against the original archive's SHA-256,
#   5. extracts it, giving msms-shortlist-model/.
#
# Usage:
#   sh reassemble-model.sh                 # parts already in the current directory
#   BASE_URL=https://example.org/path sh reassemble-model.sh   # download first
#
# Equivalent manual recipe:
#   cat msms-shortlist-dreams-morgan-model.tar.gz.part01 \
#       msms-shortlist-dreams-morgan-model.tar.gz.part02 \
#       msms-shortlist-dreams-morgan-model.tar.gz.part03 > msms-shortlist-dreams-morgan-model.tar.gz
#   shasum -a 256 msms-shortlist-dreams-morgan-model.tar.gz   # or: sha256sum
#   # expect 646bbe4fbb14bda60e3544d4a963c9319b6564663c9b0752cd5e92b879eeffc9
#   tar -xzf msms-shortlist-dreams-morgan-model.tar.gz
set -eu

NAME=msms-shortlist-dreams-morgan-model.tar.gz
ORIGINAL_SHA256=646bbe4fbb14bda60e3544d4a963c9319b6564663c9b0752cd5e92b879eeffc9
ORIGINAL_BYTES=45138751
PARTS="part01 part02 part03"
SHA_part01=fdd6e193c88fc260e8143c5096781a0cefef33a5824f0a2115054fc8d3c4552c
SHA_part02=b5bb749392ac86ea68fd022d303ebb2bccaba2518e5812644835c3e7b50148da
SHA_part03=0bd59d5db3ea054db41bc4284a0a083f3d718aa7eace506f2ba79a661431cf70

sha256() {
  if command -v sha256sum >/dev/null 2>&1; then sha256sum "$1" | cut -d' ' -f1
  else shasum -a 256 "$1" | cut -d' ' -f1; fi
}

if [ -n "${BASE_URL:-}" ]; then
  for p in $PARTS; do
    echo "downloading $NAME.$p"
    curl -fL --retry 3 -o "$NAME.$p" "$BASE_URL/$NAME.$p"
  done
fi

for p in $PARTS; do
  [ -f "$NAME.$p" ] || { echo "missing $NAME.$p" >&2; exit 1; }
  eval expected=\$SHA_$p
  got=$(sha256 "$NAME.$p")
  [ "$got" = "$expected" ] || { echo "SHA-256 mismatch for $NAME.$p: $got" >&2; exit 1; }
  echo "ok  $NAME.$p"
done

tmp="$NAME.tmp.$$"
trap 'rm -f "$tmp"' EXIT INT TERM
cat "$NAME.part01" "$NAME.part02" "$NAME.part03" > "$tmp"
got=$(sha256 "$tmp")
if [ "$got" != "$ORIGINAL_SHA256" ]; then
  echo "joined file SHA-256 $got does not match $ORIGINAL_SHA256" >&2
  exit 1
fi
mv "$tmp" "$NAME"
echo "ok  $NAME ($ORIGINAL_BYTES bytes, SHA-256 $ORIGINAL_SHA256)"

tar -xzf "$NAME"
echo "extracted msms-shortlist-model/ (dreams_morgan_formula_seed1_fp16.pt, thresholds.json, export-receipt.json)"
echo "copy dreams_morgan_formula_seed1_fp16.pt and thresholds.json into the companion's models/ directory to use --model"
