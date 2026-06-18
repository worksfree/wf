/**
 * role-content.js — 역할별 콘텐츠 제어 공통 스니펫
 *
 * 사용법: 각 페이지 <head> 하단에 삽입
 *   <script src="../../assets/role-content.js"></script>
 *
 * HTML 마킹:
 *   data-ins   → 전문 컨설턴트 전용 콘텐츠 (gfc/전문 컨설턴트만 표시)
 *   data-mgmt  → 경영지도사 전용 콘텐츠 (consultant만 표시)
 *
 * CSS 규칙 (이 파일이 자동 삽입):
 *   body.role-consultant [data-ins]  { display:none }
 *   body.role-gfc        [data-mgmt] { display:none }
 *   body.role-admin      → 모두 표시
 */

(function () {
  // CSS 주입
  var style = document.createElement('style');
  style.textContent = [
    'body.role-consultant [data-ins]  { display:none !important; }',
    'body.role-gfc        [data-mgmt] { display:none !important; }',
  ].join('\n');
  document.head.appendChild(style);

  // 역할 적용
  function applyRole(role) {
    document.body.classList.remove('role-consultant', 'role-gfc', 'role-admin', 'role-member');
    if (role) document.body.classList.add('role-' + role);
    // 역할 변경 이벤트 발행 (페이지별 추가 처리용)
    document.dispatchEvent(new CustomEvent('wf:role', { detail: { role: role } }));
  }

  // 허브로부터 역할 수신
  window.addEventListener('message', function (e) {
    if (e.data && e.data.type === 'wf_role') {
      applyRole(e.data.role || 'member');
    }
  });

  // URL 파라미터 ?role= 로 직접 테스트 가능
  var urlRole = new URLSearchParams(location.search).get('role');
  if (urlRole) applyRole(urlRole);
})();
