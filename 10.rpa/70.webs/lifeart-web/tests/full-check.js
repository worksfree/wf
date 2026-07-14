// ============================================================
// pre-test-lifeart 종합 자동 검증
//   node full-check.js   (playwright 필요)
//   전 페이지 로드/콘솔에러/헤더인라인/CLS + 관리자 콘솔 + 데이터 + 기능
// ============================================================
const { chromium } = require('playwright');
const B = 'https://pre-test-lifeart.lifeart.ai.kr';
const ADMIN = { email: 'lifeart.admin.test@worksfree.kr', password: 'LifeArt!admin2026' };
const nc = () => '?nc=' + Date.now() + Math.random().toString(36).slice(2);

const PAGES = [
  '/', '/about/story/', '/about/ceo/', '/about/location/', '/about/press/',
  '/products/', '/products/instant-album/', '/products/vip-album/', '/products/frame/', '/products/frame/order/',
  '/howto/', '/howto/instant-album/', '/howto/vip/', '/howto/frame/',
  '/business/', '/business/wedding/', '/business/travel-golf/', '/business/kiosk/', '/business/inquiry/',
  '/support/', '/support/notice/', '/support/faq/', '/support/qna/', '/support/estimate/',
  '/gallery/', '/catalog/', '/auth/login/', '/auth/signup/', '/mypage/', '/checkout/', '/admin/',
  '/terms/', '/privacy/', '/shipping/'
];

let PASS = 0, FAIL = 0; const fails = [];
const ok = (cond, name, extra) => { if (cond) { PASS++; } else { FAIL++; fails.push(name + (extra ? ' — ' + extra : '')); console.log('  ❌ ' + name + (extra ? ' — ' + extra : '')); } };

