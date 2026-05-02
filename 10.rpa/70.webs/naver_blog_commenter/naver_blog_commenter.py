"""
NaverBlogCommenter - 네이버 블로그 이웃 자동 공감+댓글 RPA
WorksFree RPA App Store | worksfree.co.kr
──────────────────────────────────────────
크레딧 과금: 공감 1건 = 1크레딧 / AI댓글 1건 = 3크레딧 / 기본댓글 1건 = 1크레딧
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import threading
import time
import random
import json
import os
import sys
from datetime import datetime
from dataclasses import dataclass, field
from typing import Optional

# ── Selenium ──────────────────────────────────────────────────────────────────
try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.common.exceptions import (
        TimeoutException, NoSuchElementException, ElementClickInterceptedException
    )
    SELENIUM_OK = True
except ImportError:
    SELENIUM_OK = False

# ── Anthropic Claude API ───────────────────────────────────────────────────────
try:
    import anthropic
    CLAUDE_OK = True
except ImportError:
    CLAUDE_OK = False

# ─────────────────────────────────────────────────────────────────────────────
# 설정 파일 경로
# ─────────────────────────────────────────────────────────────────────────────
BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "config.json")

DEFAULT_PRESETS = [
    "좋은 글 잘 읽었습니다! 오늘도 행복한 하루 되세요 😊",
    "유익한 정보 감사합니다! 자주 방문할게요 🙌",
    "공감하며 잘 보고 갑니다. 앞으로도 좋은 글 부탁드려요!",
    "정성스러운 포스팅 잘 읽었습니다. 응원합니다 💪",
    "오늘도 좋은 글 감사해요! 맞이웃 소통 즐겁습니다 ✨",
]

# ─────────────────────────────────────────────────────────────────────────────
# 설정 데이터
# ─────────────────────────────────────────────────────────────────────────────
@dataclass
class AppConfig:
    naver_id: str = ""
    naver_pw: str = ""
    claude_api_key: str = ""
    comment_mode: str = "preset"       # "preset" | "ai"
    preset_comments: list = field(default_factory=lambda: list(DEFAULT_PRESETS))
    max_blogs: int = 30                # 최대 처리 이웃 수
    delay_min: float = 3.0             # 최소 딜레이(초)
    delay_max: float = 7.0             # 최대 딜레이(초)
    do_sympathy: bool = True           # 공감 여부
    do_comment: bool = True            # 댓글 여부
    credits: int = 0

    def save(self):
        data = {
            "naver_id": self.naver_id,
            "claude_api_key": self.claude_api_key,
            "comment_mode": self.comment_mode,
            "preset_comments": self.preset_comments,
            "max_blogs": self.max_blogs,
            "delay_min": self.delay_min,
            "delay_max": self.delay_max,
            "do_sympathy": self.do_sympathy,
            "do_comment": self.do_comment,
            "credits": self.credits,
            # 비밀번호는 저장하지 않음 (보안)
        }
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    @classmethod
    def load(cls) -> "AppConfig":
        cfg = cls()
        if os.path.exists(CONFIG_PATH):
            try:
                with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                    data = json.load(f)
                for k, v in data.items():
                    if hasattr(cfg, k):
                        setattr(cfg, k, v)
            except Exception:
                pass
        return cfg


# ─────────────────────────────────────────────────────────────────────────────
# Claude AI 댓글 생성
# ─────────────────────────────────────────────────────────────────────────────
def generate_ai_comment(api_key: str, title: str, content_snippet: str) -> str:
    if not CLAUDE_OK:
        return "좋은 글 잘 읽었습니다! 오늘도 행복한 하루 되세요 😊"
    try:
        client = anthropic.Anthropic(api_key=api_key)
        prompt = f"""다음 네이버 블로그 포스팅에 달 자연스러운 댓글을 1개만 작성해 주세요.

[포스팅 제목]
{title}

[본문 요약]
{content_snippet[:500] if content_snippet else "(본문 없음)"}

