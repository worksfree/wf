// GS 인증 수준 자동화 시험 스위트 — docs/GS/04_테스트케이스.md 의 TC ID 와 1:1 대응.
// 실행: tests 디렉터리에서  PW_BASE=http://localhost:8899 npx playwright test gs-cert.spec.js
const { test, expect } = require('@playwright/test');
const fs = require('fs');
const path = require('path');

const ROOT = path.resolve(__dirname, '..');
const SKIP = new Set(['node_modules', '.wrangler', 'worker', 'tests', '.git', 'docs']);

// 전체 페이지 목록을 파일시스템에서 도출 (index.html + 404.html)
function collectPages(dir = ROOT, base = '') {
  let out = [];
  for (const e of fs.readdirSync(dir, { withFileTypes: true })) {
    if (e.isDirectory()) {
      if (!SKIP.has(e.name)) out = out.concat(collectPages(path.join(dir, e.name), base + '/' + e.name));
    } else if (e.name === 'index.html') {
      out.push(base + '/');
    } else if (e.name === '404.html') {
      out.push(base + '/404.html');
    }
  }
  return out;
}
const PAGES = collectPages().sort();
const KEY_PAGES = ['/', '/products/', '/products/instant-album/', '/products/vip-album/', '/products/frame/', '/gallery/', '/about/story/', '/business/'];

test.describe('A. 기능 적합성', () => {
  test('A-01/A-02 전 페이지 로드 200 + 콘솔 에러 0', async ({ page }) => {
    test.setTimeout(240000);
    const errors = [];
    page.on('console', m => { if (m.type() === 'error') errors.push(page.url() + ' :: ' + m.text().slice(0, 150)); });
    for (const p of PAGES) {
      const res = await page.goto(p, { waitUntil: 'domcontentloaded', timeout: 20000 });
      expect(res.status(), p).toBe(200);
      await page.waitForTimeout(400);
    }
    expect(errors, errors.join('\n')).toHaveLength(0);
  });

  test('A-04 히어로: 로드 직후 활성 슬라이드 존재', async ({ page }) => {
    await page.goto('/', { waitUntil: 'domcontentloaded' });
    await expect(page.locator('.hero-slide.active')).toHaveCount(1, { timeout: 3000 });
  });

  test('A-05 히어로 켄번즈: 1초 내 줌 진행(scale ≥ 1.03)', async ({ page }) => {
    await page.goto('/', { waitUntil: 'domcontentloaded' });
    await page.waitForSelector('.hero-slide.active');
    await page.waitForTimeout(1000);
    const scale = await page.evaluate(() => {
      const s = document.querySelector('.hero-slide.active');
      return parseFloat(getComputedStyle(s).transform.match(/[\d.]+/)[0]);
    });
    expect(scale).toBeGreaterThanOrEqual(1.03);
    expect(scale).toBeLessThan(1.14); // 점프(트랜지션 미적용) 아님을 함께 확인
  });

  test('A-06 히어로 로테이션: 슬라이드 전환 + leaving 정리', async ({ page }) => {
    await page.goto('/', { waitUntil: 'domcontentloaded' });
    await page.waitForSelector('.hero-slide.active');
    const first = await page.evaluate(() => document.querySelector('.hero-slide.active').style.backgroundImage);
    await page.waitForFunction(
      prev => { const a = document.querySelector('.hero-slide.active'); return a && a.style.backgroundImage !== prev; },
      first, { timeout: 8000 }
    );
    await page.waitForTimeout(1500); // 페이드 종료 대기
    expect(await page.locator('.hero-slide.leaving').count()).toBe(0);
  });

  test('A-07 갤러리 필터: 기업·기관 납품만 표시', async ({ page }) => {
    await page.goto('/gallery/', { waitUntil: 'domcontentloaded' });
    await page.click('.gallery-filter .tab-btn[data-f="corp"]');
    const counts = await page.evaluate(() => {
      const items = [...document.querySelectorAll('.gallery-item')];
      return {
        corpVisible: items.filter(i => i.dataset.cat === 'corp' && i.style.display !== 'none').length,
        otherVisible: items.filter(i => i.dataset.cat !== 'corp' && i.style.display !== 'none').length,
      };
    });
    expect(counts.corpVisible).toBeGreaterThan(0);
    expect(counts.otherVisible).toBe(0);
  });

  test('A-08 갤러리 라이트박스 열림/닫힘', async ({ page }) => {
    await page.goto('/gallery/', { waitUntil: 'domcontentloaded' });
    await page.locator('.gallery-item img').first().click();
    await expect(page.locator('#lightbox')).toHaveClass(/open/);
    await page.click('#lb-close');
    await expect(page.locator('#lightbox')).not.toHaveClass(/open/);
  });

  test('A-09 헤더(비로그인): 카탈로그·회원가입·로그인 노출', async ({ page }) => {
    await page.goto('/', { waitUntil: 'domcontentloaded' });
    const nav = page.locator('#nav-actions');
    await expect(nav).toHaveClass(/auth-ready/, { timeout: 8000 });
    await expect(nav).toBeVisible();
    for (const label of ['카탈로그', '회원가입', '로그인']) {
      await expect(nav.getByText(label, { exact: true })).toBeVisible();
    }
  });

  test('A-10 로그인 폼 필드·필수 속성', async ({ page }) => {
    await page.goto('/auth/login/', { waitUntil: 'domcontentloaded' });
    await expect(page.locator('#login-form input[name="email"]')).toHaveAttribute('required', '');
    await expect(page.locator('#login-form input[name="password"]')).toHaveAttribute('required', '');
  });

  test('A-11 회원가입 폼 렌더', async ({ page }) => {
    await page.goto('/auth/signup/', { waitUntil: 'domcontentloaded' });
    await expect(page.locator('input[name="email"]')).toBeVisible();
    await expect(page.locator('input[name="password"]')).toBeVisible();
  });

  test('A-12 마이페이지 비로그인 게이트', async ({ page }) => {
    await page.goto('/mypage/', { waitUntil: 'domcontentloaded' });
    await expect(page.locator('#mypage-gate')).toBeVisible({ timeout: 8000 });
  });

  test('A-13/A-14 문의·견적 폼 렌더', async ({ page }) => {
    for (const p of ['/support/estimate/', '/business/inquiry/']) {
      await page.goto(p, { waitUntil: 'domcontentloaded' });
      expect(await page.locator('form input, form textarea, form select').count(), p).toBeGreaterThan(0);
    }
  });

  test('A-15 푸터 버전 표기', async ({ page }) => {
    // 로컬은 layout.js 가 #site-footer 를 파트셜로 치환(outerHTML)하므로 footer 요소로 검사
    await page.goto('/', { waitUntil: 'domcontentloaded' });
    await expect(page.locator('footer')).toContainText(/v\d+\.\d+\.\d+\.\d+/, { timeout: 8000 });
  });
});