(async () => {
  const browser = await chromium.launch();

  // ── A. 전 페이지: 200 / 콘솔에러 / 헤더 인라인 / CLS ──
  console.log('\n[A] 전 페이지 로드·콘솔·헤더·CLS');
  for (const path of PAGES) {
    const p = await browser.newPage({ viewport: { width: 1280, height: 900 } });
    const errs = [];
    p.on('pageerror', e => errs.push(e.message));
    p.on('console', m => { if (m.type() === 'error') errs.push('C:' + m.text()); });
    await p.addInitScript(() => { window.__cls = 0; new PerformanceObserver(l => { for (const e of l.getEntries()) if (!e.hadRecentInput) window.__cls += e.value; }).observe({ type: 'layout-shift', buffered: true }); });
    let status = 0;
    try { const r = await p.goto(B + path + nc(), { waitUntil: 'networkidle', timeout: 25000 }); status = r.status(); } catch (e) { status = -1; }
    await p.waitForTimeout(800);
    const inlineHeader = await p.evaluate(() => { const h = document.getElementById('site-header'); return !!(h && h.querySelector('header')); });
    const cls = await p.evaluate(() => +(window.__cls || 0).toFixed(3));
    // admin 은 콘솔에 의도된 RPC 없음, 나머지는 에러 0 기대
    ok(status === 200, `[200] ${path}`, 'status=' + status);
    ok(inlineHeader, `[헤더인라인] ${path}`);
    ok(cls < 0.1, `[CLS<0.1] ${path}`, 'cls=' + cls);   // Google "good" 기준
    ok(errs.length === 0, `[콘솔에러0] ${path}`, errs.slice(0, 2).join(' | '));
    await p.close();
  }

  // ── B. 관리자 콘솔 (로그인 → 게이트 → 데이터) ──
  console.log('\n[B] 관리자 콘솔');
  {
    const p = await browser.newPage({ viewport: { width: 1280, height: 900 } });
    await p.goto(B + '/' + nc(), { waitUntil: 'networkidle' });
    const li = await p.evaluate(async (c) => { const { error } = await sb.auth.signInWithPassword(c); return error ? error.message : 'ok'; }, ADMIN);
    ok(li === 'ok', '관리자 로그인', li);
    await p.goto(B + '/admin/' + nc(), { waitUntil: 'networkidle' });
    await p.waitForTimeout(3500);
    const gate = await p.evaluate(() => getComputedStyle(document.getElementById('admin-gate')).display);
    ok(gate === 'none', '관리자 게이트 자동 열림', 'gate=' + gate);
    // 각 탭 데이터 로드 (RPC 정상 = "불러올 수 없습니다"/오류 문구 없어야)
    const tabCheck = async (tab, tableSel, badText) => {
      await p.evaluate((t) => { document.querySelector(`.tab-btn[data-tab="${t}"]`)?.click(); }, tab);
      await p.waitForTimeout(1200);
      const html = await p.evaluate((s) => document.querySelector(s)?.innerText || '', tableSel);
      const bad = badText.some(t => html.includes(t));
      return { bad, html: html.slice(0, 60) };
    };
    const dash = await p.evaluate(() => document.getElementById('kpi-total')?.textContent || '');
    ok(dash && dash !== '—', '매출현황 KPI 로드', 'total=' + dash);
    const ord = await tabCheck('orders', '#orders-table tbody', ['RPC', '불러올 수 없', '오류']);
    ok(!ord.bad, '주문 관리 RPC 정상', ord.html);
    const usr = await tabCheck('users', '#users-table tbody', ['RPC', '불러올 수 없', '오류']);
    ok(!usr.bad, '회원 관리 RPC 정상', usr.html);
    const press = await tabCheck('press', '#press-table tbody', ['불러올 수 없', '권한']);
    ok(!press.bad, '보도자료 로드', press.html);
    const hero = await tabCheck('hero', '#hero-table tbody', ['불러올 수 없', '권한']);
    ok(!hero.bad, '첫화면 슬라이드 로드', hero.html);
    await p.close();
  }

  // ── C. 기능/콘텐츠 스팟 체크 ──
  console.log('\n[C] 기능·콘텐츠');
  {
    const p = await browser.newPage({ viewport: { width: 1280, height: 900 } });
    // 홈 히어로 슬라이드 동작
    await p.goto(B + '/' + nc(), { waitUntil: 'networkidle' }); await p.waitForTimeout(500);
    ok(await p.locator('.hero-slide.active').count() === 1, '홈 히어로 활성 슬라이드');
    ok(await p.evaluate(() => document.documentElement.getAttribute('data-stage')) === '5', 'pre-test full(stage5)');
    // 소셜 로그인 버튼(stage5)
    await p.goto(B + '/auth/login/' + nc(), { waitUntil: 'networkidle' }); await p.waitForTimeout(400);
    ok(await p.locator('.btn-google').isVisible() && await p.locator('.btn-kakao').isVisible(), '소셜 로그인 버튼 노출');
    // 오시는 길 지도
    await p.goto(B + '/about/location/' + nc(), { waitUntil: 'networkidle' });
    ok(await p.locator('iframe[src*="google.com/maps"]').count() === 1, '오시는 길 지도 iframe');
    ok((await p.content()).includes('검단산로 239'), '주소 검단산로 239');
    // travel-golf 아날로그 2행
    await p.goto(B + '/business/travel-golf/' + nc(), { waitUntil: 'networkidle' });
    ok(await p.locator('.analog-hero').count() === 1 && await p.locator('.scan-card').count() === 3, 'travel-golf 아날로그 2행 섹션');
    // 공지/FAQ DB 로드
    await p.goto(B + '/support/notice/' + nc(), { waitUntil: 'networkidle' }); await p.waitForTimeout(1000);
    ok(!(await p.locator('#notice-list').innerText()).includes('불러오는 중'), '공지 로더 실행');
    await p.goto(B + '/support/faq/' + nc(), { waitUntil: 'networkidle' }); await p.waitForTimeout(1000);
    ok(!(await p.locator('#faq-list').innerText()).includes('불러오는 중'), 'FAQ 로더 실행');
    await p.close();
  }

  await browser.close();
  console.log(`\n════════ 결과: PASS ${PASS} / FAIL ${FAIL} ════════`);
  if (fails.length) { console.log('실패 항목:'); fails.forEach(f => console.log('  - ' + f)); }
  process.exit(FAIL === 0 ? 0 : 1);
})();