조건:
- 2~3문장, 50자 이내
- 포스팅 내용을 실제로 읽은 것처럼 구체적으로 언급
- 자연스럽고 따뜻한 한국어 구어체
- 이모지 1~2개 포함
- 광고/홍보 문구 절대 포함 금지
- 댓글 텍스트만 출력 (따옴표, 설명 없이)"""

        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=150,
            messages=[{"role": "user", "content": prompt}]
        )
        return message.content[0].text.strip().strip('"').strip("'")
    except Exception as e:
        return f"좋은 글 잘 읽었습니다! 오늘도 좋은 하루 되세요 😊"


# ─────────────────────────────────────────────────────────────────────────────
# 자동화 엔진
# ─────────────────────────────────────────────────────────────────────────────
class NaverBlogBot:
    def __init__(self, config: AppConfig, log_fn, progress_fn, credit_fn):
        self.cfg = config
        self.log = log_fn
        self.set_progress = progress_fn
        self.update_credit = credit_fn
        self.driver: Optional[webdriver.Chrome] = None
        self._stop = False
        self._preset_idx = 0

    def stop(self):
        self._stop = True

    def _next_preset(self) -> str:
        comments = self.cfg.preset_comments
        comment = comments[self._preset_idx % len(comments)]
        self._preset_idx += 1
        return comment

    def _random_delay(self):
        t = random.uniform(self.cfg.delay_min, self.cfg.delay_max)
        time.sleep(t)

    def _init_driver(self) -> bool:
        try:
            opts = Options()
            opts.add_argument("--disable-blink-features=AutomationControlled")
            opts.add_experimental_option("excludeSwitches", ["enable-automation"])
            opts.add_experimental_option("useAutomationExtension", False)
            opts.add_argument("--start-maximized")
            opts.add_argument("--disable-notifications")
            opts.add_argument(
                "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            )
            self.driver = webdriver.Chrome(options=opts)
            self.driver.execute_script(
                "Object.defineProperty(navigator,'webdriver',{get:()=>undefined})"
            )
            return True
        except Exception as e:
            self.log(f"[오류] 크롬 드라이버 초기화 실패: {e}", "error")
            return False

    def _login(self) -> bool:
        try:
            self.log("🔐 네이버 로그인 시도 중...")
            self.driver.get("https://nid.naver.com/nidlogin.login")
            wait = WebDriverWait(self.driver, 15)

            id_field = wait.until(EC.presence_of_element_located((By.ID, "id")))
            pw_field  = self.driver.find_element(By.ID, "pw")

            # 자연스러운 타이핑 (봇 감지 우회)
            self.driver.execute_script(
                "arguments[0].value = arguments[1]", id_field, self.cfg.naver_id
            )
            self.driver.execute_script(
                "arguments[0].value = arguments[1]", pw_field, self.cfg.naver_pw
            )
            pw_field.submit()
            time.sleep(3)

            # 로그인 성공 확인
            if "nid.naver.com" not in self.driver.current_url:
                self.log("✅ 로그인 성공", "success")
                return True
            else:
                self.log("[오류] 로그인 실패 — 아이디/비밀번호 확인 또는 캡챠 발생", "error")
                return False
        except Exception as e:
            self.log(f"[오류] 로그인 중 예외: {e}", "error")
            return False

    def _get_neighbor_posts(self) -> list[dict]:
        """이웃 새글 목록 수집 (모바일 피드 API 활용)"""
        posts = []
        try:
            self.log("📋 이웃 새글 목록 수집 중...")
            self.driver.get("https://m.blog.naver.com/FollowFeedList.naver")
            time.sleep(2)

            wait = WebDriverWait(self.driver, 10)
            # 스크롤로 더 많은 게시물 로드
            for _ in range(3):
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight)")
                time.sleep(1.5)

            items = self.driver.find_elements(
                By.CSS_SELECTOR, ".follow_feed_item, .blog_item, [class*='feed_item']"
            )
            if not items:
                # PC 피드 시도
                self.driver.get(
                    "https://blog.naver.com/FollowingPost.naver?followingId=&orderType=date"
                )
                time.sleep(2)
                items = self.driver.find_elements(
                    By.CSS_SELECTOR,
                    ".blog2_list .item, .blog_list .entry, [class*='post_item']"
                )

            for item in items[: self.cfg.max_blogs]:
                try:
                    link_el = item.find_element(By.CSS_SELECTOR, "a[href*='blog.naver.com'], a[href*='blogId']")
                    href    = link_el.get_attribute("href")
                    title   = link_el.text.strip() or "제목 없음"
                    if href and href not in [p["url"] for p in posts]:
                        posts.append({"url": href, "title": title})
                except Exception:
                    continue

            self.log(f"📌 수집된 게시물: {len(posts)}건")
        except Exception as e:
            self.log(f"[오류] 이웃 글 수집 실패: {e}", "error")
        return posts

    def _process_post(self, post: dict, index: int, total: int) -> dict:
        """게시물 1건 처리 (공감 + 댓글)"""
        result = {"sympathy": False, "comment": False, "credits_used": 0}
        url    = post["url"]
        title  = post["title"]

        try:
            self.driver.get(url)
            time.sleep(2)
            self.log(f"[{index}/{total}] 📄 {title[:30]}...")

            # ── 공감 클릭 ──────────────────────────────────────────────────
            if self.cfg.do_sympathy and not self._stop:
                try:
                    # PC / 모바일 공감 버튼 탐색
                    sympathy_selectors = [
                        ".u_cnt._count",
                        ".btn_sympathy",
                        "[class*='sympathy']",
                        ".ico_like",
                        "#likeItButton",
                    ]
                    clicked = False
                    for sel in sympathy_selectors:
                        btns = self.driver.find_elements(By.CSS_SELECTOR, sel)
                        if btns:
                            try:
                                self.driver.execute_script("arguments[0].click()", btns[0])
                                clicked = True
                                break
                            except Exception:
                                continue

                    if clicked:
                        result["sympathy"] = True
                        result["credits_used"] += 1
                        self.log(f"  👍 공감 완료 (-1크레딧)", "success")
                    else:
                        self.log(f"  ⚠️ 공감 버튼 없음 (이미 공감 or 셀렉터 변경)", "warn")
                    time.sleep(1)
                except Exception as e:
                    self.log(f"  ⚠️ 공감 오류: {e}", "warn")

            # ── 댓글 작성 ──────────────────────────────────────────────────
            if self.cfg.do_comment and not self._stop:
                credits_needed = 3 if self.cfg.comment_mode == "ai" else 1

                if self.cfg.credits < credits_needed:
                    self.log("  ❌ 크레딧 부족 — 댓글 건너뜀", "error")
                else:
                    # 댓글 생성
                    if self.cfg.comment_mode == "ai":
                        self.log(f"  🤖 Claude AI 댓글 생성 중...", "info")
                        content_snippet = self._get_post_content()
                        comment_text = generate_ai_comment(
                            self.cfg.claude_api_key, title, content_snippet
                        )
                        self.log(f"  💬 AI 댓글: {comment_text[:40]}...", "info")
                    else:
                        comment_text = self._next_preset()
                        self.log(f"  💬 기본 댓글: {comment_text[:40]}...", "info")

                    # 댓글 입력
                    posted = self._post_comment(comment_text)
                    if posted:
                        result["comment"] = True
                        result["credits_used"] += credits_needed
                        self.log(f"  ✅ 댓글 작성 완료 (-{credits_needed}크레딧)", "success")
                    else:
                        self.log(f"  ⚠️ 댓글 작성 실패 (댓글 불가 게시물)", "warn")

        except Exception as e:
            self.log(f"  [오류] 게시물 처리 실패: {e}", "error")

        return result

    def _get_post_content(self) -> str:
        """현재 페이지 포스팅 본문 추출"""
        try:
            selectors = [
                ".se-main-container",
                "#postViewArea",
                ".post_ct",
                "[class*='post_view']",
            ]
            for sel in selectors:
                els = self.driver.find_elements(By.CSS_SELECTOR, sel)
                if els:
                    return els[0].text[:600]
        except Exception:
            pass
        return ""

    def _post_comment(self, text: str) -> bool:
        """댓글 입력 및 제출"""
        try:
            wait = WebDriverWait(self.driver, 8)
            # 댓글 iframe 탐색
            iframes = self.driver.find_elements(By.CSS_SELECTOR, "iframe[id*='comment'], iframe[src*='comment']")
            if iframes:
                self.driver.switch_to.frame(iframes[0])

            textarea_selectors = [
                "textarea[placeholder*='댓글']",
                ".cmt_write textarea",
                "#commentText",
                "[class*='comment_write'] textarea",
                ".u_cbox_write textarea",
            ]
            textarea = None
            for sel in textarea_selectors:
                els = self.driver.find_elements(By.CSS_SELECTOR, sel)
                if els:
                    textarea = els[0]
                    break

            if not textarea:
                self.driver.switch_to.default_content()
                return False

            textarea.click()
            time.sleep(0.5)
            self.driver.execute_script("arguments[0].value = arguments[1]", textarea, text)
            textarea.send_keys(" ")  # 이벤트 트리거
            time.sleep(0.5)

            # 등록 버튼
            submit_selectors = [
                "button[class*='submit']",
                ".btn_register",
                "#btnRegister",
                "[class*='cmt_submit']",
                "button[type='submit']",
            ]
            for sel in submit_selectors:
                btns = self.driver.find_elements(By.CSS_SELECTOR, sel)
                if btns:
                    self.driver.execute_script("arguments[0].click()", btns[0])
                    self.driver.switch_to.default_content()
                    time.sleep(2)
                    return True

            self.driver.switch_to.default_content()
            return False
        except Exception as e:
            try:
                self.driver.switch_to.default_content()
            except Exception:
                pass
            return False

    def run(self):
        """메인 실행"""
        if not SELENIUM_OK:
            self.log("[오류] selenium 패키지가 설치되지 않았습니다.\npip install selenium", "error")
            return

        if not self._init_driver():
            return

        try:
            if not self._login():
                self.driver.quit()
                return

            posts = self._get_neighbor_posts()
            if not posts:
                self.log("⚠️ 처리할 게시물이 없습니다.", "warn")
                self.driver.quit()
                return

            total         = len(posts)
            done_sympathy = 0
            done_comment  = 0
            total_credits = 0

            self.log(f"\n🚀 작업 시작 — 총 {total}건\n{'─'*40}")

            for i, post in enumerate(posts, 1):
                if self._stop:
                    self.log("\n⛔ 사용자 중단 요청")
                    break

                result = self._process_post(post, i, total)

                # 크레딧 차감
                if result["credits_used"] > 0:
                    self.cfg.credits -= result["credits_used"]
                    total_credits    += result["credits_used"]
                    self.cfg.save()
                    self.update_credit(self.cfg.credits)

                if result["sympathy"]: done_sympathy += 1
                if result["comment"]:  done_comment  += 1

                self.set_progress(int(i / total * 100))

                if i < total and not self._stop:
                    delay = random.uniform(self.cfg.delay_min, self.cfg.delay_max)
                    self.log(f"  ⏳ 다음 블로그까지 {delay:.1f}초 대기...")
                    time.sleep(delay)

            self.log(f"\n{'─'*40}")
            self.log(f"✅ 작업 완료!")
            self.log(f"   👍 공감: {done_sympathy}건  💬 댓글: {done_comment}건")
            self.log(f"   💳 사용 크레딧: {total_credits}  |  잔여: {self.cfg.credits}")

        finally:
            if self.driver:
                self.driver.quit()
            self.set_progress(100)


# ─────────────────────────────────────────────────────────────────────────────
# GUI
# ─────────────────────────────────────────────────────────────────────────────
class App(tk.Tk):
    COLORS = {
        "bg":       "#0F1117",
        "panel":    "#1A1D27",
        "border":   "#2A2D3E",
        "accent":   "#03C75A",   # 네이버 그린
        "accent2":  "#00B4FF",   # 블루 포인트
        "danger":   "#FF4757",
        "warn":     "#FFA502",
        "text":     "#E8EAF0",
        "sub":      "#8892AA",
        "success":  "#03C75A",
        "entry_bg": "#12151F",
    }

    def __init__(self):
        super().__init__()
        self.cfg  = AppConfig.load()
        self.bot: Optional[NaverBlogBot] = None
        self._bot_thread: Optional[threading.Thread] = None

        self.title("NaverBlogCommenter  |  WorksFree RPA")
        self.geometry("980x740")
        self.resizable(True, True)
        self.configure(bg=self.COLORS["bg"])
        self.minsize(860, 660)

        self._build_ui()

    # ── UI 구성 ───────────────────────────────────────────────────────────────
    def _build_ui(self):
        C = self.COLORS

        # ── 헤더 ────────────────────────────────────────────────────────────
        hdr = tk.Frame(self, bg=C["panel"], height=56)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)

        tk.Label(hdr, text="  🟢 NaverBlog Commenter",
                 font=("Malgun Gothic", 14, "bold"),
                 bg=C["panel"], fg=C["accent"]).pack(side="left", padx=16, pady=12)

        tk.Label(hdr, text="WorksFree RPA  v1.0",
                 font=("Malgun Gothic", 9),
                 bg=C["panel"], fg=C["sub"]).pack(side="left", pady=12)

        # 크레딧 표시
        self.credit_frame = tk.Frame(hdr, bg=C["panel"])
        self.credit_frame.pack(side="right", padx=16)
        tk.Label(self.credit_frame, text="💳 잔여 크레딧",
                 font=("Malgun Gothic", 9), bg=C["panel"], fg=C["sub"]).pack(side="left")
        self.lbl_credit = tk.Label(self.credit_frame,
                                   text=f"  {self.cfg.credits}",
                                   font=("Malgun Gothic", 12, "bold"),
                                   bg=C["panel"], fg=C["accent2"])
        self.lbl_credit.pack(side="left")

        # ── 메인 2열 ────────────────────────────────────────────────────────
        body = tk.Frame(self, bg=C["bg"])
        body.pack(fill="both", expand=True, padx=12, pady=10)

        left  = tk.Frame(body, bg=C["bg"], width=340)
        right = tk.Frame(body, bg=C["bg"])
        left.pack(side="left", fill="y", padx=(0, 8))
        right.pack(side="left", fill="both", expand=True)
        left.pack_propagate(False)

        self._build_left(left)
        self._build_right(right)

    def _card(self, parent, title: str) -> tk.Frame:
        C = self.COLORS
        wrap = tk.Frame(parent, bg=C["bg"])
        wrap.pack(fill="x", pady=(0, 10))

        tk.Label(wrap, text=title,
                 font=("Malgun Gothic", 9, "bold"),
                 bg=C["bg"], fg=C["sub"]).pack(anchor="w", padx=2, pady=(0, 4))

        card = tk.Frame(wrap, bg=C["panel"],
                        highlightthickness=1,
                        highlightbackground=C["border"])
        card.pack(fill="x")
        return card

    def _row(self, parent, label: str, widget_fn):
        C = self.COLORS
        row = tk.Frame(parent, bg=C["panel"])
        row.pack(fill="x", padx=12, pady=5)
        tk.Label(row, text=label, width=11, anchor="w",
                 font=("Malgun Gothic", 9),
                 bg=C["panel"], fg=C["sub"]).pack(side="left")
        w = widget_fn(row)
        w.pack(side="left", fill="x", expand=True)
        return w

    def _entry(self, parent, textvariable=None, show=None) -> tk.Entry:
        C = self.COLORS
        e = tk.Entry(parent, bg=C["entry_bg"], fg=C["text"],
                     insertbackground=C["accent"],
                     relief="flat", font=("Malgun Gothic", 10),
                     textvariable=textvariable, show=show,
                     highlightthickness=1,
                     highlightbackground=C["border"],
                     highlightcolor=C["accent"])
        return e

    # ── 왼쪽 패널 ─────────────────────────────────────────────────────────────
    def _build_left(self, parent):
        C = self.COLORS

        # ── 로그인 정보 ──────────────────────────────────────────────────────
        card1 = self._card(parent, "▸ 네이버 계정")
        self.var_id = tk.StringVar(value=self.cfg.naver_id)
        self.var_pw = tk.StringVar()

        self.ent_id = self._row(card1, "아이디",
                                lambda p: self._entry(p, self.var_id))
        self.ent_pw = self._row(card1, "비밀번호",
                                lambda p: self._entry(p, self.var_pw, show="●"))
        tk.Frame(card1, bg=C["panel"], height=8).pack()

        # ── Claude API ────────────────────────────────────────────────────────
        card2 = self._card(parent, "▸ Claude API (AI 댓글 모드)")
        self.var_api = tk.StringVar(value=self.cfg.claude_api_key)
        self.ent_api = self._row(card2, "API Key",
                                 lambda p: self._entry(p, self.var_api, show="●"))
        tk.Label(card2,
                 text="  AI 댓글 1건 = 3크레딧  |  미입력 시 기본 댓글로 대체",
                 font=("Malgun Gothic", 8), bg=C["panel"], fg=C["sub"]).pack(
                     anchor="w", padx=12, pady=(0, 8))

        # ── 실행 옵션 ─────────────────────────────────────────────────────────
        card3 = self._card(parent, "▸ 실행 옵션")

        # 댓글 모드
        mode_row = tk.Frame(card3, bg=C["panel"])
        mode_row.pack(fill="x", padx=12, pady=6)
        tk.Label(mode_row, text="댓글 모드", width=11, anchor="w",
                 font=("Malgun Gothic", 9), bg=C["panel"], fg=C["sub"]).pack(side="left")

        self.var_mode = tk.StringVar(value=self.cfg.comment_mode)
        rb_preset = tk.Radiobutton(mode_row, text="기본 순차",
                                   variable=self.var_mode, value="preset",
                                   bg=C["panel"], fg=C["text"],
                                   selectcolor=C["entry_bg"],
                                   activebackground=C["panel"],
                                   font=("Malgun Gothic", 9),
                                   command=self._on_mode_change)
        rb_ai = tk.Radiobutton(mode_row, text="AI (Claude)",
                               variable=self.var_mode, value="ai",
                               bg=C["panel"], fg=C["accent2"],
                               selectcolor=C["entry_bg"],
                               activebackground=C["panel"],
                               font=("Malgun Gothic", 9, "bold"),
                               command=self._on_mode_change)
        rb_preset.pack(side="left", padx=4)
        rb_ai.pack(side="left", padx=4)

        # 최대 블로그 수
        cnt_row = tk.Frame(card3, bg=C["panel"])
        cnt_row.pack(fill="x", padx=12, pady=4)
        tk.Label(cnt_row, text="최대 블로그", width=11, anchor="w",
                 font=("Malgun Gothic", 9), bg=C["panel"], fg=C["sub"]).pack(side="left")
        self.var_max = tk.IntVar(value=self.cfg.max_blogs)
        spin = tk.Spinbox(cnt_row, from_=1, to=100, textvariable=self.var_max,
                          width=6, font=("Malgun Gothic", 10),
                          bg=C["entry_bg"], fg=C["text"],
                          buttonbackground=C["border"], relief="flat")
        spin.pack(side="left")
        tk.Label(cnt_row, text="  건",
                 font=("Malgun Gothic", 9), bg=C["panel"], fg=C["sub"]).pack(side="left")

        # 딜레이
        delay_row = tk.Frame(card3, bg=C["panel"])
        delay_row.pack(fill="x", padx=12, pady=4)
        tk.Label(delay_row, text="딜레이", width=11, anchor="w",
                 font=("Malgun Gothic", 9), bg=C["panel"], fg=C["sub"]).pack(side="left")
        self.var_dmin = tk.DoubleVar(value=self.cfg.delay_min)
        self.var_dmax = tk.DoubleVar(value=self.cfg.delay_max)
        tk.Spinbox(delay_row, from_=1, to=30, textvariable=self.var_dmin,
                   width=5, font=("Malgun Gothic", 10),
                   bg=C["entry_bg"], fg=C["text"],
                   buttonbackground=C["border"], relief="flat",
                   increment=0.5).pack(side="left")
        tk.Label(delay_row, text=" ~ ", bg=C["panel"], fg=C["sub"],
                 font=("Malgun Gothic", 9)).pack(side="left")
        tk.Spinbox(delay_row, from_=1, to=60, textvariable=self.var_dmax,
                   width=5, font=("Malgun Gothic", 10),
                   bg=C["entry_bg"], fg=C["text"],
                   buttonbackground=C["border"], relief="flat",
                   increment=0.5).pack(side="left")
        tk.Label(delay_row, text=" 초", bg=C["panel"], fg=C["sub"],
                 font=("Malgun Gothic", 9)).pack(side="left")

        # 체크박스
        chk_row = tk.Frame(card3, bg=C["panel"])
        chk_row.pack(fill="x", padx=12, pady=(4, 10))
        self.var_sym = tk.BooleanVar(value=self.cfg.do_sympathy)
        self.var_cmt = tk.BooleanVar(value=self.cfg.do_comment)
        tk.Checkbutton(chk_row, text="👍 공감",
                       variable=self.var_sym, bg=C["panel"], fg=C["text"],
                       selectcolor=C["entry_bg"], activebackground=C["panel"],
                       font=("Malgun Gothic", 9)).pack(side="left", padx=(0, 12))
        tk.Checkbutton(chk_row, text="💬 댓글",
                       variable=self.var_cmt, bg=C["panel"], fg=C["text"],
                       selectcolor=C["entry_bg"], activebackground=C["panel"],
                       font=("Malgun Gothic", 9)).pack(side="left")

        # ── 크레딧 충전 (임시 데모) ───────────────────────────────────────────
        card4 = self._card(parent, "▸ 크레딧")
        charge_row = tk.Frame(card4, bg=C["panel"])
        charge_row.pack(fill="x", padx=12, pady=8)
        tk.Label(charge_row, text="충전 코드",
                 font=("Malgun Gothic", 9), bg=C["panel"], fg=C["sub"]).pack(side="left")
        self.var_code = tk.StringVar()
        self._entry(charge_row, self.var_code).pack(side="left", fill="x",
                                                     expand=True, padx=6)
        tk.Button(charge_row, text="충전",
                  bg=C["accent2"], fg="white",
                  font=("Malgun Gothic", 9, "bold"),
                  relief="flat", padx=8,
                  command=self._charge_credit).pack(side="left")

        # ── 실행 버튼 ─────────────────────────────────────────────────────────
        btn_row = tk.Frame(parent, bg=C["bg"])
        btn_row.pack(fill="x", pady=6)

        self.btn_run = tk.Button(
            btn_row, text="▶  실행 시작",
            bg=C["accent"], fg="#000",
            font=("Malgun Gothic", 11, "bold"),
            relief="flat", height=2,
            cursor="hand2",
            command=self._start
        )
        self.btn_run.pack(fill="x", ipady=4)

        self.btn_stop = tk.Button(
            btn_row, text="⛔  중지",
            bg=C["danger"], fg="white",
            font=("Malgun Gothic", 10, "bold"),
            relief="flat",
            cursor="hand2",
            state="disabled",
            command=self._stop
        )
        self.btn_stop.pack(fill="x", pady=(4, 0), ipady=3)

        # 진행 바
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Green.Horizontal.TProgressbar",
                         troughcolor=C["border"],
                         background=C["accent"],
                         borderwidth=0)
        self.progress = ttk.Progressbar(parent, style="Green.Horizontal.TProgressbar",
                                        length=200, mode="determinate")
        self.progress.pack(fill="x", pady=(8, 0))

        self.lbl_status = tk.Label(parent, text="대기 중",
                                   font=("Malgun Gothic", 8),
                                   bg=C["bg"], fg=C["sub"])
        self.lbl_status.pack(anchor="w")

    # ── 오른쪽 패널 ───────────────────────────────────────────────────────────
    def _build_right(self, parent):
        C = self.COLORS
        nb = ttk.Notebook(parent)
        nb.pack(fill="both", expand=True)

        style = ttk.Style()
        style.configure("TNotebook",       background=C["bg"],  borderwidth=0)
        style.configure("TNotebook.Tab",   background=C["panel"],
                        foreground=C["sub"],
                        padding=[12, 6],
                        font=("Malgun Gothic", 9))
        style.map("TNotebook.Tab",
                  background=[("selected", C["accent"])],
                  foreground=[("selected", "#000")])

        # ── 탭1: 실행 로그 ────────────────────────────────────────────────────
        log_frame = tk.Frame(nb, bg=C["bg"])
        nb.add(log_frame, text="  📋 실행 로그  ")

        log_top = tk.Frame(log_frame, bg=C["bg"])
        log_top.pack(fill="x", padx=4, pady=(6, 2))
        tk.Label(log_top, text="실행 로그",
                 font=("Malgun Gothic", 9, "bold"),
                 bg=C["bg"], fg=C["sub"]).pack(side="left")
        tk.Button(log_top, text="지우기",
                  bg=C["border"], fg=C["sub"],
                  font=("Malgun Gothic", 8), relief="flat",
                  command=self._clear_log).pack(side="right")

        self.log_box = scrolledtext.ScrolledText(
            log_frame,
            bg=C["entry_bg"], fg=C["text"],
            font=("Consolas", 9),
            relief="flat",
            insertbackground=C["accent"],
            wrap="word",
        )
        self.log_box.pack(fill="both", expand=True, padx=4, pady=(0, 4))
        self.log_box.tag_config("success", foreground=C["success"])
        self.log_box.tag_config("error",   foreground=C["danger"])
        self.log_box.tag_config("warn",    foreground=C["warn"])
        self.log_box.tag_config("info",    foreground=C["accent2"])

        # ── 탭2: 기본 댓글 설정 ────────────────────────────────────────────────
        preset_frame = tk.Frame(nb, bg=C["bg"])
        nb.add(preset_frame, text="  ✏️ 기본 댓글  ")

        tk.Label(preset_frame,
                 text="순차 사용될 기본 댓글 5개를 설정하세요 (모드 A)",
                 font=("Malgun Gothic", 9), bg=C["bg"], fg=C["sub"]).pack(
                     anchor="w", padx=8, pady=(8, 4))

        self.preset_vars = []
        self.preset_entries = []
        for i, pc in enumerate(self.cfg.preset_comments[:5]):
            row = tk.Frame(preset_frame, bg=C["bg"])
            row.pack(fill="x", padx=8, pady=3)
            tk.Label(row, text=f"{i+1}",
                     font=("Malgun Gothic", 9, "bold"),
                     bg=C["bg"], fg=C["accent"],
                     width=2).pack(side="left")
            var = tk.StringVar(value=pc)
            self.preset_vars.append(var)
            ent = self._entry(row, var)
            ent.pack(side="left", fill="x", expand=True, padx=4)
            self.preset_entries.append(ent)

        tk.Button(preset_frame, text="💾  댓글 저장",
                  bg=C["accent"], fg="#000",
                  font=("Malgun Gothic", 9, "bold"),
                  relief="flat",
                  command=self._save_presets).pack(
                      anchor="w", padx=8, pady=10, ipadx=12, ipady=4)

        # ── 탭3: 요금 안내 ─────────────────────────────────────────────────────
        fee_frame = tk.Frame(nb, bg=C["bg"])
        nb.add(fee_frame, text="  💳 요금 안내  ")
        self._build_fee_tab(fee_frame)

    def _build_fee_tab(self, parent):
        C = self.COLORS
        fee_info = [
            ("👍 공감",          "1 크레딧 / 건",  "이웃 블로그 자동 공감 클릭"),
            ("💬 기본 댓글",     "1 크레딧 / 건",  "5개 기본 댓글 순차 입력"),
            ("🤖 AI 댓글 (Claude)", "3 크레딧 / 건", "포스팅 내용 분석 후 맞춤 댓글 생성"),
        ]
        tk.Label(parent, text="\n  크레딧 소비 기준",
                 font=("Malgun Gothic", 11, "bold"),
                 bg=C["bg"], fg=C["text"]).pack(anchor="w", padx=16)

        for action, cost, desc in fee_info:
            row = tk.Frame(parent, bg=C["panel"],
                           highlightthickness=1, highlightbackground=C["border"])
            row.pack(fill="x", padx=16, pady=5)
            tk.Label(row, text=f"  {action}",
                     font=("Malgun Gothic", 10, "bold"),
                     bg=C["panel"], fg=C["text"], width=22, anchor="w").pack(
                         side="left", pady=10)
            tk.Label(row, text=cost,
                     font=("Malgun Gothic", 10, "bold"),
                     bg=C["panel"], fg=C["accent"], width=18).pack(side="left")
            tk.Label(row, text=desc,
                     font=("Malgun Gothic", 9),
                     bg=C["panel"], fg=C["sub"]).pack(side="left")

        tk.Label(parent,
                 text="\n  ※ 크레딧 충전은 worksfree.co.kr 에서 결제 후 코드를 입력하세요.",
                 font=("Malgun Gothic", 9), bg=C["bg"], fg=C["sub"]).pack(
                     anchor="w", padx=16)

    # ── 이벤트 핸들러 ──────────────────────────────────────────────────────────
    def _on_mode_change(self):
        pass  # 추후 AI 탭 자동 활성화 등 확장 가능

    def _save_presets(self):
        self.cfg.preset_comments = [v.get() for v in self.preset_vars]
        self.cfg.save()
        self._log_msg("💾 기본 댓글이 저장되었습니다.", "success")
        messagebox.showinfo("저장 완료", "기본 댓글이 저장되었습니다.")

    def _charge_credit(self):
        code = self.var_code.get().strip()
        # TODO: wf_license 모듈 연동 (서버 검증)
        # 데모: 특정 코드로 임시 충전
        DEMO_CODES = {"DEMO100": 100, "DEMO300": 300, "WF2024": 50}
        if code in DEMO_CODES:
            amount = DEMO_CODES[code]
            self.cfg.credits += amount
            self.cfg.save()
            self.lbl_credit.config(text=f"  {self.cfg.credits}")
            self._log_msg(f"💳 크레딧 {amount} 충전 완료 (잔여: {self.cfg.credits})", "success")
            messagebox.showinfo("충전 완료", f"크레딧 {amount}이 충전되었습니다.")
        else:
            messagebox.showerror("오류", "유효하지 않은 충전 코드입니다.")
        self.var_code.set("")

    def _start(self):
        naver_id = self.var_id.get().strip()
        naver_pw = self.var_pw.get().strip()

        if not naver_id or not naver_pw:
            messagebox.showwarning("입력 오류", "네이버 아이디와 비밀번호를 입력하세요.")
            return

        if self.cfg.credits <= 0:
            messagebox.showwarning("크레딧 부족",
                                   "크레딧이 없습니다.\n충전 코드를 입력하여 충전하세요.")
            return

        # 설정 반영
        self.cfg.naver_id     = naver_id
        self.cfg.naver_pw     = naver_pw
        self.cfg.claude_api_key = self.var_api.get().strip()
        self.cfg.comment_mode = self.var_mode.get()
        self.cfg.max_blogs    = self.var_max.get()
        self.cfg.delay_min    = self.var_dmin.get()
        self.cfg.delay_max    = self.var_dmax.get()
        self.cfg.do_sympathy  = self.var_sym.get()
        self.cfg.do_comment   = self.var_cmt.get()
        self.cfg.save()

        self.btn_run.config(state="disabled")
        self.btn_stop.config(state="normal")
        self.progress["value"] = 0
        self.lbl_status.config(text="실행 중...")

        self._log_msg(f"\n{'═'*45}")
        self._log_msg(f"🚀 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} 실행 시작")
        self._log_msg(f"   모드: {'🤖 AI (Claude)' if self.cfg.comment_mode == 'ai' else '📝 기본 순차'}")
        self._log_msg(f"   최대: {self.cfg.max_blogs}건  딜레이: {self.cfg.delay_min}~{self.cfg.delay_max}초")
        self._log_msg(f"{'═'*45}")

        self.bot = NaverBlogBot(
            config      = self.cfg,
            log_fn      = self._log_msg,
            progress_fn = self._set_progress,
            credit_fn   = self._update_credit,
        )
        self._bot_thread = threading.Thread(target=self._run_bot, daemon=True)
        self._bot_thread.start()

    def _run_bot(self):
        try:
            self.bot.run()
        finally:
            self.after(0, self._on_done)

    def _stop(self):
        if self.bot:
            self.bot.stop()
        self.btn_stop.config(state="disabled")

    def _on_done(self):
        self.btn_run.config(state="normal")
        self.btn_stop.config(state="disabled")
        self.lbl_status.config(text="완료")

    # ── 공통 헬퍼 ─────────────────────────────────────────────────────────────
    def _log_msg(self, msg: str, tag: str = ""):
        def _do():
            ts = datetime.now().strftime("%H:%M:%S")
            self.log_box.insert("end", f"[{ts}] {msg}\n", tag)
            self.log_box.see("end")
        self.after(0, _do)

    def _set_progress(self, val: int):
        def _do():
            self.progress["value"] = val
            self.lbl_status.config(text=f"진행: {val}%")
        self.after(0, _do)

    def _update_credit(self, val: int):
        self.after(0, lambda: self.lbl_credit.config(text=f"  {val}"))

    def _clear_log(self):
        self.log_box.delete("1.0", "end")


# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    app = App()
    app.mainloop()
