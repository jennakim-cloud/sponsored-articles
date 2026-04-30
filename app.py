import streamlit as st
import io
import os
import subprocess
import tempfile
import glob
import time
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont
from pypdf import PdfReader
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Image as RLImage, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus.flowables import HRFlowable
from reportlab.lib import colors

# ─────────────────────────────────────────────
# 페이지 설정
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="증빙 자료 생성기",
    page_icon="📋",
    layout="centered"
)

st.markdown("""
<style>
    .main-title {
        font-size: 1.8rem; font-weight: 700;
        color: #1a1a2e; margin-bottom: 0.2rem;
    }
    .sub-title {
        font-size: 0.95rem; color: #666; margin-bottom: 1.5rem;
    }
    .section-label {
        font-weight: 600; font-size: 0.95rem;
        color: #1a1a2e; margin-bottom: 0.5rem;
    }
    .success-box {
        background: #e8f5e9; border-left: 4px solid #43a047;
        border-radius: 6px; padding: 0.8rem 1.2rem;
        color: #2e7d32; font-weight: 500;
    }
    .stButton>button {
        background-color: #4f8ef7; color: white;
        font-weight: 600; border: none;
        border-radius: 8px; padding: 0.6rem 2rem; width: 100%;
    }
    .stButton>button:hover { background-color: #2f6be0; }
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-title">📋 증빙 자료 생성기</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">파일을 업로드하면 하나의 PDF로 합쳐드립니다.</div>', unsafe_allow_html=True)

# ─────────────────────────────────────────────
# 공통 헬퍼 함수
# ─────────────────────────────────────────────
def pdf_bytes_to_pil_images(file_bytes: bytes) -> list[Image.Image]:
    result: list[Image.Image] = []
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            pdf_path = os.path.join(tmpdir, "input.pdf")
            out_prefix = os.path.join(tmpdir, "page")
            with open(pdf_path, "wb") as f:
                f.write(file_bytes)
            proc = subprocess.run(
                ["pdftoppm", "-r", "150", "-png", pdf_path, out_prefix],
                capture_output=True, timeout=60
            )
            if proc.returncode == 0:
                for png_path in sorted(glob.glob(f"{out_prefix}*.png")):
                    img = Image.open(png_path).convert("RGB")
                    result.append(img.copy())
        if result:
            return result
    except Exception:
        pass

    try:
        reader = PdfReader(io.BytesIO(file_bytes))
        for page in reader.pages:
            for img_obj in page.images:
                try:
                    pil_img = Image.open(io.BytesIO(img_obj.data)).convert("RGB")
                    result.append(pil_img)
                except Exception:
                    continue
        if result:
            return result
    except Exception:
        pass

    return result


def file_to_pil_images(uploaded_file) -> list[Image.Image]:
    file_bytes = uploaded_file.read()
    name_lower = uploaded_file.name.lower()
    if name_lower.endswith(".pdf"):
        images = pdf_bytes_to_pil_images(file_bytes)
        if images:
            return images
        img = Image.new("RGB", (1240, 1754), "white")
        ImageDraw.Draw(img).text((60, 80), "PDF 변환 실패 — 이미지로 변환 후 업로드해 주세요.", fill=(200, 0, 0))
        return [img]
    else:
        return [Image.open(io.BytesIO(file_bytes)).convert("RGB")]


def _find_korean_font_path() -> str | None:
    candidates = [
        "/usr/share/fonts/truetype/nanum/NanumGothic.ttf",
        "/usr/share/fonts/truetype/nanum/NanumBarunGothic.ttf",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/fonts-japanese-gothic.ttf",
        "/System/Library/Fonts/AppleSDGothicNeo.ttc",
        "C:/Windows/Fonts/malgun.ttf",
    ]
    for path in candidates:
        try:
            font = ImageFont.truetype(path, 20)
            test_img = Image.new("RGB", (200, 40), "white")
            ImageDraw.Draw(test_img).text((0, 0), "한글테스트", font=font, fill="black")
            if any(p != (255, 255, 255) for p in test_img.getdata()):
                return path
        except Exception:
            continue
    return None

_KOREAN_FONT_PATH = _find_korean_font_path()
_LABEL_FONT_SIZE  = 36
_LABEL_PADDING    = 18


def build_section_label(text: str) -> RLImage:
    """섹션 라벨을 PIL 이미지로 그려 ReportLab Flowable로 반환"""
    usable_w_pt = A4[0] - 2 * 15 * mm
    dpi_scale   = 150 / 72
    img_w_px    = int(usable_w_pt * dpi_scale)
    img_h_px    = _LABEL_FONT_SIZE + _LABEL_PADDING * 2

    img = Image.new("RGB", (img_w_px, img_h_px), (232, 237, 248))
    draw = ImageDraw.Draw(img)
    draw.rectangle([0, 0, 7, img_h_px], fill=(79, 142, 247))
    try:
        font = ImageFont.truetype(_KOREAN_FONT_PATH, _LABEL_FONT_SIZE) if _KOREAN_FONT_PATH else ImageFont.load_default()
    except Exception:
        font = ImageFont.load_default()
    draw.text((_LABEL_PADDING + 10, _LABEL_PADDING // 2), text, fill=(26, 26, 46), font=font)

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return RLImage(buf, width=usable_w_pt, height=img_h_px * (usable_w_pt / img_w_px))


def pil_to_reportlab_image(pil_img: Image.Image, max_width: float, max_height: float) -> RLImage:
    buf = io.BytesIO()
    pil_img.save(buf, format="JPEG", quality=90)
    buf.seek(0)
    w, h = pil_img.size
    ratio = min(max_width / w, max_height / h)
    return RLImage(buf, width=w * ratio, height=h * ratio)


def generate_pdf(sections: list[dict], filename: str) -> bytes:
    """
    sections: [{"label": str, "images": [PIL], "link": str|None}, ...]
    link があれば ラベル直下に ハイパーリンク付きテキストを挿入
    """
    from reportlab.platypus import Paragraph
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.enums import TA_LEFT

    buf = io.BytesIO()
    margin = 15 * mm
    usable_w = A4[0] - 2 * margin
    usable_h = A4[1] - 2 * margin - 35 * mm

    link_style = ParagraphStyle(
        name="LinkStyle",
        fontSize=9,
        textColor=colors.HexColor("#1a56db"),
        spaceAfter=4,
        leading=13,
    )

    story = []
    first = True

    for sec in sections:
        if not sec.get("images"):
            continue
        if not first:
            story.append(PageBreak())
        first = False

        story.append(build_section_label(sec["label"]))
        story.append(Spacer(1, 3 * mm))

        # 하이퍼링크 (기사 링크가 있을 때만)
        link = sec.get("link", "").strip()
        if link:
            if not link.startswith("http"):
                link = "https://" + link
            story.append(Paragraph(
                f'<link href="{link}" color="#1a56db">{link}</link>',
                link_style
            ))
            story.append(Spacer(1, 2 * mm))

        for pil_img in sec["images"]:
            story.append(pil_to_reportlab_image(pil_img, usable_w, usable_h))
            story.append(Spacer(1, 4 * mm))

    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=margin, rightMargin=margin,
        topMargin=margin, bottomMargin=margin,
        title=filename,
    )
    doc.build(story)
    buf.seek(0)
    return buf.read()


def collect_files(file_list) -> list[Image.Image]:
    images = []
    for f in (file_list or []):
        f.seek(0)
        images.extend(file_to_pil_images(f))
    return images


def capture_via_screenshotone(url: str, api_key: str) -> bytes:
    import requests as req
    params = {
        "access_key": api_key, "url": url,
        "full_page": "true", "viewport_width": "1280",
        "viewport_height": "900", "format": "png",
        "block_ads": "true", "block_cookie_banners": "true",
        "delay": "2", "timeout": "30",
    }
    resp = req.get("https://api.screenshotone.com/take", params=params, timeout=60)
    if resp.status_code != 200:
        raise RuntimeError(f"API 오류 {resp.status_code}: {resp.text[:200]}")
    return resp.content


# ─────────────────────────────────────────────
# 공통 파일명 설정
# ─────────────────────────────────────────────
col1, col2 = st.columns(2)
with col1:
    year_month = st.text_input("📅 연도월", value=datetime.now().strftime("%Y%m"), placeholder="예: 202506")
with col2:
    media_name = st.text_input("📰 매체명", placeholder="예: 중앙일보")

st.divider()

# ─────────────────────────────────────────────
# 2개 탭
# ─────────────────────────────────────────────
tab1, tab2 = st.tabs(["📰 협찬 기사 증빙", "📱 뉴미디어 협업 증빙"])


# ══════════════════════════════════════════════
# TAB 1 — 협찬 기사 증빙
# 순서: ① 공문  ② 게재 기사  ③ 계산서
# ══════════════════════════════════════════════
with tab1:

    # ① 공문
    st.markdown('<div class="section-label">① 공문</div>', unsafe_allow_html=True)
    official_files = st.file_uploader(
        "공문 이미지/PDF를 업로드하세요",
        type=["jpg", "jpeg", "png", "pdf"],
        accept_multiple_files=True,
        key="t1_official"
    )
    if official_files:
        st.success(f"✅ {len(official_files)}개 파일 업로드됨")

    st.divider()

    # ② 게재 기사
    st.markdown('<div class="section-label">② 게재 기사</div>', unsafe_allow_html=True)

    t1_col1, t1_col2 = st.columns(2)
    with t1_col1:
        t1_article_date = st.text_input("📅 게재 날짜", placeholder="예: 2025년 06월 15일", key="t1_date")
    with t1_col2:
        t1_article_link = st.text_input("🔗 기사 링크 (PDF에 하이퍼링크로 삽입)", placeholder="https://...", key="t1_link")

    t1_atab1, t1_atab2 = st.tabs(["🖼️ 이미지 직접 업로드", "🔗 URL 자동 캡쳐"])

    with t1_atab1:
        t1_article_files = st.file_uploader(
            "기사 캡쳐 이미지를 업로드하세요 (여러 장 가능)",
            type=["jpg", "jpeg", "png", "pdf"],
            accept_multiple_files=True,
            key="t1_article_upload"
        )
        if t1_article_files:
            st.success(f"✅ {len(t1_article_files)}개 파일 업로드됨")

    with t1_atab2:
        t1_article_url = st.text_input("기사 URL 입력", placeholder="https://...", key="t1_url_input")
        t1_capture_btn = st.button("📸 기사 캡쳐하기", key="t1_capture_btn")

        api_key = st.secrets.get("SCREENSHOTONE_KEY", "") if hasattr(st, "secrets") else ""
        if not api_key:
            api_key = st.text_input("🔑 ScreenshotOne API Key", type="password",
                                    placeholder="screenshotone.com 무료 가입 후 발급",
                                    key="t1_api_key")

        if t1_capture_btn and t1_article_url:
            if not api_key:
                st.warning("⚠️ API 키를 입력해주세요.")
            else:
                try:
                    with st.spinner("📸 캡쳐 중..."):
                        shot = capture_via_screenshotone(t1_article_url, api_key)
                    st.session_state["t1_url_screenshot"] = shot
                    st.image(Image.open(io.BytesIO(shot)), caption="캡쳐된 기사 화면", use_container_width=True)
                    st.success("✅ 캡쳐 완료!")
                except Exception as e:
                    st.error(f"캡쳐 실패: {e}")

        elif "t1_url_screenshot" in st.session_state:
            st.image(Image.open(io.BytesIO(st.session_state["t1_url_screenshot"])),
                     caption="캡쳐된 기사 화면", use_container_width=True)

    st.divider()

    # ③ 계산서
    st.markdown('<div class="section-label">③ 계산서</div>', unsafe_allow_html=True)
    t1_invoice_files = st.file_uploader(
        "계산서 이미지/PDF를 업로드하세요",
        type=["jpg", "jpeg", "png", "pdf"],
        accept_multiple_files=True,
        key="t1_invoice"
    )
    if t1_invoice_files:
        st.success(f"✅ {len(t1_invoice_files)}개 파일 업로드됨")

    st.divider()

    # PDF 생성
    st.markdown("### 📥 PDF 생성")
    if not year_month or not media_name:
        st.info("상단에서 연도월과 매체명을 입력해주세요.")
    else:
        filename1 = f"{year_month}_{media_name}_협찬기사증빙"
        if st.button(f"📄 '{filename1}.pdf' 생성하기", key="t1_gen"):

            # 기사 이미지 수집
            t1_article_images: list[Image.Image] = []
            if "t1_url_screenshot" in st.session_state and st.session_state["t1_url_screenshot"]:
                t1_article_images.append(
                    Image.open(io.BytesIO(st.session_state["t1_url_screenshot"])).convert("RGB")
                )
            t1_article_images.extend(collect_files(t1_article_files))

            date_str = t1_article_date.strip() if t1_article_date.strip() else "날짜 미입력"
            article_label = f"② 게재 기사 ({media_name}, {date_str})"

            sections = [
                {"label": "① 공문",         "images": collect_files(official_files),  "link": ""},
                {"label": article_label,      "images": t1_article_images,              "link": t1_article_link},
                {"label": "③ 계산서",        "images": collect_files(t1_invoice_files), "link": ""},
            ]
            sections = [s for s in sections if s["images"]]

            if not sections:
                st.warning("⚠️ 업로드된 파일이 없습니다.")
            else:
                with st.spinner("PDF 생성 중..."):
                    try:
                        pdf_bytes = generate_pdf(sections, filename1)
                        total = sum(len(s["images"]) for s in sections)
                        st.markdown(
                            f'<div class="success-box">✅ PDF 생성 완료 — 총 {total}장, {len(sections)}개 섹션</div>',
                            unsafe_allow_html=True
                        )
                        st.download_button(
                            label=f"⬇️ {filename1}.pdf 다운로드",
                            data=pdf_bytes,
                            file_name=f"{filename1}.pdf",
                            mime="application/pdf",
                            use_container_width=True,
                        )
                    except Exception as e:
                        st.error(f"PDF 생성 중 오류: {e}")


# ══════════════════════════════════════════════
# TAB 2 — 뉴미디어 협업 증빙
# 순서: ① 게재 결과  ② 계산서  ③ 사업자등록증  ④ 통장사본
# ══════════════════════════════════════════════
with tab2:

    # ① 게재 결과
    st.markdown('<div class="section-label">① 게재 결과</div>', unsafe_allow_html=True)

    t2_col1, t2_col2 = st.columns(2)
    with t2_col1:
        t2_article_date = st.text_input("📅 게재 날짜", placeholder="예: 2025년 06월 15일", key="t2_date")
    with t2_col2:
        t2_article_link = st.text_input("🔗 게시물 링크 (PDF에 하이퍼링크로 삽입)", placeholder="https://...", key="t2_link")

    t2_atab1, t2_atab2 = st.tabs(["🖼️ 이미지 직접 업로드", "🔗 URL 자동 캡쳐"])

    with t2_atab1:
        t2_article_files = st.file_uploader(
            "게재 결과 이미지를 업로드하세요 (여러 장 가능)",
            type=["jpg", "jpeg", "png", "pdf"],
            accept_multiple_files=True,
            key="t2_article_upload"
        )
        if t2_article_files:
            st.success(f"✅ {len(t2_article_files)}개 파일 업로드됨")

    with t2_atab2:
        t2_article_url = st.text_input("URL 입력", placeholder="https://...", key="t2_url_input")
        t2_capture_btn = st.button("📸 캡쳐하기", key="t2_capture_btn")

        api_key2 = st.secrets.get("SCREENSHOTONE_KEY", "") if hasattr(st, "secrets") else ""
        if not api_key2:
            api_key2 = st.text_input("🔑 ScreenshotOne API Key", type="password",
                                     placeholder="screenshotone.com 무료 가입 후 발급",
                                     key="t2_api_key")

        if t2_capture_btn and t2_article_url:
            if not api_key2:
                st.warning("⚠️ API 키를 입력해주세요.")
            else:
                try:
                    with st.spinner("📸 캡쳐 중..."):
                        shot2 = capture_via_screenshotone(t2_article_url, api_key2)
                    st.session_state["t2_url_screenshot"] = shot2
                    st.image(Image.open(io.BytesIO(shot2)), caption="캡쳐 화면", use_container_width=True)
                    st.success("✅ 캡쳐 완료!")
                except Exception as e:
                    st.error(f"캡쳐 실패: {e}")

        elif "t2_url_screenshot" in st.session_state:
            st.image(Image.open(io.BytesIO(st.session_state["t2_url_screenshot"])),
                     caption="캡쳐 화면", use_container_width=True)

    st.divider()

    # ② 계산서
    st.markdown('<div class="section-label">② 계산서</div>', unsafe_allow_html=True)
    t2_invoice_files = st.file_uploader(
        "계산서 이미지/PDF를 업로드하세요",
        type=["jpg", "jpeg", "png", "pdf"],
        accept_multiple_files=True,
        key="t2_invoice"
    )
    if t2_invoice_files:
        st.success(f"✅ {len(t2_invoice_files)}개 파일 업로드됨")

    st.divider()

    # ③ 사업자등록증
    st.markdown('<div class="section-label">③ 사업자등록증</div>', unsafe_allow_html=True)
    t2_biz_files = st.file_uploader(
        "사업자등록증 이미지/PDF를 업로드하세요",
        type=["jpg", "jpeg", "png", "pdf"],
        accept_multiple_files=True,
        key="t2_biz"
    )
    if t2_biz_files:
        st.success(f"✅ {len(t2_biz_files)}개 파일 업로드됨")

    st.divider()

    # ④ 통장사본
    st.markdown('<div class="section-label">④ 통장사본</div>', unsafe_allow_html=True)
    t2_bank_files = st.file_uploader(
        "통장사본 이미지/PDF를 업로드하세요",
        type=["jpg", "jpeg", "png", "pdf"],
        accept_multiple_files=True,
        key="t2_bank"
    )
    if t2_bank_files:
        st.success(f"✅ {len(t2_bank_files)}개 파일 업로드됨")

    st.divider()

    # PDF 생성
    st.markdown("### 📥 PDF 생성")
    if not year_month or not media_name:
        st.info("상단에서 연도월과 매체명을 입력해주세요.")
    else:
        filename2 = f"{year_month}_{media_name}_뉴미디어협업증빙"
        if st.button(f"📄 '{filename2}.pdf' 생성하기", key="t2_gen"):

            t2_article_images: list[Image.Image] = []
            if "t2_url_screenshot" in st.session_state and st.session_state["t2_url_screenshot"]:
                t2_article_images.append(
                    Image.open(io.BytesIO(st.session_state["t2_url_screenshot"])).convert("RGB")
                )
            t2_article_images.extend(collect_files(t2_article_files))

            date_str2 = t2_article_date.strip() if t2_article_date.strip() else "날짜 미입력"
            result_label = f"① 게재 결과 ({media_name}, {date_str2})"

            sections2 = [
                {"label": result_label,      "images": t2_article_images,               "link": t2_article_link},
                {"label": "② 계산서",        "images": collect_files(t2_invoice_files),  "link": ""},
                {"label": "③ 사업자등록증",   "images": collect_files(t2_biz_files),      "link": ""},
                {"label": "④ 통장사본",       "images": collect_files(t2_bank_files),     "link": ""},
            ]
            sections2 = [s for s in sections2 if s["images"]]

            if not sections2:
                st.warning("⚠️ 업로드된 파일이 없습니다.")
            else:
                with st.spinner("PDF 생성 중..."):
                    try:
                        pdf_bytes2 = generate_pdf(sections2, filename2)
                        total2 = sum(len(s["images"]) for s in sections2)
                        st.markdown(
                            f'<div class="success-box">✅ PDF 생성 완료 — 총 {total2}장, {len(sections2)}개 섹션</div>',
                            unsafe_allow_html=True
                        )
                        st.download_button(
                            label=f"⬇️ {filename2}.pdf 다운로드",
                            data=pdf_bytes2,
                            file_name=f"{filename2}.pdf",
                            mime="application/pdf",
                            use_container_width=True,
                        )
                    except Exception as e:
                        st.error(f"PDF 생성 중 오류: {e}")
