#!/bin/bash
# 협찬 증빙 자료 생성기 — 초기 설치 스크립트

echo "=== 패키지 설치 중 ==="
pip install -r requirements.txt

echo ""
echo "=== Playwright Chromium 브라우저 설치 중 ==="
python -m playwright install chromium

echo ""
echo "=== poppler 설치 (PDF 처리용) ==="
if [[ "$OSTYPE" == "darwin"* ]]; then
    brew install poppler
elif command -v apt-get &> /dev/null; then
    sudo apt-get install -y poppler-utils
fi

echo ""
echo "✅ 설치 완료! 아래 명령어로 앱을 시작하세요:"
echo "   streamlit run app.py"
