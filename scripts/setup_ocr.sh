#!/usr/bin/env bash
# Project-local OCR runtime; no system package installation or sudo required.
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p .tools/ocr/packages .tools/ocr/tessdata .tools/fonts
(
  cd .tools/ocr/packages
  apt-get download tesseract-ocr=5.3.4-1build5 libtesseract5=5.3.4-1build5 liblept5 tesseract-ocr-eng tesseract-ocr-osd
  for package in *.deb; do dpkg-deb -x "$package" ../root; done
)
for model in jpn jpn_vert; do
  curl -fL "https://raw.githubusercontent.com/tesseract-ocr/tessdata_best/main/$model.traineddata" -o ".tools/ocr/tessdata/$model.traineddata"
done
cp .tools/ocr/root/usr/share/tesseract-ocr/5/tessdata/eng.traineddata .tools/ocr/tessdata/
cp -r .tools/ocr/root/usr/share/tesseract-ocr/5/tessdata/configs .tools/ocr/tessdata/
cp .tools/ocr/root/usr/share/tesseract-ocr/5/tessdata/pdf.ttf .tools/ocr/tessdata/
curl -fL https://raw.githubusercontent.com/google/fonts/main/ofl/bizudpgothic/BIZUDPGothic-Regular.ttf -o .tools/fonts/BIZUDPGothic-Regular.ttf
curl -fL https://raw.githubusercontent.com/google/fonts/main/ofl/bizudpgothic/OFL.txt -o .tools/fonts/OFL.txt
