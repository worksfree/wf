
document.addEventListener('DOMContentLoaded', () => {
  // 프래그먼트 전용 이동(popstate) 판별용 — 경로+쿼리가 안 바뀌면 "진짜 페이지 이동"이 아니다.
  // (href="#" 앵커 클릭도 브라우저가 popstate 를 쏘는데, 그때마다 body 를 통째로
  //  fetch·교체하면 인라인 스크립트가 재실행되어 최상위 let/const 재선언 에러로 죽는다.)
  let lastPath = location.pathname + location.search;

  // Turn all internal links into SPA-style navigation
  document.body.addEventListener('click', async (e) => {
    const link = e.target.closest('a');

    // Not a link, or not an internal link, or special links
    if (!link || link.hostname !== location.hostname || 
        link.getAttribute('href')?.startsWith('#') ||
        e.metaKey || e.ctrlKey || e.shiftKey || e.altKey ||
        link.target === '_blank') {
      return;
    }

    // Don't intercept links that are meant to be handled by other scripts
    if (link.hasAttribute('data-no-spa')) return;

    e.preventDefault();
    const url = new URL(link.href);

    try {
      const response = await fetch(url.href);
      if (!response.ok) {
        // Fallback to full page load if fetch fails
        location.href = url.href;
        return;
      }
      const text = await response.text();
      const parser = new DOMParser();
      const doc = parser.parseFromString(text, 'text/html');

      // Replace head and body content
      document.head.innerHTML = doc.head.innerHTML;
      document.body.innerHTML = doc.body.innerHTML;

      // Update URL
      history.pushState({}, '', url.href);
      lastPath = url.pathname + url.search;

      // Re-run scripts. This is a simplified approach.
      // We need to re-evaluate the scripts in the new body.
      // 외부(src) 스크립트는 이미 로드·실행되어 전역(const sb 등)이 존재하므로 재실행 금지
      // (재실행 시 'Identifier already declared' 에러). 인라인 스크립트만 재실행한다.
      const scripts = Array.from(document.body.querySelectorAll('script'));
      for(const script of scripts) {
        if (script.src) continue;
        const newScript = document.createElement('script');
        newScript.textContent = script.textContent;
        script.parentNode.replaceChild(newScript, script);
      }

      // Dispatch layout:ready again as layout.js does
      // It might be better to create a more robust lifecycle event system
      setTimeout(() => {
        window.__layoutReady = true;
        document.dispatchEvent(new CustomEvent('layout:ready'));
      }, 0);

    } catch (err) {
      console.error('SPA Navigation failed:', err);
      // Fallback to full page load on error
      location.href = url.href;
    }
  });

  // Handle back/forward navigation
  window.addEventListener('popstate', async (e) => {
    const url = new URL(location.href);

    // 경로·쿼리가 그대로면 해시(#)만 바뀐 프래그먼트 이동 — 진짜 페이지 전환이 아니므로
    // body 를 다시 fetch·교체하지 않는다(안 그러면 인라인 스크립트가 재실행되어 깨진다).
    const newPath = url.pathname + url.search;
    if (newPath === lastPath) return;
    lastPath = newPath;

    try {
      const response = await fetch(url.href);
      if (!response.ok) {
        location.reload();
        return;
      }
      const text = await response.text();
      const parser = new DOMParser();
      const doc = parser.parseFromString(text, 'text/html');

      document.head.innerHTML = doc.head.innerHTML;
      document.body.innerHTML = doc.body.innerHTML;

      // Re-run scripts
      const scripts = Array.from(document.body.querySelectorAll('script'));
      for(const script of scripts) {
        if (script.src) continue;   // 외부 스크립트 재실행 금지(const 재선언 에러 방지)
        const newScript = document.createElement('script');
        newScript.textContent = script.textContent;
        script.parentNode.replaceChild(newScript, script);
      }
      
      setTimeout(() => {
        window.__layoutReady = true;
        document.dispatchEvent(new CustomEvent('layout:ready'));
      }, 0);

    } catch (err) {
      console.error('SPA Popstate failed:', err);
      location.reload();
    }
  });
});