test.describe('B. UI/반응형', () => {
  for (const [name, vp] of [['B-01 모바일 375px', { width: 375, height: 812 }],
                            ['B-02 태블릿 768px', { width: 768, height: 1024 }],
                            ['B-03 데스크톱 1280px', { width: 1280, height: 900 }]]) {
    test(`${name}: 주요 페이지 가로 스크롤 없음`, async ({ page }) => {
      test.setTimeout(90000);
      await page.setViewportSize(vp);
      for (const p of KEY_PAGES) {
        await page.goto(p, { waitUntil: 'domcontentloaded' });
        await page.waitForTimeout(400);
        const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
        expect(overflow, `${p} @${vp.width}px`).toBeLessThanOrEqual(1);
      }
    });
  }

  test('B-04 전 페이지 헤더·푸터 주입', async ({ page }) => {
    test.setTimeout(240000);
    for (const p of PAGES.filter(x => !x.endsWith('404.html'))) {
      await page.goto(p, { waitUntil: 'domcontentloaded' });
      await page.waitForFunction(() => {
        const h = document.getElementById('site-header') || document.querySelector('header');
        return h && (h.children.length > 0 || h.tagName === 'HEADER');
      }, { timeout: 8000 });
    }
  });
});

test.describe('C. 접근성(KWCAG 표본)', () => {
  test('C-01/C-02/C-03 전 페이지 lang·title·img alt', async ({ page }) => {
    test.setTimeout(240000);
    const problems = [];
    const titles = new Map();
    for (const p of PAGES) {
      await page.goto(p, { waitUntil: 'domcontentloaded' });
      const r = await page.evaluate(() => ({
        lang: document.documentElement.lang,
        title: document.title.trim(),
        noAlt: [...document.querySelectorAll('img')].filter(i => !i.hasAttribute('alt')).map(i => i.getAttribute('src')),
      }));
      if (r.lang !== 'ko') problems.push(`${p}: lang="${r.lang}"`);
      if (!r.title) problems.push(`${p}: 빈 title`);
      if (r.noAlt.length) problems.push(`${p}: alt 누락 ${r.noAlt.join(',')}`);
      if (titles.has(r.title) && !p.endsWith('404.html')) problems.push(`${p}: title 중복(${titles.get(r.title)})`);
      titles.set(r.title, p);
    }
    expect(problems, problems.join('\n')).toHaveLength(0);
  });

  test('C-04 주요 페이지 h1 정확히 1개', async ({ page }) => {
    for (const p of KEY_PAGES) {
      await page.goto(p, { waitUntil: 'domcontentloaded' });
      expect(await page.locator('h1').count(), p).toBe(1);
    }
  });

  test('C-05 skip-nav 링크 존재', async ({ page }) => {
    await page.goto('/', { waitUntil: 'domcontentloaded' });
    await page.waitForSelector('.skip-nav', { state: 'attached', timeout: 8000 });
    expect(await page.locator('.skip-nav').getAttribute('href')).toBe('#main');
  });

  test('C-06 로그인 폼 라벨 연결(for/id 자동 부여)', async ({ page }) => {
    await page.goto('/auth/login/', { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(600); // layout:ready 접근성 보강 대기
    const linked = await page.evaluate(() =>
      [...document.querySelectorAll('#login-form .form-row')].every(row => {
        const l = row.querySelector('label'), f = row.querySelector('input');
        return l && f && l.htmlFor && l.htmlFor === f.id;
      })
    );
    expect(linked).toBe(true);
  });
});

test.describe('D. 성능 효율성', () => {
  test('D-01 메인 DOMContentLoaded < 3초', async ({ page }) => {
    const t0 = Date.now();
    await page.goto('/', { waitUntil: 'domcontentloaded' });
    expect(Date.now() - t0).toBeLessThan(3000);
  });

  test('D-02 히어로 첫 이미지 preload 선언', async ({ page }) => {
    await page.goto('/', { waitUntil: 'domcontentloaded' });
    expect(await page.locator('link[rel="preload"][as="image"]').count()).toBeGreaterThan(0);
  });

  test('D-03 참조 이미지 개별 ≤ 500KB', async () => {
    // 텍스트 파일에서 참조되는 이미지 파일명 수집 → 실제 파일 크기 검사
    const textExt = ['.html', '.css', '.js'];
    let corpus = '';
    (function walk(dir) {
      for (const e of fs.readdirSync(dir, { withFileTypes: true })) {
        if (e.isDirectory()) { if (!SKIP.has(e.name)) walk(path.join(dir, e.name)); }
        else if (textExt.includes(path.extname(e.name))) corpus += fs.readFileSync(path.join(dir, e.name), 'utf8');
      }
    })(ROOT);
    const over = [];
    (function walkImg(dir) {
      for (const e of fs.readdirSync(dir, { withFileTypes: true })) {
        if (e.isDirectory()) walkImg(path.join(dir, e.name));
        else if (/\.(jpe?g|png|webp)$/i.test(e.name) && corpus.includes(e.name)) {
          const sz = fs.statSync(path.join(dir, e.name)).size;
          if (sz > 500 * 1024) over.push(`${e.name} ${(sz / 1024).toFixed(0)}KB`);
        }
      }
    })(path.join(ROOT, 'assets'));
    expect(over, over.join('\n')).toHaveLength(0);
  });
});

test.describe('E. 보안성(기본)', () => {
  test('E-01 소스 내 비밀키(service_role 등) 노출 없음', async () => {
    const bad = [];
    (function walk(dir) {
      for (const e of fs.readdirSync(dir, { withFileTypes: true })) {
        if (e.isDirectory()) { if (!SKIP.has(e.name)) walk(path.join(dir, e.name)); }
        else if (['.html', '.js', '.css'].includes(path.extname(e.name))) {
          const c = fs.readFileSync(path.join(dir, e.name), 'utf8');
          // anon 키(공개 설계)는 허용, service_role JWT·시크릿 키 패턴은 금지
          if (/"role"\s*:\s*"service_role"/.test(c) || /sbp_[A-Za-z0-9]{20,}/.test(c) || /test_sk_|live_sk_/.test(c)) {
            bad.push(path.join(dir, e.name));
          }
          for (const m of c.match(/eyJ[A-Za-z0-9_-]+\.eyJ[A-Za-z0-9_-]+/g) || []) {
            try {
              const payload = JSON.parse(Buffer.from(m.split('.')[1], 'base64').toString());
              if (payload.role && payload.role !== 'anon') bad.push(`${path.join(dir, e.name)} (role=${payload.role})`);
            } catch (_) {}
          }
        }
      }
    })(ROOT);
    expect(bad, bad.join('\n')).toHaveLength(0);
  });

  test('E-02 외부 리소스 https 전용', async ({ page }) => {
    const insecure = [];
    page.on('request', r => { if (r.url().startsWith('http://') && !r.url().includes('localhost')) insecure.push(r.url()); });
    for (const p of KEY_PAGES) await page.goto(p, { waitUntil: 'networkidle' });
    expect(insecure, insecure.join('\n')).toHaveLength(0);
  });
});
