# 협찬 증빙 자료 생성기

## 📦 설치 방법

```bash
# 1. 패키지 설치
pip install -r requirements.txt

# 2. Playwright 브라우저 설치 (URL 자동 캡쳐 기능 사용 시)
playwright install chromium

# 3. pdf2image 의존성 (macOS)
brew install poppler

# 3. pdf2image 의존성 (Ubuntu/Debian)
# sudo apt-get install poppler-utils

# 4. 앱 실행
streamlit run app.py
```

## 🖥️ 사용 방법

1. **연도월** (예: `202506`) 과 **매체명** (예: `중앙일보`) 입력
2. 4개 섹션에 파일 업로드:
   - ① 기사 캡쳐 — 이미지 직접 업로드 또는 URL 입력 후 자동 캡쳐
   - ② 계산서 캡쳐본
   - ③ 사업자 등록증
   - ④ 통장 사본
3. **PDF 생성하기** 버튼 클릭
4. 생성된 `연도월_매체명_협찬증빙.pdf` 다운로드

## 📌 지원 파일 형식
- 이미지: JPG, JPEG, PNG
- 문서: PDF (각 페이지가 자동으로 이미지로 변환됨)
- 여러 장 동시 업로드 가능

## 🔗 URL 자동 캡쳐
- playwright 설치 필요
- 전체 페이지 스크롤 캡쳐 지원
- 캡쳐 실패 시 이미지 직접 업로드 사용
