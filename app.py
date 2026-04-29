import streamlit as st
import io
import os
import re
import tempfile
import time
from datetime import datetime
from pathlib import Path
from PIL import Image
from pypdf import PdfReader, PdfWriter
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Image as RLImage, Spacer, Paragraph, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER

# ─────────────────────────────────────────────
# 페이지 설정
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="협찬 증빙 자료 생성기",
    page_icon="📋",
    layout="centered"
)

st.markdown("""
<style>
    .main-title {
        font-size: 1.8rem;
        font-weight: 700;
        color: #1a1a2e;
        margin-bottom: 0.2rem;
    }
    .sub-title {
        font-size: 0.95rem;
        color: #666;
        margin-bottom: 2rem;
    }
    .section-box {
        background: #f8f9fb;
        border-left: 4px solid #4f8ef7;
        border-radius: 6px;
        padding: 1rem 1.2rem;
        margin-bottom: 1.2rem;
    }
    .section-label {
        font-weight: 600;
        font-size: 0.95rem;
        color: #1a1a2e;
        margin-bottom: 0.5rem;
    }
    .success-box {
        background: #e8f5e9;
        border-left: 4px solid #43a047;
        border-radius: 6px;
        padding: 0.8rem 1.2rem;
        color: #2e7d32;
        font-weight: 500;
    }
    .stButton>button {
        background-color: #4f8ef7;
        color: white;
        font-weight: 600;
        border: none;
        border-radius: 8px;
        padding: 0.6rem 2rem;
        width: 100%;
    }
    .stButton>button:hover {
        background-color: #2f6be0;
    }
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-title">📋 협찬 증빙 자료 생성기</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">이미지/PDF 파일을 업로드하거나 기사 링크를 입력하면 하나의 PDF로 합쳐드립니다.</div>', unsafe_allow_html=True)

# ─────────────────────────────────────────────
# 파일명 설정
# ─────────────────────────────────────────────
col1, col2 = st.columns(2)
with col1:
    year_month = st.text_input("📅 연도월", value=datetime.now().strftime("%Y%m"), placeholder="예: 202506")
with col2:
    media_name = st.text_input("📰 매체명", placeholder="예: 중앙일보")

st.divider()

# ─────────────────────────────────────────────
# 섹션 1: 기사 캡쳐
# ─────────────────────────────────────────────
st.markdown('<div class="section-label">① 웹 기사 캡쳐본</div>', unsafe_allow_html=True)

article_tab1, article_tab2 = st.tabs(["🖼️ 이미지 직접 업로드", "🔗 기사 URL로 자동 캡쳐"])

with article_tab1:
    article_files = st.file_uploader(
        "기사 캡쳐 이미지를 업로드하세요 (여러 장 가능)",
        type=["jpg", "jpeg", "png", "pdf"],
        accept_multiple_files=True,
        key="article_upload"
    )
    if article_files:
        st.success(f"✅ {len(article_files)}개 파일 업로드됨")

with article_tab2:
    article_url = st.text_input("기사 URL 입력", placeholder="https://news.example.com/article/12345")
    capture_btn = st.button("📸 기사 캡쳐하기", key="capture_btn")

    url_screenshot_bytes = None

    if capture_btn and article_url:
        try:
            from playwright.sync_api import sync_playwright
            with st.spinner("기사 페이지 캡쳐 중..."):
                with sync_playwright() as p:
                    browser = p.chromium.launch(
                        headless=True,
                        args=["--no-sandbox", "--disable-setuid-sandbox",
                              "--disable-dev-shm-usage", "--disable-gpu"]
                    )
                    page = browser.new_page(viewport={"width": 1280, "height": 900})
                    page.goto(article_url, wait_until="networkidle", timeout=30000)
                    time.sleep(2)

                    # 전체 페이지 스크롤 후 캡쳐
                    page.evaluate("window.scrollTo(0, 0)")
                    screenshot_bytes = page.screenshot(full_page=True)
                    browser.close()

                    url_screenshot_bytes = screenshot_bytes
                    st.session_state["url_screenshot"] = screenshot_bytes

            img_preview = Image.open(io.BytesIO(url_screenshot_bytes))
            st.image(img_preview, caption="캡쳐된 기사 화면", use_container_width=True)
            st.success("✅ 기사 캡쳐 완료!")

        except ImportError:
            st.error("playwright가 설치되어 있지 않습니다.\n`pip install playwright && playwright install chromium`")
        except Exception as e:
            st.error(f"캡쳐 실패: {e}\n\n이미지 직접 업로드를 이용해주세요.")

    elif "url_screenshot" in st.session_state:
        url_screenshot_bytes = st.session_state["url_screenshot"]
        img_preview = Image.open(io.BytesIO(url_screenshot_bytes))
        st.image(img_preview, caption="캡쳐된 기사 화면", use_container_width=True)

st.divider()

# ─────────────────────────────────────────────
# 섹션 2: 계산서
# ─────────────────────────────────────────────
st.markdown('<div class="section-label">② 발행된 계산서 캡쳐본</div>', unsafe_allow_html=True)
invoice_files = st.file_uploader(
    "계산서 이미지/PDF를 업로드하세요",
    type=["jpg", "jpeg", "png", "pdf"],
    accept_multiple_files=True,
    key="invoice_upload"
)
if invoice_files:
    st.success(f"✅ {len(invoice_files)}개 파일 업로드됨")

st.divider()

# ─────────────────────────────────────────────
# 섹션 3: 사업자 등록증
# ─────────────────────────────────────────────
st.markdown('<div class="section-label">③ 사업자 등록증</div>', unsafe_allow_html=True)
biz_files = st.file_uploader(
    "사업자 등록증 이미지/PDF를 업로드하세요",
    type=["jpg", "jpeg", "png", "pdf"],
    accept_multiple_files=True,
    key="biz_upload"
)
if biz_files:
    st.success(f"✅ {len(biz_files)}개 파일 업로드됨")

st.divider()

# ─────────────────────────────────────────────
# 섹션 4: 통장 사본
# ─────────────────────────────────────────────
st.markdown('<div class="section-label">④ 통장 사본</div>', unsafe_allow_html=True)
bank_files = st.file_uploader(
    "통장 사본 이미지/PDF를 업로드하세요",
    type=["jpg", "jpeg", "png", "pdf"],
    accept_multiple_files=True,
    key="bank_upload"
)
if bank_files:
    st.success(f"✅ {len(bank_files)}개 파일 업로드됨")

st.divider()

# ─────────────────────────────────────────────
# 헬퍼 함수
# ─────────────────────────────────────────────
def file_to_pil_images(uploaded_file) -> list[Image.Image]:
    """업로드 파일(이미지/PDF)을 PIL Image 리스트로 변환"""
    file_bytes = uploaded_file.read()
    name_lower = uploaded_file.name.lower()

    if name_lower.endswith(".pdf"):
        from pdf2image import convert_from_bytes
        images = convert_from_bytes(file_bytes, dpi=150)
        return images
    else:
        img = Image.open(io.BytesIO(file_bytes)).convert("RGB")
        return [img]


def pil_to_reportlab_image(pil_img: Image.Image, max_width: float, max_height: float):
    """PIL Image → ReportLab Image (비율 유지)"""
    buf = io.BytesIO()
    pil_img.save(buf, format="JPEG", quality=90)
    buf.seek(0)

    w, h = pil_img.size
    ratio = min(max_width / w, max_height / h)
    draw_w = w * ratio
    draw_h = h * ratio

    return RLImage(buf, width=draw_w, height=draw_h)


def build_section_label(text: str, styles) -> Paragraph:
    label_style = ParagraphStyle(
        name="SectionLabel",
        parent=styles["Normal"],
        fontSize=13,
        fontName="Helvetica-Bold",
        textColor=colors.HexColor("#1a1a2e"),
        spaceAfter=6,
        spaceBefore=4,
        borderPad=6,
        backColor=colors.HexColor("#e8edf8"),
        borderColor=colors.HexColor("#4f8ef7"),
        borderWidth=0,
        leftIndent=0,
    )
    return Paragraph(text, label_style)


def generate_pdf(sections: dict, filename: str) -> bytes:
    """
    sections: {"label": [PIL Images], ...}  순서 있는 dict
    """
    buf = io.BytesIO()
    page_w, page_h = A4
    margin = 15 * mm
    usable_w = page_w - 2 * margin
    usable_h = page_h - 2 * margin - 30 * mm  # 레이블 공간 확보

    styles = getSampleStyleSheet()

    story = []
    first_section = True

    for section_label, pil_images in sections.items():
        if not pil_images:
            continue

        if not first_section:
            story.append(PageBreak())
        first_section = False

        story.append(build_section_label(section_label, styles))
        story.append(Spacer(1, 4 * mm))

        for pil_img in pil_images:
            rl_img = pil_to_reportlab_image(pil_img, usable_w, usable_h)
            story.append(rl_img)
            story.append(Spacer(1, 4 * mm))

    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=margin,
        rightMargin=margin,
        topMargin=margin,
        bottomMargin=margin,
        title=filename,
    )
    doc.build(story)
    buf.seek(0)
    return buf.read()


# ─────────────────────────────────────────────
# PDF 생성 버튼
# ─────────────────────────────────────────────
st.markdown("### 📥 PDF 생성")

if not year_month or not media_name:
    st.info("연도월과 매체명을 입력하면 PDF를 생성할 수 있습니다.")
else:
    filename = f"{year_month}_{media_name}_협찬증빙"

    generate_btn = st.button(f"📄 '{filename}.pdf' 생성하기")

    if generate_btn:
        # 기사 이미지 수집
        article_images: list[Image.Image] = []

        # URL 캡쳐 우선
        if "url_screenshot" in st.session_state and st.session_state["url_screenshot"]:
            img = Image.open(io.BytesIO(st.session_state["url_screenshot"])).convert("RGB")
            article_images.append(img)

        # 직접 업로드
        if article_files:
            for f in article_files:
                f.seek(0)
                article_images.extend(file_to_pil_images(f))

        invoice_images: list[Image.Image] = []
        if invoice_files:
            for f in invoice_files:
                f.seek(0)
                invoice_images.extend(file_to_pil_images(f))

        biz_images: list[Image.Image] = []
        if biz_files:
            for f in biz_files:
                f.seek(0)
                biz_images.extend(file_to_pil_images(f))

        bank_images: list[Image.Image] = []
        if bank_files:
            for f in bank_files:
                f.seek(0)
                bank_images.extend(file_to_pil_images(f))

        if not any([article_images, invoice_images, biz_images, bank_images]):
            st.warning("⚠️ 업로드된 파일이 없습니다. 최소 하나의 파일을 업로드해주세요.")
        else:
            with st.spinner("PDF를 생성하는 중..."):
                sections = {}
                if article_images:
                    sections[f"① 웹 기사 캡쳐본 ({media_name})"] = article_images
                if invoice_images:
                    sections["② 발행된 계산서"] = invoice_images
                if biz_images:
                    sections["③ 사업자 등록증"] = biz_images
                if bank_images:
                    sections["④ 통장 사본"] = bank_images

                try:
                    pdf_bytes = generate_pdf(sections, filename)
                    total = sum(len(v) for v in sections.values())

                    st.markdown(
                        f'<div class="success-box">✅ PDF 생성 완료 — 총 {total}장, {len(sections)}개 섹션</div>',
                        unsafe_allow_html=True
                    )
                    st.download_button(
                        label=f"⬇️ {filename}.pdf 다운로드",
                        data=pdf_bytes,
                        file_name=f"{filename}.pdf",
                        mime="application/pdf",
                        use_container_width=True,
                    )
                except Exception as e:
                    st.error(f"PDF 생성 중 오류: {e}")
